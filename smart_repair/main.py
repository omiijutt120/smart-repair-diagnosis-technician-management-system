from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from smart_repair.extensions import db
from smart_repair.forms import ProfileForm
from smart_repair.models import *
from smart_repair.services.workflow import local_now, local_datetime, to_utc

bp = Blueprint("main", __name__)


def scoped_requests():
    query = RepairRequest.query.filter(RepairRequest.archived_at.is_(None))
    if current_user.has_role("Admin"):
        return query
    if current_user.has_role("Technician") and current_user.technician:
        return query.join(RepairJob).join(TechnicianAssignment, RepairJob.assigned_assignment_id == TechnicianAssignment.id).filter(
            TechnicianAssignment.technician_id == current_user.technician.id, TechnicianAssignment.status.in_(["Active", "Closed"]))
    if current_user.customer:
        return query.filter_by(customer_id=current_user.customer.id)
    abort(403)


@bp.get("/")
def landing():
    return render_template("landing.html", title="Repair, without the guesswork")


@bp.get("/dashboard")
@login_required
def dashboard():
    query = scoped_requests()
    total = query.count()
    active = query.filter(~RepairRequest.status.in_(["Completed", "Rejected", "Cancelled"])).count()
    completed = query.filter_by(status="Completed").count()
    awaiting = query.filter_by(status="Awaiting Approval").count()
    recent = query.order_by(RepairRequest.created_at.desc()).limit(6).all()
    statuses = [(name, query.filter_by(status=name).count()) for name in ["Submitted", "Assigned", "Inspection", "Awaiting Approval", "In Progress", "Ready for Collection", "Completed"]]
    notifications = Notification.query.filter_by(user_id=current_user.id, archived_at=None).order_by(Notification.created_at.desc()).limit(4).all()
    today = local_now().date()
    start_day = to_utc(datetime.combine(today, datetime.min.time()))
    end_day = start_day + timedelta(days=1)
    appointments_query = Appointment.query.join(RepairRequest).filter(Appointment.status == "Scheduled", Appointment.scheduled_end >= utcnow())
    if current_user.role_name == "Customer":
        appointments_query = appointments_query.filter(RepairRequest.customer_id == current_user.customer.id)
    elif current_user.role_name == "Technician":
        appointments_query = appointments_query.join(RepairJob).join(TechnicianAssignment, RepairJob.assigned_assignment_id == TechnicianAssignment.id).filter(TechnicianAssignment.technician_id == current_user.technician.id)
    appointments = appointments_query.order_by(Appointment.scheduled_start).limit(3).all()
    techs = TechnicianProfile.query.filter_by(archived_at=None).all() if current_user.has_role("Admin") else []
    low_stock = [p for p in SparePart.query.filter_by(is_active=True, archived_at=None).all() if p.available <= p.reorder_level] if current_user.has_role("Admin") else []
    revenue = sum(p.amount for p in Payment.query.filter_by(status="Completed").all()) if current_user.has_role("Admin") else 0
    return render_template("dashboard.html", title="Overview", total=total, active=active, completed=completed,
        awaiting=awaiting, recent=recent, statuses=statuses, notifications=notifications, appointments=appointments,
        technicians=techs, low_stock=low_stock, revenue=revenue)


@bp.get("/repairs")
@login_required
def repairs():
    query = scoped_requests()
    search = request.args.get("q", "").strip()[:150]
    status = request.args.get("status", "")
    if search:
        query = query.join(CustomerDevice).filter(db.or_(RepairRequest.request_code.ilike(f"%{search}%"),
            RepairRequest.issue_description.ilike(f"%{search}%"), CustomerDevice.nickname.ilike(f"%{search}%")))
    if status:
        query = query.filter(RepairRequest.status == status)
    if request.args.get("center", type=int):
        query = query.filter(RepairRequest.service_center_id == request.args.get("center", type=int))
    if request.args.get("technician", type=int):
        assignment_ids = db.select(TechnicianAssignment.repair_request_id).where(
            TechnicianAssignment.technician_id == request.args.get("technician", type=int), TechnicianAssignment.status == "Active")
        query = query.filter(RepairRequest.id.in_(assignment_ids))
    for arg, is_end in [("from", False), ("to", True)]:
        value = request.args.get(arg)
        if value:
            try:
                date = datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                abort(400, "Enter valid filter dates.")
            boundary = to_utc(date + timedelta(days=1) if is_end else date)
            query = query.filter(RepairRequest.created_at < boundary if is_end else RepairRequest.created_at >= boundary)
    page = db.paginate(query.order_by(RepairRequest.created_at.desc()).statement,
        page=max(1, request.args.get("page", 1, type=int)), per_page=10, error_out=False)
    from smart_repair.services.workflow import TRANSITIONS
    return render_template("repairs.html", page=page, title="Repair requests", statuses=TRANSITIONS,
        centers=ServiceCenter.query.filter_by(is_active=True, archived_at=None).all(),
        technicians=TechnicianProfile.query.filter_by(archived_at=None).all() if current_user.has_role("Admin") else [])


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm()
    if request.method == "GET":
        form.full_name.data, form.phone.data = current_user.full_name, current_user.phone
        if current_user.customer:
            for name in ["address", "city", "preferred_contact"]:
                form[name].data = getattr(current_user.customer, name)
    if form.validate_on_submit():
        phone = form.phone.data.strip() or None
        if phone and User.query.filter(User.phone == phone, User.id != current_user.id).first():
            form.phone.errors.append("This phone number is already in use.")
        else:
            current_user.full_name, current_user.phone = form.full_name.data.strip(), phone
            current_user.audit(current_user.id, "Updated own contact details")
            if current_user.customer:
                for name in ["address", "city", "preferred_contact"]:
                    setattr(current_user.customer, name, form[name].data)
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("main.profile"))
    return render_template("form.html", form=form, title="Your profile", subtitle=current_user.email, submit="Save changes")


@bp.get("/notifications")
@login_required
def notifications():
    records = Notification.query.filter_by(user_id=current_user.id, archived_at=None).order_by(Notification.created_at.desc())
    page = db.paginate(records.statement, page=max(1, request.args.get("page", 1, type=int)), per_page=15, error_out=False)
    return render_template("notifications.html", page=page, title="Notifications")


@bp.post("/notifications/<int:id>/read")
@login_required
def read_notification(id):
    record = db.get_or_404(Notification, id)
    if record.user_id != current_user.id:
        abort(404)
    record.is_read = True
    if request.form.get("archive") == "yes":
        record.archived_at, record.archive_reason = utcnow(), "Archived by recipient"
    record.audit(current_user.id, "Notification read/archived")
    db.session.commit()
    return redirect(url_for("main.notifications"))
