from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from smart_repair.extensions import db
from smart_repair.forms import AvailabilityForm
from smart_repair.models import *
from smart_repair.security import roles_required, accessible_job
from smart_repair.services.workflow import BusinessError, transition, TECH_STATUSES, validate_availability, local_now
from smart_repair.services.stock import consume

bp = Blueprint("technician", __name__, url_prefix="/technician")


@bp.get("/jobs")
@roles_required("Technician")
def jobs():
    return redirect(url_for("main.repairs"))


@bp.get("/jobs/<int:id>")
@roles_required("Technician")
def job_detail(id):
    job = accessible_job(id)
    return redirect(url_for("customer.request_detail", id=job.repair_request_id))


@bp.post("/jobs/<int:id>/status")
@roles_required("Technician", "Admin")
def status(id):
    job = accessible_job(id)
    new_status = request.form.get("status", "")
    if not current_user.has_role("Admin") and new_status not in TECH_STATUSES:
        abort(403)
    transition(job, new_status, current_user.id, request.form.get("note", "").strip())
    db.session.commit()
    flash("Repair status updated and added to the timeline.", "success")
    return redirect(url_for("customer.request_detail", id=job.repair_request_id))


@bp.post("/jobs/<int:id>/notes")
@roles_required("Technician", "Admin")
def notes(id):
    job = accessible_job(id)
    text = request.form.get("note_text", "").strip()
    if not 2 <= len(text) <= 5000:
        raise BusinessError("A note must contain between 2 and 5,000 characters.")
    note = RepairNote(repair_job_id=id, author_user_id=current_user.id, note_text=text,
        is_customer_visible=request.form.get("is_customer_visible") == "on")
    note.audit(current_user.id, "Note added")
    db.session.add(note)
    db.session.commit()
    flash("Repair note added.", "success")
    return redirect(url_for("customer.request_detail", id=job.repair_request_id))


@bp.post("/jobs/<int:id>/parts")
@roles_required("Technician", "Admin")
def parts(id):
    job = accessible_job(id)
    reservation = db.get_or_404(PartReservation, request.form.get("reservation_id", type=int))
    if reservation.repair_job_id != job.id:
        abort(404)
    if not job.assignment:
        raise BusinessError("Assign a technician before recording parts usage.")
    tech = job.assignment.technician if current_user.has_role("Admin") else current_user.technician
    consume(reservation, tech, current_user.id)
    db.session.commit()
    flash("Reserved parts used. Stock movement recorded once.", "success")
    return redirect(url_for("customer.request_detail", id=job.repair_request_id))


@bp.route("/availability", methods=["GET", "POST"])
@roles_required("Technician")
def availability():
    form = AvailabilityForm()
    edit_id = request.args.get("edit", type=int)
    record = db.get_or_404(TechnicianAvailability, edit_id) if edit_id else None
    if record and record.technician_id != current_user.technician.id:
        abort(404)
    if record and request.method == "GET":
        form = AvailabilityForm(obj=record)
    if form.validate_on_submit():
        slot = record or TechnicianAvailability(technician_id=current_user.technician.id)
        form.populate_obj(slot)
        with db.session.no_autoflush:
            validate_availability(slot)
        slot.audit(current_user.id, "Availability saved")
        db.session.add(slot)
        db.session.commit()
        flash("Availability saved.", "success")
        return redirect(url_for("technician.availability"))
    slots = TechnicianAvailability.query.filter_by(technician_id=current_user.technician.id, archived_at=None).order_by(TechnicianAvailability.available_date).all()
    return render_template("availability.html", form=form, slots=slots, title="My availability", technician=current_user.technician)


@bp.post("/availability/<int:id>/delete")
@roles_required("Technician")
def delete_availability(id):
    slot = db.get_or_404(TechnicianAvailability, id)
    if slot.technician_id != current_user.technician.id:
        abort(404)
    if slot.available_date < local_now().date():
        raise BusinessError("Past availability is retained as history.")
    from smart_repair.admin.policy import check_availability_assignments
    check_availability_assignments(slot)
    slot.is_available, slot.archived_at = False, utcnow()
    slot.audit(current_user.id, "Availability removed")
    db.session.commit()
    flash("Availability removed.", "success")
    return redirect(url_for("technician.availability"))
