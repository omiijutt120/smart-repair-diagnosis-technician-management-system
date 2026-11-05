from smart_repair.models import DiagnosticRule, DeviceCategory, Symptom
from smart_repair.services.diagnosis import diagnose


def test_weighted_ranking_and_required_symptoms(app):
    category = DeviceCategory.query.filter_by(name="Laptop").one()
    symptoms = [Symptom.query.filter_by(name=name).one().id for name in ["No power", "Not charging"]]
    results = diagnose(category.id, symptoms)
    assert results and results[0]["score"] == 100
    assert any(r["rule"].probable_fault == "Power input / adapter issue" for r in results)
    results = diagnose(category.id, [symptoms[1]])
    assert not any(r["rule"].probable_fault == "Power input / adapter issue" for r in results)


def test_no_match_and_disabled_rule(app):
    assert diagnose(1, []) == []
    assert diagnose(1, [999999]) == []
    from smart_repair.extensions import db
    for rule in DiagnosticRule.query.all():
        rule.is_active = False
    db.session.flush()
    assert diagnose(1, [1,2,3]) == []


def test_diagnosis_prg_and_intake(client, login):
    from smart_repair.models import User, CustomerDevice, RepairRequest
    login("customer")
    user = User.query.filter_by(email="customer@smartrepair.test").one()
    device = CustomerDevice.query.filter_by(customer_id=user.customer.id).first()
    response = client.post("/customer/diagnosis",data={"device_id":device.id,"symptom_ids":[1,2]})
    assert response.status_code == 302
    response = client.get(response.location)
    assert response.status_code == 200 and b"match score" in response.data
    response = client.post("/customer/requests/new",data={"device_id":device.id,"symptom_ids":[1,2],"service_center_id":1,"issue_description":"No power and not charging for two days.","urgency":"High"})
    assert response.status_code == 302
    record = RepairRequest.query.order_by(RepairRequest.id.desc()).first()
    assert record.results and record.customer_id == user.customer.id


def test_symptom_checkboxes_do_not_require_every_choice(client, login):
    import re
    login("customer")
    for route in ["/customer/diagnosis", "/customer/requests/new"]:
        response = client.get(route)
        inputs = re.findall(r'<input[^>]+name="symptom_ids"[^>]*>', response.data.decode())
        assert inputs and all("required" not in checkbox for checkbox in inputs)
    response = client.post("/customer/diagnosis", data={"device_id": 1})
    assert response.status_code == 200
    assert b"Select at least one symptom" in response.data
