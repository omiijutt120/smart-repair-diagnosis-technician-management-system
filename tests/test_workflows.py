from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest

from smart_repair.extensions import db
from smart_repair.models import *
from smart_repair.services.workflow import BusinessError, transition, local_now, book_appointment, validate_availability, assign_technician
from smart_repair.services.stock import reserve, release_reservation, consume, receive_order, reverse_movement, movement
from smart_repair.services.billing import create_estimate, send_estimate, decide_estimate, issue_invoice, record_payment


def test_valid_transition_records_history_and_actor(app):
    job = RepairJob.query.filter_by(status="Assigned").first()
    before = RepairStatusHistory.query.filter_by(repair_job_id=job.id).count()
    transition(job,"Inspection",job.assignment.technician.user_id,"Bench inspection")
    db.session.flush()
    history = RepairStatusHistory.query.filter_by(repair_job_id=job.id).order_by(RepairStatusHistory.id.desc()).first()
    assert job.status == job.request.status == "Inspection"
    assert history.old_status == "Assigned" and history.new_status == "Inspection"
    assert history.changed_by_user_id == job.assignment.technician.user_id
    assert RepairStatusHistory.query.filter_by(repair_job_id=job.id).count() == before + 1


def test_invalid_and_unapproved_transitions(app):
    job = RepairJob.query.filter_by(status="Inspection").first()
    with pytest.raises(BusinessError): transition(job,"Completed",1)
    with pytest.raises(BusinessError): transition(job,"Approved",1)
    with pytest.raises(BusinessError): transition(job,"On Hold",1,"")


def test_booking_conflict_hours_and_availability_overlap(app):
    existing = Appointment.query.filter_by(status="Scheduled").first()
    from smart_repair.services.workflow import local_datetime
    record = RepairRequest.query.filter_by(status="Submitted").first()
    start = local_datetime(existing.scheduled_start).replace(tzinfo=None)
    end = local_datetime(existing.scheduled_end).replace(tzinfo=None)
    with pytest.raises(BusinessError): book_appointment(record, existing.center,start,end,record.customer.user_id)
    with pytest.raises(BusinessError): book_appointment(record, existing.center,start.replace(hour=7),end.replace(hour=8),1)
    slot = TechnicianAvailability(technician_id=1,available_date=local_now().date()+timedelta(days=1),start_time=time(10),end_time=time(12))
    with pytest.raises(BusinessError): validate_availability(slot)


def test_wrong_skill_and_unavailable_assignment(app):
    record = RepairRequest.query.filter_by(status="Submitted").first()
    tech = TechnicianProfile.query.first()
    computer_skill = Skill.query.filter_by(name="Computer repair").one()
    record.required_skill_id = computer_skill.id
    with pytest.raises(BusinessError): assign_technician(record,tech,1)
    record.required_skill_id = None
    tech.is_available = False
    with pytest.raises(BusinessError): assign_technician(record,tech,1)


def test_reservation_limits_release_and_consume_once(app):
    job = RepairJob.query.filter_by(status="In Progress").first()
    part = SparePart.query.filter_by(sku="RAM-007").one()
    start = part.quantity_on_hand
    with pytest.raises(BusinessError): reserve(part,job,part.available+1,1)
    reservation = reserve(part,job,2,1)
    assert part.available == start-2
    usage = consume(reservation,job.assignment.technician,1)
    db.session.flush()
    assert part.quantity_on_hand == start-2 and part.available == start-2
    with pytest.raises(BusinessError): consume(reservation,job.assignment.technician,1)
    second = reserve(part,job,1,1)
    release_reservation(second,1)
    with pytest.raises(BusinessError): release_reservation(second,1)
    assert part.quantity_on_hand == start-2


def test_order_receipt_is_idempotent_and_audited(app):
    order = PurchaseOrder.query.filter_by(status="Draft").first()
    item = order.items[0]
    start = item.part.quantity_on_hand
    receive_order(order,1)
    db.session.flush()
    assert item.part.quantity_on_hand == start+item.quantity_ordered
    assert item.quantity_received == item.quantity_ordered
    with pytest.raises(BusinessError): receive_order(order,1)
    assert item.part.quantity_on_hand == start+item.quantity_ordered


def test_adjustment_reversal_once(app):
    part = SparePart.query.first()
    before = part.quantity_on_hand
    tx = movement(part,3,1,"Adjustment",notes="Count correction")
    db.session.flush()
    reverse_movement(tx,1,"Incorrect stock count")
    db.session.flush()
    assert part.quantity_on_hand == before and tx.reversed_at
    with pytest.raises(BusinessError): reverse_movement(tx,1,"Second reversal")


def test_end_to_end_billing_approval_parts_payment_completion(app):
    job = RepairJob.query.filter_by(status="Inspection").first()
    service = Service.query.first()
    part = SparePart.query.filter_by(sku="RAM-007").one()
    estimate = create_estimate(job,1,[("service",service.id,2),("part",part.id,1)],tax=100,discount=50)
    assert estimate.grand_total == Decimal("7850.00")
    send_estimate(estimate,1)
    with pytest.raises(BusinessError): decide_estimate(estimate,999,"approve",1)
    decide_estimate(estimate,job.request.customer_id,"approve",job.request.customer.user_id)
    assert estimate.decided_at and job.status == "Approved"
    transition(job,"In Progress",job.assignment.technician.user_id)
    reservation = reserve(part,job,1,1)
    consume(reservation,job.assignment.technician,1)
    transition(job,"Ready for Collection",job.assignment.technician.user_id)
    invoice = issue_invoice(job,1)
    db.session.flush()
    db.session.expire(job,["invoice"])
    record_payment(invoice,2000,"Cash",1,"TEST-PARTIAL")
    assert invoice.status == "Partially Paid" and invoice.balance == Decimal("5850.00")
    with pytest.raises(BusinessError): record_payment(invoice,6000,"Cash",1)
    with pytest.raises(BusinessError): transition(job,"Completed",1)
    record_payment(invoice,invoice.balance,"Simulated",1)
    transition(job,"Completed",1,"Collected by customer")
    db.session.flush()
    assert invoice.status == "Paid" and job.completed_at


def test_review_requires_completed_owned_job(client,login):
    login("customer")
    job = RepairJob.query.filter_by(status="In Progress").first()
    response = client.post(f"/customer/jobs/{job.id}/review",data={"rating":5,"comment":"Too early"})
    assert response.status_code == 422
    other = next(j for j in RepairJob.query.filter_by(status="Completed").all() if j.request.customer.user.email == "customer@smartrepair.test")
    response = client.post(f"/customer/jobs/{other.id}/review",data={"rating":6,"comment":"Invalid rating"})
    assert response.status_code == 422


def test_upload_validation_and_download_ownership(client,login):
    from io import BytesIO
    login("customer")
    response = client.post("/customer/requests/new",data={"device_id":1,"service_center_id":1,"symptom_ids":[1],"issue_description":"The device no longer turns on.","urgency":"Normal","attachment":(BytesIO(b"not a real image"),"photo.png","image/png")},content_type="multipart/form-data")
    assert response.status_code == 422
