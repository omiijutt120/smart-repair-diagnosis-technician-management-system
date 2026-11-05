from smart_repair.extensions import db
from smart_repair.models import *
from .workflow import BusinessError


def movement(part, change, actor_id, kind, reference=None, notes=""):
    if part.quantity_on_hand + change < 0 or part.available + change < 0:
        raise BusinessError("This operation would make available stock negative.")
    part.quantity_on_hand += change
    tx = InventoryTransaction(spare_part_id=part.id, performed_by_user_id=actor_id,
        transaction_type=kind, quantity_change=change, notes=notes,
        reference_type=reference.__tablename__ if reference else None, reference_id=reference.id if reference else None)
    db.session.add(tx)
    part.audit(actor_id, f"Stock {change:+d}: {kind}. {notes}")
    return tx


def reserve(part, job, quantity, actor_id):
    if job.status in {"Completed", "Cancelled", "Rejected", "Ready for Collection"}:
        raise BusinessError("This job cannot reserve parts.")
    if quantity <= 0 or quantity > part.available or not part.is_active:
        raise BusinessError("Requested quantity exceeds available stock or is invalid.")
    reservation = PartReservation(repair_job_id=job.id, spare_part_id=part.id, reserved_quantity=quantity)
    reservation.audit(actor_id, f"Reserved {quantity} units")
    db.session.add(reservation)
    db.session.flush()
    db.session.expire(part, ["reservations"])
    return reservation


def release_reservation(reservation, actor_id):
    if reservation.status != "Active":
        raise BusinessError("This reservation has already been released or consumed.")
    reservation.status, reservation.released_at = "Released", utcnow()
    reservation.audit(actor_id, "Released reserved stock")


def consume(reservation, technician, actor_id):
    job = db.session.get(RepairJob, reservation.repair_job_id)
    if not job or job.status != "In Progress":
        raise BusinessError("Parts can be used only while an approved repair is In Progress.")
    if not job.assignment or job.assignment.technician_id != technician.id:
        raise BusinessError("Only the assigned technician may use reserved parts.")
    if reservation.status != "Active" or RepairPartUsage.query.filter_by(reservation_id=reservation.id).first():
        raise BusinessError("This reservation has already been consumed or released.")
    reservation.status = "Consumed"
    reservation.released_at = utcnow()
    db.session.flush()
    usage = RepairPartUsage(repair_job_id=job.id, spare_part_id=reservation.spare_part_id,
        technician_id=technician.id, reservation_id=reservation.id,
        quantity_used=reservation.reserved_quantity, unit_cost_at_use=reservation.part.unit_cost)
    db.session.add(usage)
    db.session.flush()
    movement(reservation.part, -usage.quantity_used, actor_id, "Usage", usage, "Reserved parts consumed")
    return usage


def receive_order(order, actor_id):
    if order.status not in {"Draft", "Ordered", "Partially Received"} or not order.items:
        raise BusinessError("Order has already been received, cancelled or has no items.")
    for item in order.items:
        remaining = item.quantity_ordered - item.quantity_received
        if remaining:
            item.quantity_received += remaining
            movement(item.part, remaining, actor_id, "Receipt", item, order.order_number)
    order.status = "Received"
    order.audit(actor_id, "All remaining order quantities received")


def reverse_movement(tx, actor_id, reason):
    if tx.reversed_at or tx.transaction_type == "Reversal" or not reason.strip():
        raise BusinessError("Movement is already reversed, is a reversal, or needs a reason.")
    if tx.transaction_type not in {"Adjustment", "Opening"}:
        raise BusinessError("Receipt and usage history must be retained. Record a justified stock adjustment for returns.")
    movement(tx.part, -tx.quantity_change, actor_id, "Reversal", tx, reason)
    tx.reversed_at = utcnow()
    tx.audit(actor_id, f"Reversed: {reason}")


# Imported lazily in workflow.transition to keep stock operations independent.
