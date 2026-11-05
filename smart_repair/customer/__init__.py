import json
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from smart_repair.extensions import db
from smart_repair.forms import *
from smart_repair.models import *
from smart_repair.security import accessible_request, accessible_job, roles_required
from smart_repair.services.diagnosis import diagnose, save_results
from smart_repair.services.workflow import BusinessError, code, book_appointment, request_status, notify_admins, local_now
from smart_repair.services.billing import decide_estimate
from smart_repair.services.uploads import validate_upload, store_upload

bp = Blueprint("customer", __name__, url_prefix="/customer")


def own_device(device_id):
    device = db.get_or_404(CustomerDevice, device_id)
    if not current_user.customer or device.customer_id != current_user.customer.id or device.archived_at:
        abort(404)
    return device


def intake_choices(form):
    form.device_id.choices = [(d.id, f"{d.nickname} · {d.model.brand.name} {d.model.model_name}") for d in CustomerDevice.query.filter_by(customer_id=current_user.customer.id, archived_at=None).all()]
    form.symptom_ids.choices = [(s.id, f"{s.category.name} · {s.name}") for s in Symptom.query.filter_by(is_active=True, archived_at=None).all()]
    if hasattr(form, "service_center_id"):
        form.service_center_id.choices = [(c.id, f"{c.name} · {c.city}") for c in ServiceCenter.query.filter_by(is_active=True, archived_at=None).all()]


@bp.route("/devices", methods=["GET", "POST"])
@roles_required("Customer")
def devices():
    form = DeviceForm()
    form.device_model_id.choices = [(m.id, f"{m.brand.name} {m.model_name} · {m.category.name}") for m in DeviceModel.query.filter_by(archived_at=None).all() if m.brand.is_active and m.category.is_active and not m.brand.archived_at and not m.category.archived_at]
    if form.validate_on_submit():
        if form.purchase_date.data and form.purchase_date.data > local_now().date():
            form.purchase_date.errors.append("Purchase date cannot be in the future.")
        else:
            device = CustomerDevice(customer_id=current_user.customer.id)
            form.populate_obj(device)
            db.session.add(device)
            db.session.commit()
            flash("Device registered. You're ready to request a repair.", "success")
            return redirect(url_for("customer.devices"))
    records = CustomerDevice.query.filter_by(customer_id=current_user.customer.id, archived_at=None).all()
    return render_template("devices.html", form=form, devices=records, title="My devices")


@bp.route("/devices/<int:id>/edit", methods=["GET", "POST"])
@roles_required("Customer")
def edit_device(id):
    device = own_device(id)
    form = DeviceForm(obj=device)
    form.device_model_id.choices = [(m.id, f"{m.brand.name} {m.model_name}") for m in DeviceModel.query.filter_by(archived_at=None).all()]
    if form.validate_on_submit():
        if form.purchase_date.data and form.purchase_date.data > local_now().date():
            form.purchase_date.errors.append("Purchase date cannot be in the future.")
        elif RepairRequest.query.filter_by(customer_device_id=device.id).first() and form.device_model_id.data != device.device_model_id:
            form.device_model_id.errors.append("A model linked to repair history cannot be changed.")
        else:
            form.populate_obj(device)
            device.audit(current_user.id, "Customer updated device")
            db.session.commit()
            flash("Device updated.", "success")
            return redirect(url_for("customer.devices"))
    return render_template("form.html", form=form, title="Edit device", subtitle=device.nickname, submit="Save device")


@bp.post("/devices/<int:id>/delete")
@roles_required("Customer")
def delete_device(id):
    device = own_device(id)
    if RepairRequest.query.filter_by(customer_device_id=id).first():
        device.archived_at, device.archive_reason = utcnow(), "Archived by owner; repair history retained"
    else:
        db.session.delete(device)
    db.session.commit()
    flash("Device removed from your device list.", "success")
    return redirect(url_for("customer.devices"))


@bp.route("/diagnosis", methods=["GET", "POST"])
@roles_required("Customer")
def diagnosis():
    form = DiagnosisForm()
    intake_choices(form)
    results = None
    if form.validate_on_submit():
        device = own_device(form.device_id.data)
        session["diagnosis"] = {"device_id": device.id, "symptoms": form.symptom_ids.data}
        return redirect(url_for("customer.diagnosis", result=1))
    if request.method == "GET" and request.args.get("result") and session.get("diagnosis"):
        saved = session["diagnosis"]
        device = own_device(saved["device_id"])
        form.device_id.data, form.symptom_ids.data = device.id, saved["symptoms"]
        results = diagnose(device.model.category_id, saved["symptoms"])
    return render_template("diagnosis.html", form=form, results=results, title="Smart diagnosis")


from flask import session


@bp.route("/requests", methods=["GET", "POST"])
@roles_required("Customer")
def requests():
    if request.method == "POST":
        return new_request()
    return redirect(url_for("main.repairs"))


@bp.route("/requests/new", methods=["GET", "POST"])
@roles_required("Customer")
def new_request():
    form = RequestForm()
    intake_choices(form)
    if request.method == "GET" and session.get("diagnosis"):
        saved = session["diagnosis"]
        form.device_id.data, form.symptom_ids.data = saved["device_id"], saved["symptoms"]
    if form.validate_on_submit():
        device = own_device(form.device_id.data)
        validated = validate_upload(form.attachment.data) if form.attachment.data else None
        record = RepairRequest(customer_id=current_user.customer.id, customer_device_id=device.id,
            service_center_id=form.service_center_id.data, request_code=code("SR"),
            issue_description=form.issue_description.data.strip(), urgency=form.urgency.data,
            selected_symptoms=json.dumps(form.symptom_ids.data))
        db.session.add(record)
        db.session.flush()
        record.audit(current_user.id, "Customer submitted repair request")
        save_results(record, diagnose(device.model.category_id, form.symptom_ids.data))
        attachment = None
        if validated:
            attachment = store_upload(validated, record.id, current_user.id)
            db.session.add(attachment)
        notify_admins("New repair request", f"{record.request_code}: {device.nickname}", record)
        try:
            db.session.commit()
        except Exception:
            if attachment:
                (Path(current_app.config["UPLOAD_FOLDER"]) / attachment.file_path).unlink(missing_ok=True)
            raise
        session.pop("diagnosis", None)
        flash(f"Repair request {record.request_code} submitted successfully.", "success")
        return redirect(url_for("customer.request_detail", id=record.id))
    return render_template("request_form.html", form=form, title="New repair request")


@bp.get("/requests/<int:id>")
@login_required
def request_detail(id):
    record = accessible_request(id)
    return render_template("repair_detail.html", record=record, job=record.job, title=record.request_code,
        transitions=__import__("smart_repair.services.workflow", fromlist=["TRANSITIONS"]).TRANSITIONS,
        technicians=TechnicianProfile.query.filter_by(is_available=True, archived_at=None).all() if current_user.has_role("Admin") else [],
        skills=Skill.query.filter_by(is_active=True, archived_at=None).all(),
        parts=SparePart.query.filter_by(is_active=True, archived_at=None).all() if current_user.role_name != "Customer" else [],
        services=Service.query.filter_by(is_active=True, archived_at=None).all() if current_user.has_role("Admin") else [],
        review_form=ReviewForm())


@bp.post("/requests/<int:id>/cancel")
@roles_required("Customer")
def cancel_request(id):
    record = accessible_request(id)
    if record.customer_id != current_user.customer.id or record.status not in {"Submitted", "Under Review", "Appointment Scheduled"}:
        abort(403)
    request_status(record, "Cancelled", current_user.id, request.form.get("reason", ""))
    for appointment in record.appointments:
        if appointment.status == "Scheduled":
            appointment.status = "Cancelled"
            appointment.audit(current_user.id, "Request cancelled by customer")
    db.session.commit()
    flash("Request cancelled.", "success")
    return redirect(url_for("customer.request_detail", id=id))


@bp.route("/appointments", methods=["GET", "POST"])
@roles_required("Customer")
def appointments():
    form = AppointmentForm()
    owned = RepairRequest.query.filter_by(customer_id=current_user.customer.id).all()
    form.repair_request_id.choices = [(r.id, f"{r.request_code} · {r.device.nickname}") for r in owned if r.status in {"Submitted", "Under Review", "Appointment Scheduled"}]
    form.service_center_id.choices = [(c.id, f"{c.name} ({c.opening_time:%H:%M}–{c.closing_time:%H:%M})") for c in ServiceCenter.query.filter_by(is_active=True, archived_at=None).all()]
    edit_id = request.args.get("edit", type=int)
    appointment = db.get_or_404(Appointment, edit_id) if edit_id else None
    if appointment:
        accessible_request(appointment.repair_request_id)
        if appointment.request.customer_id != current_user.customer.id or appointment.status != "Scheduled":
            abort(403)
        if request.method == "GET":
            from smart_repair.services.workflow import local_datetime
            form.repair_request_id.data, form.service_center_id.data = appointment.repair_request_id, appointment.service_center_id
            form.scheduled_start.data = local_datetime(appointment.scheduled_start).replace(tzinfo=None)
            form.scheduled_end.data = local_datetime(appointment.scheduled_end).replace(tzinfo=None)
    if form.validate_on_submit():
        record = accessible_request(form.repair_request_id.data)
        if appointment and record.id != appointment.repair_request_id:
            raise BusinessError("A rescheduled appointment must keep the same repair request.")
        book_appointment(record, db.get_or_404(ServiceCenter, form.service_center_id.data),
            form.scheduled_start.data, form.scheduled_end.data, current_user.id, appointment)
        db.session.commit()
        flash("Appointment saved. All times are Pakistan time.", "success")
        return redirect(url_for("customer.appointments"))
    records = Appointment.query.join(RepairRequest).filter(RepairRequest.customer_id == current_user.customer.id).order_by(Appointment.scheduled_start.desc()).all()
    return render_template("appointments.html", form=form, appointments=records, title="Appointments", editing=appointment)


@bp.post("/appointments/<int:id>/cancel")
@roles_required("Customer")
def cancel_appointment(id):
    appointment = db.get_or_404(Appointment, id)
    record = accessible_request(appointment.repair_request_id)
    if record.customer_id != current_user.customer.id or appointment.status != "Scheduled" or record.status not in {"Submitted", "Under Review", "Appointment Scheduled"}:
        abort(403)
    appointment.status = "Cancelled"
    appointment.audit(current_user.id, "Customer cancelled appointment")
    if record.status == "Appointment Scheduled":
        request_status(record, "Under Review", current_user.id, "Appointment cancelled")
    db.session.commit()
    flash("Appointment cancelled.", "success")
    return redirect(url_for("customer.appointments"))


@bp.post("/estimates/<int:id>/decision")
@roles_required("Customer")
def estimate_decision(id):
    estimate = db.get_or_404(Estimate, id)
    accessible_job(estimate.repair_job_id)
    decide_estimate(estimate, current_user.customer.id, request.form.get("decision"), current_user.id)
    db.session.commit()
    flash("Your estimate decision has been recorded.", "success")
    return redirect(url_for("customer.request_detail", id=estimate.job.repair_request_id))


@bp.get("/invoices/<int:id>")
@roles_required("Customer", "Admin")
def invoice(id):
    record = db.get_or_404(Invoice, id)
    accessible_job(record.repair_job_id)
    return render_template("invoice.html", invoice=record, title=record.invoice_number)


@bp.post("/jobs/<int:id>/review")
@roles_required("Customer")
def review(id):
    job = accessible_job(id)
    form = ReviewForm()
    if job.status != "Completed" or job.request.customer_id != current_user.customer.id:
        raise BusinessError("Only the customer of a completed job can submit feedback.")
    if not form.validate_on_submit():
        raise BusinessError("Choose a rating from 1 to 5 and keep feedback under 2,000 characters.")
    existing = Review.query.filter_by(repair_job_id=id, customer_id=current_user.customer.id).first()
    record = existing or Review(repair_job_id=id, customer_id=current_user.customer.id)
    record.rating, record.comment = form.rating.data, form.comment.data
    record.archived_at = None
    record.audit(current_user.id, "Customer saved review")
    db.session.add(record)
    db.session.commit()
    flash("Thank you. Your feedback has been saved.", "success")
    return redirect(url_for("customer.request_detail", id=job.repair_request_id))


@bp.post("/reviews/<int:id>/delete")
@roles_required("Customer")
def delete_review(id):
    record = db.get_or_404(Review, id)
    if record.customer_id != current_user.customer.id:
        abort(404)
    record.archived_at, record.archive_reason = utcnow(), "Customer withdrew review"
    record.audit(current_user.id, record.archive_reason)
    db.session.commit()
    flash("Review withdrawn.", "success")
    return redirect(url_for("main.repairs"))


@bp.get("/attachments/<int:id>")
@login_required
def attachment(id):
    record = db.get_or_404(RepairAttachment, id)
    accessible_request(record.repair_request_id)
    if record.archived_at:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], record.file_path,
        as_attachment=True, download_name=record.file_name, mimetype=record.mime_type)
