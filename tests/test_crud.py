import pytest
from sqlalchemy import inspect, text

from smart_repair.extensions import db
from smart_repair.models import *


def test_all_40_models_populated_and_connected(app):
    assert len(MODELS) == len(db.metadata.tables) == 40
    assert set(inspect(db.engine).get_table_names()) == set(MODELS)
    edges = {name:set() for name in MODELS}
    for name,model in MODELS.items():
        assert model.query.count() > 0, name
        for foreign in model.__table__.foreign_keys:
            parent = foreign.column.table.name
            edges[name].add(parent)
            edges[parent].add(name)
    reached = set()
    pending = ["users"]
    while pending:
        name = pending.pop()
        if name not in reached:
            reached.add(name)
            pending.extend(edges[name]-reached)
    assert reached == set(MODELS)
    assert db.session.execute(text("PRAGMA foreign_key_check")).all() == []


def test_every_admin_list_detail_and_edit_screen_renders(client,login):
    from smart_repair.admin.policy import can_edit
    login("admin")
    assert client.get("/admin/data").status_code == 200
    for name,model in MODELS.items():
        record = model.query.first()
        response = client.get(f"/admin/{name}")
        assert response.status_code == 200, name
        response = client.get(f"/admin/{name}/{record.id}")
        assert response.status_code == 200, name
        if can_edit(name,record):
            assert client.get(f"/admin/{name}/{record.id}/edit").status_code == 200, name


def test_safe_catalogue_crud_and_association_delete(client,login):
    login("admin")
    response = client.post("/admin/skills/new",data={"name":"Console repair","description":"Demo console diagnostics","is_active":"y"})
    assert response.status_code == 302
    skill = Skill.query.filter_by(name="Console repair").one()
    response = client.post(f"/admin/skills/{skill.id}/edit",data={"name":"Game console repair","description":"Updated","is_active":"y"})
    assert response.status_code == 302
    assert skill.name == "Game console repair"
    response = client.post(f"/admin/skills/{skill.id}/delete",data={"reason":"Unused demonstration skill"})
    assert response.status_code == 302
    assert skill.archived_at and not skill.is_active
    tech = TechnicianProfile.query.first()
    new_skill = Skill(name="Temp test skill",is_active=True)
    db.session.add(new_skill); db.session.commit()
    response = client.post("/admin/technician_skills/new",data={"technician_id":tech.id,"skill_id":new_skill.id,"proficiency_level":3})
    assert response.status_code == 302
    link = TechnicianSkill.query.filter_by(skill_id=new_skill.id).one()
    assert client.post(f"/admin/technician_skills/{link.id}/delete",data={"reason":"Remove test association"}).status_code == 302
    assert db.session.get(TechnicianSkill,link.id) is None


def test_financial_and_history_tampering_blocked(client,login):
    login("admin")
    payment = Payment.query.first()
    before = payment.amount
    assert client.post(f"/admin/payments/{payment.id}/edit",data={"amount":1}).status_code == 302
    assert payment.amount == before
    history = RepairStatusHistory.query.first()
    assert client.post(f"/admin/repair_status_history/{history.id}/delete",data={"reason":"Try to erase history"}).status_code == 422
    assert db.session.get(RepairStatusHistory,history.id)


def test_duplicate_and_invalid_admin_fields(client,login):
    login("admin")
    assert client.post("/admin/skills/new",data={"name":"Mobile repair","is_active":"y"}).status_code == 409
    response = client.post("/admin/technician_skills/new",data={"technician_id":1,"skill_id":1,"proficiency_level":10})
    assert response.status_code == 200
    assert b"between 1 and 5" in response.data


def test_all_role_screens(client,login):
    paths = {
        "admin":["/dashboard","/repairs","/admin/reports","/admin/inventory","/notifications","/profile"],
        "customer":["/dashboard","/repairs","/customer/devices","/customer/diagnosis","/customer/requests/new","/customer/appointments","/notifications","/profile"],
        "tech":["/dashboard","/repairs","/technician/availability","/notifications","/profile"],
    }
    assert client.get("/").status_code == 200
    for role,routes in paths.items():
        login(role)
        for path in routes:
            assert client.get(path).status_code == 200,(role,path)
        for repair in RepairRequest.query.all():
            response = client.get(f"/customer/requests/{repair.id}")
            assert response.status_code in {200,404},(role,repair.id)
