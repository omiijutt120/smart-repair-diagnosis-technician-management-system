from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from smart_repair.models import RepairRequest, RepairJob
from smart_repair.extensions import db


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if not any(current_user.has_role(role) for role in roles):
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def accessible_request(request_id):
    record = db.get_or_404(RepairRequest, request_id)
    if current_user.has_role("Admin"):
        return record
    if current_user.has_role("Customer") and current_user.customer and record.customer_id == current_user.customer.id:
        return record
    if current_user.has_role("Technician") and current_user.technician and record.job and record.job.assignment and record.job.assignment.status in {"Active", "Closed"} and record.job.assignment.technician_id == current_user.technician.id:
        return record
    abort(404)


def accessible_job(job_id):
    job = db.get_or_404(RepairJob, job_id)
    accessible_request(job.repair_request_id)
    return job
