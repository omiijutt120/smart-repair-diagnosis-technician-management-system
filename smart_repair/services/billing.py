from datetime import timedelta
from decimal import Decimal

from smart_repair.extensions import db
from smart_repair.models import *
from .workflow import BusinessError, code, decimal, local_now, notify, transition


def recalculate(estimate):
    labor, parts = Decimal("0"), Decimal("0")
    for line in estimate.lines:
        if line.archived_at:
            continue
        line.line_total = decimal(line.quantity * line.unit_price)
        if line.service_id:
            labor += line.line_total
        else:
            parts += line.line_total
    estimate.labor_total, estimate.parts_total = labor, parts
    total = labor + parts + decimal(estimate.tax_amount or 0) - decimal(estimate.discount_amount or 0)
    if total < 0:
        raise BusinessError("Discount cannot exceed the estimate subtotal and tax.")
    estimate.grand_total = total


def create_estimate(job, actor_id, lines, tax=0, discount=0, valid_until=None):
    if job.status not in {"Inspection", "On Hold"}:
        raise BusinessError("Inspect the device before preparing an estimate.")
    if Estimate.query.filter(Estimate.repair_job_id == job.id, Estimate.status.in_(["Sent", "Approved"])).first():
        raise BusinessError("This job already has a sent or approved estimate.")
    if not lines or decimal(tax) < 0 or decimal(discount) < 0:
        raise BusinessError("Include at least one line and non-negative tax/discount.")
    expiry = valid_until or local_now().date() + timedelta(days=7)
    if expiry < local_now().date():
        raise BusinessError("Estimate expiry must not be in the past.")
    estimate = Estimate(repair_job_id=job.id, prepared_by_user_id=actor_id,
        estimate_number=code("EST"), tax_amount=decimal(tax), discount_amount=decimal(discount),
        valid_until=expiry, status="Draft")
    db.session.add(estimate)
    db.session.flush()
    for kind, source_id, quantity in lines:
        if quantity <= 0:
            raise BusinessError("Line quantities must be greater than zero.")
        source = db.session.get(Service if kind == "service" else SparePart, source_id)
        if not source or not source.is_active or source.archived_at:
            raise BusinessError("Choose an active service or part.")
        line = EstimateLine(estimate_id=estimate.id, description=source.name, quantity=quantity,
            unit_price=source.base_price if kind == "service" else source.sale_price,
            service_id=source.id if kind == "service" else None,
            spare_part_id=source.id if kind != "service" else None)
        db.session.add(line)
    db.session.flush()
    recalculate(estimate)
    return estimate


def send_estimate(estimate, actor_id):
    if estimate.status != "Draft" or not estimate.lines:
        raise BusinessError("Only a draft estimate with line items may be sent.")
    if estimate.valid_until < local_now().date():
        raise BusinessError("Update the expired draft's validity date before sending.")
    if estimate.job.status == "On Hold":
        transition(estimate.job, "Inspection", actor_id, "Inspection resumed to prepare estimate")
    recalculate(estimate)
    estimate.status = "Sent"
    estimate.audit(actor_id, "Sent for customer approval")
    transition(estimate.job, "Awaiting Approval", actor_id, estimate.estimate_number, via_estimate=True)
    notify(estimate.job.request.customer.user_id, "Estimate ready", f"{estimate.estimate_number} is ready for your decision.", estimate.job.request)


def decide_estimate(estimate, customer_id, decision, actor_id):
    if estimate.job.request.customer_id != customer_id:
        raise BusinessError("This estimate belongs to another customer.")
    if decision not in {"approve", "reject"} or estimate.status != "Sent" or estimate.valid_until < local_now().date():
        raise BusinessError("Estimate is no longer awaiting a valid decision.")
    estimate.status = "Approved" if decision == "approve" else "Rejected"
    estimate.decided_at = utcnow()
    estimate.audit(actor_id, f"Customer {decision}")
    transition(estimate.job, estimate.status, actor_id, f"Customer {decision}d {estimate.estimate_number}", via_estimate=True)


def issue_invoice(job, actor_id):
    if job.status != "Ready for Collection" or job.invoice:
        raise BusinessError("An invoice can be issued once when the job is Ready for Collection.")
    estimate = Estimate.query.filter_by(repair_job_id=job.id, status="Approved").first()
    if not estimate:
        raise BusinessError("An approved estimate is required.")
    invoice = Invoice(repair_job_id=job.id, estimate_id=estimate.id, invoice_number=code("INV"),
        subtotal=estimate.labor_total + estimate.parts_total, tax_amount=estimate.tax_amount,
        discount_amount=estimate.discount_amount, total_amount=estimate.grand_total,
        due_date=local_now().date() + timedelta(days=7), status="Paid" if estimate.grand_total == 0 else "Unpaid")
    invoice.audit(actor_id, "Issued from approved estimate")
    db.session.add(invoice)
    notify(job.request.customer.user_id, "Invoice issued", f"{invoice.invoice_number}: PKR {invoice.total_amount:,.2f}", job.request)
    return invoice


def record_payment(invoice, amount, method, actor_id, reference=None):
    amount = decimal(amount)
    if invoice.status in {"Void", "Paid"} or amount <= 0 or amount > invoice.balance:
        raise BusinessError("Payment must be positive and cannot exceed the outstanding balance.")
    if method not in {"Cash", "Bank transfer", "Simulated"}:
        raise BusinessError("Choose Cash, Bank transfer or Simulated.")
    payment = Payment(invoice_id=invoice.id, received_by_user_id=actor_id, amount=amount,
        method=method, payment_reference=reference or code("PAY"), status="Completed", paid_at=utcnow())
    payment.audit(actor_id, "Manual payment recorded; no card or banking credentials collected")
    db.session.add(payment)
    db.session.flush()
    db.session.expire(invoice, ["payments"])
    invoice.status = "Paid" if invoice.balance == 0 else "Partially Paid"
    notify(invoice.job.request.customer.user_id, "Payment recorded", f"PKR {amount:,.2f} received for {invoice.invoice_number}.", invoice.job.request)
    return payment


def refund_payment(payment, actor_id, reason):
    if payment.status != "Completed" or not reason.strip():
        raise BusinessError("Only completed payments can be refunded, with a reason.")
    if payment.invoice.job.status == "Completed":
        raise BusinessError("Completed jobs retain their settled billing. Contact the manager for an offline refund review.")
    payment.status = "Refunded"
    payment.audit(actor_id, f"Manual refund recorded: {reason}")
    db.session.flush()
    payment.invoice.status = "Partially Paid" if payment.invoice.paid else "Unpaid"
