from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from zoneinfo import ZoneInfo

from smart_repair.extensions import db
from smart_repair.models import *

LOCAL_TZ = ZoneInfo("Asia/Karachi")
TERMINAL = {"Completed", "Rejected", "Cancelled"}
TRANSITIONS = {
    "Submitted": {"Under Review", "Appointment Scheduled", "Assigned", "Rejected", "Cancelled"},
    "Under Review": {"Appointment Scheduled", "Assigned", "Rejected", "Cancelled"},
    "Appointment Scheduled": {"Under Review", "Assigned", "Cancelled"},
    "Assigned": {"Inspection", "Cancelled"},
    "Inspection": {"Awaiting Approval", "On Hold", "Rejected", "Cancelled"},
    "Awaiting Approval": {"Approved", "Rejected", "Cancelled"},
    "Approved": {"In Progress", "On Hold", "Cancelled"},
    "In Progress": {"On Hold", "Ready for Collection"},
    "On Hold": {"Inspection", "In Progress", "Cancelled"},
    "Ready for Collection": {"Completed"},
    "Completed": set(), "Rejected": set(), "Cancelled": set(),
}
TECH_STATUSES = {"Inspection", "In Progress", "On Hold", "Ready for Collection"}


class BusinessError(ValueError):
    pass


def code(prefix):
    return f"{prefix}-{uuid4().hex[:8].upper()}"


def decimal(value):
    try:
        number = Decimal(str(value)).quantize(Decimal("0.01"))
        if not number.is_finite() or abs(number) > Decimal("99999999.99"):
            raise InvalidOperation
        return number
    except (InvalidOperation, TypeError, ValueError):
        raise BusinessError("Enter a valid monetary amount.")


def local_now():
    return datetime.now(LOCAL_TZ)


def to_utc(value):
    return value.replace(tzinfo=LOCAL_TZ).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def local_datetime(value):
    return value.replace(tzinfo=ZoneInfo("UTC")).astimezone(LOCAL_TZ) if value else None


def notify(user_id, title, message, record=None):
    db.session.add(Notification(user_id=user_id, title=title, message=message,
        related_type=record.__tablename__ if record else None, related_id=record.id if record else None))


def notify_admins(title, message, record=None):
    for user in User.query.filter_by(is_active=True).all():
        if user.has_role("Admin"):
            notify(user.id, title, message, record)


def transition(job, new_status, actor_id, note="", via_estimate=False):
    old_status = job.status
    if new_status not in TRANSITIONS.get(old_status, set()):
        raise BusinessError(f"Cannot move from {old_status} to {new_status}.")
    if new_status in {"Rejected", "Cancelled", "On Hold"} and not note.strip():
        raise BusinessError("A reason is required for this status change.")
    if new_status in {"Awaiting Approval", "Approved"} and not via_estimate:
        raise BusinessError("Send an estimate and record the customer's decision to change this status.")
    if new_status in {"In Progress", "Ready for Collection"}:
        approved = Estimate.query.filter_by(repair_job_id=job.id, status="Approved").first()
        if not approved:
            raise BusinessError("Customer approval of an estimate is required before repair work.")
    if new_status == "Completed":
        if not job.invoice or job.invoice.status != "Paid":
            raise BusinessError("Issue an invoice and settle its balance before completing the repair.")
        job.completed_at = utcnow()
    if new_status == "Inspection" and not job.started_at:
        job.started_at = utcnow()
    job.status = new_status
    job.request.status = new_status
    job.request.updated_at = utcnow()
    db.session.add(RepairStatusHistory(repair_job_id=job.id, changed_by_user_id=actor_id,
        old_status=old_status, new_status=new_status, note=note))
    job.audit(actor_id, f"Status {old_status} → {new_status}: {note}")
    if new_status in TERMINAL:
        from .stock import release_reservation
        for reservation in job.reservations:
            if reservation.status == "Active":
                release_reservation(reservation, actor_id)
        if job.assignment:
            job.assignment.status = "Closed"
        for appointment in job.request.appointments:
            if appointment.status == "Scheduled":
                appointment.status = "Completed" if new_status == "Completed" else "Cancelled"
                appointment.audit(actor_id, f"Repair {new_status}")
    notify(job.request.customer.user_id, "Repair status updated", f"{job.request.request_code}: {new_status}", job.request)


def request_status(repair_request, new_status, actor_id, reason=""):
    if repair_request.job:
        transition(repair_request.job, new_status, actor_id, reason)
    else:
        if new_status not in TRANSITIONS.get(repair_request.status, set()):
            raise BusinessError("This request cannot be moved to that status.")
        if new_status in {"Cancelled", "Rejected"} and not reason.strip():
            raise BusinessError("Please provide a reason.")
        repair_request.audit(actor_id, f"Status {repair_request.status} → {new_status}: {reason}")
        repair_request.status = new_status
        notify(repair_request.customer.user_id, "Request updated", f"{repair_request.request_code}: {new_status}", repair_request)


def validate_availability(slot):
    if slot.end_time <= slot.start_time or slot.available_date < local_now().date():
        raise BusinessError("Availability must be in the future and end after its start.")
    tech = db.session.get(TechnicianProfile, slot.technician_id)
    if not tech or tech.archived_at or not tech.user.is_active:
        raise BusinessError("Choose an active technician.")
    if slot.start_time < tech.center.opening_time or slot.end_time > tech.center.closing_time:
        raise BusinessError("Availability must fit within centre opening hours.")
    query = TechnicianAvailability.query.filter(
        TechnicianAvailability.technician_id == slot.technician_id,
        TechnicianAvailability.available_date == slot.available_date,
        TechnicianAvailability.archived_at.is_(None), TechnicianAvailability.is_available.is_(True),
        TechnicianAvailability.start_time < slot.end_time, TechnicianAvailability.end_time > slot.start_time)
    if slot.id:
        query = query.filter(TechnicianAvailability.id != slot.id)
    if query.first():
        raise BusinessError("This availability overlaps an existing slot.")


def book_appointment(repair_request, center, start, end, actor_id, appointment=None):
    if repair_request.status in TERMINAL or repair_request.status not in {"Submitted", "Under Review", "Appointment Scheduled"}:
        raise BusinessError("Appointments may only be changed before technician assignment.")
    if not center.is_active or center.archived_at:
        raise BusinessError("This service centre is unavailable.")
    if start <= local_now().replace(tzinfo=None) or end <= start or start.date() != end.date():
        raise BusinessError("Choose a future slot ending after it starts on the same day.")
    if start.time() < center.opening_time or end.time() > center.closing_time:
        raise BusinessError("The appointment must fit within centre opening hours.")
    utc_start, utc_end = to_utc(start), to_utc(end)
    conflicts = Appointment.query.filter(Appointment.service_center_id == center.id,
        Appointment.status == "Scheduled", Appointment.scheduled_start < utc_end,
        Appointment.scheduled_end > utc_start, Appointment.archived_at.is_(None))
    if appointment:
        conflicts = conflicts.filter(Appointment.id != appointment.id)
    if conflicts.first():
        raise BusinessError("This slot is already booked. Please choose another time.")
    duplicate = Appointment.query.filter_by(repair_request_id=repair_request.id, status="Scheduled").first()
    if duplicate and (not appointment or duplicate.id != appointment.id):
        raise BusinessError("Reschedule or cancel the existing appointment first.")
    if not appointment:
        appointment = Appointment(repair_request_id=repair_request.id)
        db.session.add(appointment)
    appointment.audit(actor_id, f"Scheduled {start.isoformat()} to {end.isoformat()} Asia/Karachi")
    appointment.service_center_id = center.id
    appointment.scheduled_start, appointment.scheduled_end = utc_start, utc_end
    appointment.status = "Scheduled"
    repair_request.service_center_id = center.id
    if repair_request.status != "Appointment Scheduled":
        request_status(repair_request, "Appointment Scheduled", actor_id, "Appointment booked")
    notify_admins("Appointment booked", f"{repair_request.request_code} · {start:%d %b, %H:%M} PKT", repair_request)
    return appointment


def assign_technician(repair_request, tech, actor_id, notes=""):
    if repair_request.status in TERMINAL or repair_request.status not in {"Submitted", "Under Review", "Appointment Scheduled", "Assigned", "Inspection", "On Hold"}:
        raise BusinessError("This repair is not eligible for assignment.")
    if not tech.is_available or tech.archived_at or not tech.user.is_active:
        raise BusinessError("This technician is unavailable.")
    if repair_request.service_center_id != tech.service_center_id:
        raise BusinessError("The technician must belong to the request's service centre.")
    if repair_request.required_skill_id and not any(s.skill_id == repair_request.required_skill_id and not s.archived_at for s in tech.skills):
        raise BusinessError("This technician does not have the required repair skill.")
    scheduled = next((a for a in repair_request.appointments if a.status == "Scheduled"), None)
    if scheduled:
        start = local_datetime(scheduled.scheduled_start).replace(tzinfo=None)
        end = local_datetime(scheduled.scheduled_end).replace(tzinfo=None)
        slots = TechnicianAvailability.query.filter_by(technician_id=tech.id, available_date=start.date(), is_available=True).all()
        if not any(not s.archived_at and s.start_time <= start.time() and s.end_time >= end.time() for s in slots):
            raise BusinessError("Technician has no availability covering this appointment.")
        for other in TechnicianAssignment.query.filter_by(technician_id=tech.id, status="Active").all():
            if other.repair_request_id == repair_request.id:
                continue
            for appt in other.request.appointments:
                if appt.status == "Scheduled" and appt.scheduled_start < scheduled.scheduled_end and appt.scheduled_end > scheduled.scheduled_start:
                    raise BusinessError("Technician already has an overlapping assignment.")
    else:
        today = local_now().date()
        if not TechnicianAvailability.query.filter(TechnicianAvailability.technician_id == tech.id,
            TechnicianAvailability.available_date >= today, TechnicianAvailability.is_available.is_(True),
            TechnicianAvailability.archived_at.is_(None)).first():
            raise BusinessError("Technician has no upcoming availability. Add a slot before assignment.")
    for old in TechnicianAssignment.query.filter_by(repair_request_id=repair_request.id, status="Active").all():
        old.status = "Reassigned"
        old.audit(actor_id, "Reassigned to another technician")
    assignment = TechnicianAssignment(repair_request_id=repair_request.id, technician_id=tech.id,
        assigned_by_user_id=actor_id, notes=notes)
    db.session.add(assignment)
    db.session.flush()
    job = repair_request.job
    if not job:
        previous = repair_request.status
        job = RepairJob(repair_request_id=repair_request.id, service_center_id=tech.service_center_id,
            job_code=code("JOB"), assigned_assignment_id=assignment.id, status="Assigned")
        db.session.add(job)
        db.session.flush()
        repair_request.status = "Assigned"
        db.session.add(RepairStatusHistory(repair_job_id=job.id, changed_by_user_id=actor_id,
            old_status=previous, new_status="Assigned", note=notes or f"Assigned to {tech.user.full_name}"))
    else:
        job.assigned_assignment_id = assignment.id
    job.audit(actor_id, f"Assigned technician {tech.employee_code}. {notes}")
    notify(tech.user_id, "New assignment", f"{repair_request.request_code} has been assigned to you.", repair_request)
    notify(repair_request.customer.user_id, "Technician assigned", f"{tech.user.full_name} will inspect your device.", repair_request)
    return job
