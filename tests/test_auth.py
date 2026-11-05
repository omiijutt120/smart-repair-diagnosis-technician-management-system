from smart_repair.extensions import db
from smart_repair.models import User


def test_registration_hash_and_duplicate(client):
    data = {"full_name": "New Customer", "email": "new@example.com", "password": "CustomerPass123", "confirm_password": "CustomerPass123", "phone": "+923001234567"}
    response = client.post("/auth/register", data=data)
    assert response.status_code == 302
    user = User.query.filter_by(email="new@example.com").one()
    assert user.customer and user.check_password("CustomerPass123")
    assert user.password_hash != "CustomerPass123"
    client.post("/auth/logout")
    response = client.post("/auth/register", data=data)
    assert response.status_code == 200
    assert b"already registered" in response.data


def test_invalid_registration_and_login_logout(client, login):
    response = client.post("/auth/register", data={"email":"invalid", "full_name":"A", "password":"x", "confirm_password":"y"})
    assert response.status_code == 200
    assert b"valid email" in response.data
    assert client.get("/dashboard").status_code == 302
    login("customer")
    assert client.get("/dashboard").status_code == 200
    assert client.get("/auth/logout").status_code == 405
    assert client.post("/auth/logout").status_code == 302
    assert client.get("/dashboard").status_code == 302


def test_csrf_required(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post("/auth/login", data={"email":"admin@smartrepair.test","password":"RepairDemo123!"})
    assert response.status_code == 400
    assert b"CSRF" in response.data


def test_role_checks_and_disabled_session(client, login):
    login("customer")
    assert client.get("/admin/data").status_code == 403
    assert client.post("/admin/inventory/adjust", data={"part_id":1,"quantity_change":5,"reason":"bad"}).status_code == 403
    assert client.get("/technician/availability").status_code == 403
    user = User.query.filter_by(email="customer@smartrepair.test").one()
    user.is_active = False
    db.session.commit()
    assert client.get("/dashboard").status_code == 302


def test_request_invoice_estimate_and_attachment_ownership(client, login):
    from smart_repair.models import RepairRequest, Invoice, RepairAttachment, Estimate, CustomerProfile
    login("customer2")
    owner = User.query.filter_by(email="customer@smartrepair.test").one().customer
    record = RepairRequest.query.filter_by(customer_id=owner.id).first()
    assert client.get(f"/customer/requests/{record.id}").status_code == 404
    attachment = RepairAttachment.query.filter_by(repair_request_id=record.id).first()
    assert attachment
    assert client.get(f"/customer/attachments/{attachment.id}").status_code == 404
    invoice = Invoice.query.join(__import__('smart_repair.models', fromlist=['RepairJob']).RepairJob).filter_by(repair_request_id=RepairRequest.query.filter_by(customer_id=owner.id,status="Completed").first().id).first()
    assert invoice
    assert client.get(f"/customer/invoices/{invoice.id}").status_code == 404


def test_server_side_session_cookie_contains_no_identity(client, login):
    login("customer")
    cookie = client.get_cookie("session")
    assert cookie and cookie.http_only and cookie.same_site == "Lax"
    assert "customer" not in cookie.value and "RepairDemo" not in cookie.value


def test_technician_cannot_open_unassigned_job(client, login):
    from smart_repair.models import RepairJob
    login("tech2")
    job = next(j for j in RepairJob.query.all() if j.assignment.technician.user.email == "tech@smartrepair.test")
    assert client.get(f"/technician/jobs/{job.id}").status_code == 404
    assert client.post(f"/technician/jobs/{job.id}/status",data={"status":"Inspection"}).status_code == 404
