from decimal import Decimal

from smart_repair.extensions import db
from smart_repair.models import Invoice, Payment


def test_billing_page_is_scoped_and_role_protected(client, login):
    login("customer")
    response = client.get("/billing")
    assert response.status_code == 200
    assert b"Billing &amp; payments" in response.data
    assert b"Payment received" in response.data

    login("tech")
    assert client.get("/billing").status_code == 403


def test_admin_can_record_payment_received_from_billing(app, client, login):
    login("admin")
    with app.app_context():
        invoice = Invoice.query.filter(Invoice.status.in_(["Unpaid", "Partially Paid"])).first()
        assert invoice is not None
        invoice_id = invoice.id
        balance = invoice.balance
        before = Payment.query.filter_by(invoice_id=invoice_id, status="Completed").count()

    response = client.post(f"/admin/invoices/{invoice_id}/payment", data={
        "amount": str(balance),
        "method": "Cash",
        "reference": "TEST-RECEIPT-001",
        "return_to": "billing",
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/billing")

    with app.app_context():
        invoice = db.session.get(Invoice, invoice_id)
        assert invoice.status == "Paid"
        assert invoice.balance == Decimal("0.00")
        assert Payment.query.filter_by(invoice_id=invoice_id, status="Completed").count() == before + 1
