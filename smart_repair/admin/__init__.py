from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import String, Text, cast

from smart_repair.extensions import db
from smart_repair.models import *
from smart_repair.security import roles_required
from smart_repair.services.workflow import BusinessError, assign_technician, request_status, code, decimal
from smart_repair.services.stock import movement, receive_order, reserve, release_reservation, reverse_movement
from smart_repair.services.billing import create_estimate, send_estimate, issue_invoice, record_payment, refund_payment
from .policy import *

bp = Blueprint("admin", __name__, url_prefix="/admin")


def resource_model(resource):
    if resource not in MODELS:
        abort(404)
    return MODELS[resource]


def columns_for(model):
    hidden = {"password_hash", "file_path", "audit_log"}
    return [c for c in model.__table__.columns if c.name not in hidden]


@bp.get("/data")
@roles_required("Admin")
def data():
    counts = {name: model.query.count() for name, model in MODELS.items()}
    return render_template("admin/data.html", counts=counts, title="Data management")


@bp.get("/reports")
@roles_required("Admin")
def reports():
    statuses = db.session.execute(db.select(RepairRequest.status, db.func.count()).group_by(RepairRequest.status)).all()
    workloads = [(tech, TechnicianAssignment.query.filter_by(technician_id=tech.id, status="Active").count()) for tech in TechnicianProfile.query.all()]
    payments = Payment.query.filter_by(status="Completed").order_by(Payment.created_at.desc()).all()
    low_stock = [p for p in SparePart.query.filter_by(is_active=True, archived_at=None).all() if p.available <= p.reorder_level]
    return render_template("admin/reports.html", statuses=statuses, workloads=workloads, payments=payments,
        revenue=sum(p.amount for p in payments), low_stock=low_stock, title="Reports & insights")


@bp.get("/inventory")
@bp.get("/inventory/low-stock")
@roles_required("Admin")
def inventory():
    parts = SparePart.query.filter_by(archived_at=None).all()
    if request.path.endswith("low-stock"):
        parts = [p for p in parts if p.available <= p.reorder_level]
    return render_template("admin/inventory.html", parts=parts,
        orders=PurchaseOrder.query.filter_by(archived_at=None).order_by(PurchaseOrder.id.desc()).all(),
        transactions=InventoryTransaction.query.order_by(InventoryTransaction.id.desc()).limit(20).all(), title="Parts & inventory")


@bp.route("/assignments", methods=["GET", "POST"])
@roles_required("Admin")
def assignments():
    if request.method == "GET":
        return redirect(url_for("main.repairs"))
    repair = db.get_or_404(RepairRequest, request.form.get("repair_request_id", type=int))
    tech = db.get_or_404(TechnicianProfile, request.form.get("technician_id", type=int))
    skill = request.form.get("required_skill_id", type=int)
    if skill:
        db.get_or_404(Skill, skill)
        repair.required_skill_id = skill
    assign_technician(repair, tech, current_user.id, request.form.get("notes", "").strip()[:2000])
    db.session.commit()
    flash("Technician assigned. Work order and timeline updated.", "success")
    return redirect(url_for("customer.request_detail", id=repair.id))


@bp.post("/requests/<int:id>/review")
@roles_required("Admin")
def review_request(id):
    record = db.get_or_404(RepairRequest, id)
    status = request.form.get("status")
    if status not in {"Under Review", "Rejected", "Cancelled"}:
        raise BusinessError("Choose a permitted review action.")
    request_status(record, status, current_user.id, request.form.get("reason", ""))
    db.session.commit()
    flash("Request updated.", "success")
    return redirect(url_for("customer.request_detail", id=id))


@bp.post("/jobs/<int:id>/reserve")
@roles_required("Admin")
def reserve_part(id):
    job = db.get_or_404(RepairJob, id)
    part = db.get_or_404(SparePart, request.form.get("part_id", type=int))
    quantity = request.form.get("quantity", type=int)
    if quantity is None:
        raise BusinessError("Enter a whole-number quantity.")
    reserve(part, job, quantity, current_user.id)
    db.session.commit()
    flash("Parts reserved for this repair.", "success")
    return redirect(url_for("customer.request_detail", id=job.repair_request_id))


@bp.post("/reservations/<int:id>/release")
@roles_required("Admin")
def release_part(id):
    record = db.get_or_404(PartReservation, id)
    release_reservation(record, current_user.id)
    db.session.commit()
    flash("Stock reservation released.", "success")
    return redirect(url_for("customer.request_detail", id=db.session.get(RepairJob, record.repair_job_id).repair_request_id))


@bp.post("/inventory/adjust")
@roles_required("Admin")
def adjust_stock():
    part = db.get_or_404(SparePart, request.form.get("part_id", type=int))
    change = request.form.get("quantity_change", type=int)
    reason = request.form.get("reason", "").strip()
    if not change or not 3 <= len(reason) <= 1000:
        raise BusinessError("Enter a non-zero whole-number stock change and a reason (3–1,000 characters).")
    movement(part, change, current_user.id, "Adjustment", notes=reason)
    db.session.commit()
    flash("Stock adjusted with an audit record.", "success")
    return redirect(url_for("admin.inventory"))


@bp.post("/orders/<int:id>/receive")
@roles_required("Admin")
def receive(id):
    receive_order(db.get_or_404(PurchaseOrder, id), current_user.id)
    db.session.commit()
    flash("Order received. Remaining quantities added to stock.", "success")
    return redirect(url_for("admin.inventory"))


@bp.post("/jobs/<int:id>/estimates")
@roles_required("Admin")
def estimate(id):
    job = db.get_or_404(RepairJob, id)
    lines = []
    for service in Service.query.filter_by(is_active=True, archived_at=None).all():
        qty = request.form.get(f"service_{service.id}", type=int) or 0
        if qty < 0:
            raise BusinessError("Line quantities cannot be negative.")
        if qty:
            lines.append(("service", service.id, qty))
    for part in SparePart.query.filter_by(is_active=True, archived_at=None).all():
        qty = request.form.get(f"part_{part.id}", type=int) or 0
        if qty < 0:
            raise BusinessError("Line quantities cannot be negative.")
        if qty:
            lines.append(("part", part.id, qty))
    expiry = None
    if request.form.get("valid_until"):
        try:
            expiry = datetime.strptime(request.form["valid_until"], "%Y-%m-%d").date()
        except ValueError:
            raise BusinessError("Enter a valid estimate expiry date.")
    record = create_estimate(job, current_user.id, lines, request.form.get("tax", 0), request.form.get("discount", 0), expiry)
    if request.form.get("send") == "yes":
        send_estimate(record, current_user.id)
    db.session.commit()
    flash("Estimate prepared. All totals were calculated on the server.", "success")
    return redirect(url_for("customer.request_detail", id=job.repair_request_id))


@bp.post("/estimates/<int:id>/send")
@roles_required("Admin")
def send(id):
    record = db.get_or_404(Estimate, id)
    send_estimate(record, current_user.id)
    db.session.commit()
    flash("Estimate sent for customer approval.", "success")
    return redirect(url_for("customer.request_detail", id=record.job.repair_request_id))


@bp.post("/jobs/<int:id>/invoice")
@roles_required("Admin")
def invoice(id):
    record = issue_invoice(db.get_or_404(RepairJob, id), current_user.id)
    db.session.commit()
    flash("Final invoice issued.", "success")
    return redirect(url_for("customer.invoice", id=record.id))


@bp.post("/invoices/<int:id>/payment")
@roles_required("Admin")
def payment(id):
    record = db.get_or_404(Invoice, id)
    record_payment(record, request.form.get("amount"), request.form.get("method"), current_user.id,
        (request.form.get("reference", "").strip() or None))
    db.session.commit()
    flash("Payment recorded.", "success")
    return redirect(url_for("customer.invoice", id=id))


@bp.get("/<resource>")
@roles_required("Admin")
def list_resource(resource):
    model = resource_model(resource)
    query = model.query
    search = request.args.get("q", "").strip()[:150]
    if search:
        columns = [c for c in columns_for(model) if isinstance(c.type, (String, Text)) and c.name not in {"archive_reason"}]
        query = query.filter(db.or_(*(c.ilike(f"%{search}%") for c in columns)))
    if request.args.get("archived") != "1":
        query = query.filter(model.archived_at.is_(None))
    page = db.paginate(query.order_by(model.id.desc()).statement, page=max(1, request.args.get("page", 1, type=int)), per_page=12, error_out=False)
    columns = [c for c in columns_for(model) if c.name not in {"archived_at", "archive_reason"}][:7]
    return render_template("admin/list.html", resource=resource, page=page, columns=columns,
        title=resource.replace("_", " ").title(), can_create=can_edit(resource) and resource not in CREATE_DISABLED,
        guide=WORKFLOW_GUIDE.get(resource), can_edit=can_edit)


@bp.route("/<resource>/new", methods=["GET", "POST"])
@bp.route("/<resource>/<int:id>/edit", methods=["GET", "POST"])
@roles_required("Admin")
def edit_resource(resource, id=None):
    model = resource_model(resource)
    record = db.get_or_404(model, id) if id else None
    if not can_edit(resource, record) or (not id and resource in CREATE_DISABLED):
        flash(WORKFLOW_GUIDE.get(resource, "This historical record is protected. Use its workflow action."), "info")
        return redirect(url_for("admin.list_resource", resource=resource))
    form = build_form(resource, record)
    if form.validate_on_submit():
        original = {c.name: getattr(record, c.name) for c in model.__table__.columns} if record else None
        target = record or model()
        populate(resource, form, target, current_user.id)
        with db.session.no_autoflush:
            validate_record(resource, target, current_user.id, original)
        if original:
            changes = [f"{name}: {original.get(name)!r} → {getattr(target, name)!r}"
                for name in EDIT_FIELDS[resource].split() if original.get(name) != getattr(target, name)]
            if changes:
                target.audit(current_user.id, "; ".join(changes))
        target.audit(current_user.id, "Updated through administrator form" if record else "Created through administrator form")
        db.session.add(target)
        db.session.flush()
        recalculate_parent(resource, target)
        db.session.commit()
        flash("Record saved.", "success")
        return redirect(url_for("admin.detail_resource", resource=resource, id=target.id))
    return render_template("form.html", form=form, title=f"{'Edit' if id else 'New'} {resource.replace('_', ' ').rstrip('s')}",
        subtitle="Reference and draft data · server validation enabled", submit="Save record")


@bp.get("/<resource>/<int:id>")
@roles_required("Admin")
def detail_resource(resource, id):
    model = resource_model(resource)
    record = db.get_or_404(model, id)
    return render_template("admin/detail.html", resource=resource, record=record, columns=columns_for(model),
        title=str(record), editable=can_edit(resource, record), guide=WORKFLOW_GUIDE.get(resource))


@bp.post("/<resource>/<int:id>/delete")
@roles_required("Admin")
def delete_resource(resource, id):
    model = resource_model(resource)
    record = db.get_or_404(model, id)
    reason = request.form.get("reason", "").strip()
    if not 3 <= len(reason) <= 1000 or record.archived_at:
        raise BusinessError("Provide a reason (3–1,000 characters) for an active record.")
    if resource == "roles" and record.is_system:
        raise BusinessError("System roles are protected.")
    if resource == "users":
        if record.id == current_user.id:
            raise BusinessError("You cannot deactivate your own administrator account.")
        record.is_active = False
    elif resource == "user_roles":
        if record.user_id == current_user.id and db.session.get(Role, record.role_id).name == "Admin":
            raise BusinessError("You cannot remove your own administrator role.")
        record.audit(current_user.id, f"Unassigned role: {reason}")
        db.session.delete(record)
        db.session.commit()
        flash("Role unassigned.", "success")
        return redirect(url_for("admin.list_resource", resource=resource))
    elif resource == "inventory_transactions":
        reverse_movement(record, current_user.id, reason)
        db.session.commit()
        flash("Stock movement reversed with a compensating transaction.", "success")
        return redirect(url_for("admin.detail_resource", resource=resource, id=id))
    elif resource == "payments":
        refund_payment(record, current_user.id, reason)
        db.session.commit()
        flash("Manual refund recorded; original payment retained.", "success")
        return redirect(url_for("admin.detail_resource", resource=resource, id=id))
    elif resource == "invoices":
        if record.paid or record.job.status == "Completed":
            raise BusinessError("Refund payments before voiding an unsettled job invoice. Completed billing is retained.")
        if record.status == "Void":
            raise BusinessError("This invoice is already void.")
        record.status = "Void"
        record.audit(current_user.id, f"Invoice voided: {reason}")
        db.session.commit()
        flash("Invoice voided and retained.", "success")
        return redirect(url_for("admin.detail_resource", resource=resource, id=id))
    elif resource in {"repair_status_history", "repair_part_usages"}:
        raise BusinessError("This audit history is immutable. Add a corrective note or stock adjustment.")
    elif resource == "part_reservations":
        release_reservation(record, current_user.id)
    elif resource in {"repair_requests", "repair_jobs"}:
        repair = record if resource == "repair_requests" else record.request
        request_status(repair, "Cancelled", current_user.id, reason)
    elif resource == "appointments":
        if record.request.status not in {"Submitted", "Under Review", "Appointment Scheduled"}:
            raise BusinessError("Appointments linked to assigned work are retained.")
        record.status = "Cancelled"
        if record.request.status == "Appointment Scheduled":
            request_status(record.request, "Under Review", current_user.id, reason)
    elif resource == "technician_assignments":
        raise BusinessError("Use technician reassignment on the repair detail page so the work order remains consistent.")
    elif resource in {"purchase_orders", "purchase_order_items", "estimates", "estimate_lines", "repair_job_services"}:
        if not can_edit(resource, record):
            raise BusinessError("Posted or approved records cannot be removed. Use the appropriate cancel/void workflow.")
        if resource == "purchase_orders" and record.items:
            raise BusinessError("Remove draft order lines before deleting the order.")
        if resource == "estimates" and record.lines:
            raise BusinessError("Remove draft estimate lines before deleting the estimate.")
        parent_id = record.purchase_order_id if resource == "purchase_order_items" else record.estimate_id if resource == "estimate_lines" else None
        db.session.delete(record)
        db.session.flush()
        if parent_id:
            if resource == "purchase_order_items":
                parent = db.session.get(PurchaseOrder, parent_id)
                db.session.expire(parent, ["items"])
                parent.total_amount = sum(i.quantity_ordered * i.unit_cost for i in parent.items)
            else:
                from smart_repair.services.billing import recalculate
                parent = db.session.get(Estimate, parent_id)
                db.session.expire(parent, ["lines"])
                recalculate(parent)
        db.session.commit()
        flash("Draft record deleted.", "success")
        return redirect(url_for("admin.list_resource", resource=resource))
    elif resource == "technician_availability":
        check_availability_assignments(record)
        if record.available_date < local_now().date():
            raise BusinessError("Past availability is retained.")
        record.is_available = False
    elif resource in EDIT_FIELDS and resource not in {"customer_profiles", "technician_profiles", "customer_devices", "repair_notes", "notifications"}:
        # Unreferenced catalogue/association data may be deleted; RESTRICT prevents history loss.
        if not hasattr(record, "is_active"):
            db.session.delete(record)
            db.session.commit()
            flash("Unreferenced record deleted.", "success")
            return redirect(url_for("admin.list_resource", resource=resource))
        record.is_active = False
    if hasattr(record, "is_active"):
        record.is_active = False
    record.archived_at, record.archive_reason = utcnow(), reason
    record.audit(current_user.id, f"Archived: {reason}")
    db.session.commit()
    flash("Record archived. Linked history retained.", "success")
    return redirect(url_for("admin.list_resource", resource=resource))
