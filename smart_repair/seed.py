"""Fictional, idempotent demo data built through the same services as the UI."""
import base64
import json
from datetime import timedelta, time
from pathlib import Path

from flask import current_app

from .extensions import db
from .models import *
from .services.diagnosis import diagnose, save_results
from .services.workflow import assign_technician, local_now, transition, notify
from .services.stock import movement, reserve, consume, receive_order
from .services.billing import create_estimate, send_estimate, decide_estimate, issue_invoice, record_payment

DEMO_PASSWORD = "RepairDemo123!"


def add(model, **values):
    obj = model(**values)
    db.session.add(obj)
    db.session.flush()
    return obj


def seed_database():
    if User.query.first():
        return False
    today = local_now().date()
    roles = {name: add(Role, name=name, description=f"{name} workspace", is_system=True) for name in ("Admin", "Technician", "Customer")}

    def user(name, email, role):
        obj = User(full_name=name, email=email, is_active=True)
        obj.set_password(DEMO_PASSWORD)
        db.session.add(obj)
        db.session.flush()
        add(UserRole, user_id=obj.id, role_id=roles[role].id)
        return obj

    admin = user("Mehar Zain", "admin@smartrepair.test", "Admin")
    tech_user = user("Ali Hassan", "tech@smartrepair.test", "Technician")
    tech_user2 = user("Sara Ahmed", "tech2@smartrepair.test", "Technician")
    customer_user = user("Hamza Khan", "customer@smartrepair.test", "Customer")
    customer_user2 = user("Ayesha Malik", "customer2@smartrepair.test", "Customer")
    customer = add(CustomerProfile, user_id=customer_user.id, city="Lahore", address="12 Demo Street, Model Town", preferred_contact="Email")
    customer2 = add(CustomerProfile, user_id=customer_user2.id, city="Lahore", address="8 Sample Avenue, Gulberg", preferred_contact="Phone")
    center = add(ServiceCenter, name="Gulberg Repair Hub", city="Lahore", address="24 Main Boulevard, Gulberg III (fictional)",
        phone="+92 300 0000000", opening_time=time(9), closing_time=time(18))
    add(ServiceCenter, name="Johar Town Studio", city="Lahore", address="19 Service Lane, Johar Town (fictional)",
        phone="+92 300 0000001", opening_time=time(10), closing_time=time(19))
    skills = [add(Skill, name=name, description=f"Inspection and repair of {name.lower()}") for name in ["Mobile repair", "Computer repair", "Board diagnostics", "Display replacement"]]
    tech = add(TechnicianProfile, user_id=tech_user.id, service_center_id=center.id, employee_code="TECH-001",
        experience_years=6, bio="Phones, tablets and board-level diagnostics.", hire_date=today-timedelta(days=1100))
    tech2 = add(TechnicianProfile, user_id=tech_user2.id, service_center_id=center.id, employee_code="TECH-002",
        experience_years=4, bio="Computer diagnostics, thermal systems and storage.", hire_date=today-timedelta(days=700))
    for skill in [skills[0], skills[2], skills[3]]:
        add(TechnicianSkill, technician_id=tech.id, skill_id=skill.id, proficiency_level=5)
    for skill in [skills[1], skills[2]]:
        add(TechnicianSkill, technician_id=tech2.id, skill_id=skill.id, proficiency_level=4)
    for day in range(21):
        for t in [tech, tech2]:
            add(TechnicianAvailability, technician_id=t.id, available_date=today+timedelta(days=day), start_time=time(9), end_time=time(18))
    categories = [add(DeviceCategory, name=name, description=f"{name} diagnostics and repairs") for name in ["Smartphone", "Laptop", "Tablet", "Printer", "Television"]]
    brands = [add(DeviceBrand, name=name) for name in ["Apple", "Samsung", "Dell", "HP", "Lenovo", "Canon", "Sony"]]
    catalogue = [(0,0,"iPhone 14"),(1,0,"Galaxy S23"),(2,1,"XPS 13"),(3,1,"Pavilion 15"),(0,2,"iPad Air"),(4,1,"ThinkPad T14"),(5,3,"PIXMA G3010"),(6,4,"Bravia X80")]
    models = [add(DeviceModel, brand_id=brands[b].id, category_id=categories[c].id, model_name=name, release_year=2023) for b,c,name in catalogue]
    devices = []
    for i,m in enumerate(models):
        owner = customer if i % 2 == 0 else customer2
        devices.append(add(CustomerDevice, customer_id=owner.id, device_model_id=m.id,
            nickname=["Daily driver", "Work phone", "Design laptop", "Home laptop", "Study tablet", "Work laptop", "Home printer", "Living room TV"][i],
            serial_number=f"DEMO-DEV-{i+1:04d}", purchase_date=today-timedelta(days=400+i*20)))
    symptom_groups = [add(SymptomCategory, name=n) for n in ["Power & battery", "Display", "Performance", "Sound & cooling"]]
    symptom_specs = [(0,"No power"),(0,"Not charging"),(0,"Battery drains quickly"),(1,"Screen flickers"),(1,"Cracked display"),(2,"Slow performance"),(3,"Overheating"),(3,"Unusual noise"),(2,"Unexpected restart"),(1,"No display")]
    symptoms = [add(Symptom, category_id=symptom_groups[g].id, name=n, default_severity="Medium") for g,n in symptom_specs]
    rule_specs = [
        (0,"Charging port issue","Charging connection may be worn or obstructed.",[(1,4,True),(2,1,False)]),
        (0,"Battery degradation","A worn battery may cause rapid drain and unexpected shutdowns.",[(2,4,True),(8,2,False),(6,1,False)]),
        (1,"Power input / adapter issue","The power input or adapter may not be supplying enough power.",[(0,4,True),(1,3,False)]),
        (1,"Thermal cooling issue","Restricted airflow or a worn fan may cause heat and slow performance.",[(6,4,True),(7,2,False),(5,1,False)]),
        (0,"Display assembly damage","Visible cracks can damage the display and touch assembly.",[(4,5,True),(3,2,False)]),
        (1,"Storage or memory bottleneck","Storage and memory health should be checked before replacing parts.",[(5,4,True),(8,2,False)]),
        (2,"Tablet charging circuit issue","A power connection or charging circuit could need inspection.",[(1,3,True),(0,2,False)]),
        (3,"Printer feed or motor issue","An obstruction or worn feed mechanism may cause unusual noise.",[(7,4,True),(5,1,False)]),
        (4,"Display or backlight issue","The backlight, display cable or panel could need testing.",[(9,4,True),(3,2,False)]),
        (None,"Power delivery interruption","A missing power supply or internal connection may prevent startup.",[(0,3,True),(1,2,False)]),
        (None,"Display connection issue","Intermittent display symptoms may point to a cable or connector.",[(3,4,True),(9,2,False)]),
        (None,"System instability","Heat and background load can cause unexpected restarts.",[(8,3,True),(6,2,False),(5,1,False)]),
    ]
    for i,(category,fault,explanation,mappings) in enumerate(rule_specs):
        rule = add(DiagnosticRule, title=fault, category_id=categories[category].id if category is not None else None,
            probable_fault=fault, explanation=explanation, severity="High" if i in [2,4] else "Medium",
            estimated_minutes=45+i*10, priority=12-i, suggested_action="Book a technician inspection. Do not attempt electrical repairs while the device is powered.")
        for symptom,weight,required in mappings:
            add(DiagnosticRuleSymptom, rule_id=rule.id, symptom_id=symptoms[symptom].id, weight=weight, is_required=required)
    services = [add(Service, name=n, description=desc, base_price=price, estimated_minutes=minutes, required_skill_id=skill.id)
        for n,desc,price,minutes,skill in [
            ("Device inspection","Physical diagnostics and a written repair recommendation",1500,45,skills[2]),
            ("Component replacement","Labour for replacing and testing a device component",2500,90,skills[0]),
            ("Thermal service","Clean cooling system and refresh thermal compound",3000,60,skills[1]),
            ("System tune-up","Storage health checks and performance troubleshooting",2000,60,skills[1])]]
    supplier = add(Supplier, name="Circuit Supply Co.", contact_name="Demo Vendor", phone="+92 300 0000020", email="parts@example.test", address="Fictional electronics market, Lahore")
    part_specs = [("BAT-001","Phone battery",0,3000,4500,14),("PRT-002","USB-C charging port",0,900,1800,3),("DSP-003","OLED display",0,9500,13500,7),
        ("PWR-004","65W adapter",1,2500,3800,12),("FAN-005","Laptop cooling fan",1,1800,3000,2),("SSD-006","512GB SSD",1,6500,8500,10),
        ("RAM-007","8GB DDR4 memory",1,3200,4800,8),("THM-008","Thermal compound",1,400,800,20)]
    parts = []
    for sku,name,cat,cost,price,stock in part_specs:
        part = add(SparePart, sku=sku, name=name, compatible_category_id=categories[cat].id, unit_cost=cost, sale_price=price, quantity_on_hand=0, reorder_level=5)
        movement(part, stock, admin.id, "Opening", notes="Opening demo stock")
        parts.append(part)
    order = add(PurchaseOrder, supplier_id=supplier.id, created_by_user_id=admin.id, order_number="PO-DEMO-001", order_date=today-timedelta(days=2), expected_date=today+timedelta(days=3), status="Draft", total_amount=9000)
    add(PurchaseOrderItem, purchase_order_id=order.id, spare_part_id=parts[1].id, quantity_ordered=10, unit_cost=900, quantity_received=0)
    received = add(PurchaseOrder, supplier_id=supplier.id, created_by_user_id=admin.id, order_number="PO-DEMO-002", order_date=today-timedelta(days=7), status="Ordered", total_amount=5000)
    add(PurchaseOrderItem, purchase_order_id=received.id, spare_part_id=parts[3].id, quantity_ordered=2, unit_cost=2500, quantity_received=0)
    db.session.expire(received, ["items"])
    receive_order(received, admin.id)
    statuses = ["In Progress","Awaiting Approval","Inspection","Ready for Collection","Submitted","Assigned","Completed","On Hold","Under Review","Submitted","Completed","Awaiting Approval"]
    requests = []
    for i,target in enumerate(statuses):
        device = devices[i % len(devices)]
        owner = db.session.get(CustomerProfile, device.customer_id)
        symptom_ids = [symptoms[s].id for s in ([2,8] if i%3==0 else [0,1] if i%3==1 else [6,5])]
        record = add(RepairRequest, customer_id=owner.id, customer_device_id=device.id, service_center_id=center.id,
            request_code=f"SR-2026-{1041+i:04d}", issue_description=["Battery drains much faster than usual and the device sometimes restarts.","The device won't switch on or charge. Please inspect the power input.","The device gets unusually hot and slows down during normal use."][i%3],
            selected_symptoms=json.dumps(symptom_ids), urgency=["High","Normal","Urgent","Normal"][i%4],
            created_at=utcnow()-timedelta(days=i//2,hours=i), status="Submitted")
        record.audit(owner.user_id, "Fictional demonstration request created")
        save_results(record, diagnose(device.model.category_id, symptom_ids))
        requests.append(record)
        if target in {"Submitted", "Under Review"}:
            record.status = target
            continue
        selected_tech = tech2 if device.model.category.name == "Laptop" else tech
        job = assign_technician(record, selected_tech, admin.id, "Demo assignment after reviewing symptoms")
        db.session.expire(record, ["job"])
        if target == "Assigned":
            continue
        transition(job, "Inspection", selected_tech.user_id, "Physical inspection started")
        add(RepairNote, repair_job_id=job.id, author_user_id=selected_tech.user_id,
            note_text="Device received. We are checking the reported symptoms and component health.", is_customer_visible=True)
        add(RepairNote, repair_job_id=job.id, author_user_id=selected_tech.user_id,
            note_text="Internal demo note: verify serial and run bench checks before parts replacement.", is_customer_visible=False)
        add(RepairJobService, repair_job_id=job.id, service_id=services[0].id, quantity=1, agreed_unit_price=services[0].base_price)
        if target == "Inspection":
            continue
        estimate = create_estimate(job, admin.id, [("service",services[0].id,1),("service",services[1].id,1),("part",parts[0].id,1)], tax=425, discount=0)
        send_estimate(estimate, admin.id)
        if target == "Awaiting Approval":
            continue
        decide_estimate(estimate, owner.id, "approve", owner.user_id)
        transition(job, "In Progress", selected_tech.user_id, "Customer approved; repair work underway")
        reservation = reserve(parts[0], job, 1, admin.id)
        db.session.flush()
        db.session.expire(parts[0], ["reservations"])
        if target == "On Hold":
            transition(job, "On Hold", selected_tech.user_id, "Waiting for a specialist test fixture")
            continue
        if target == "In Progress":
            continue
        consume(reservation, selected_tech, selected_tech.user_id)
        transition(job, "Ready for Collection", selected_tech.user_id, "Repair tested and ready for collection")
        invoice = issue_invoice(job, admin.id)
        db.session.flush()
        db.session.expire(job, ["invoice"])
        if target == "Ready for Collection":
            record_payment(invoice, 3000, "Cash", admin.id)
            continue
        record_payment(invoice, invoice.total_amount, "Simulated", admin.id)
        transition(job, "Completed", admin.id, "Payment settled and device collected")
        add(Review, repair_job_id=job.id, customer_id=owner.id, rating=5,
            comment="Clear updates and a smooth repair. Fictional demonstration review.")
    # A future, non-conflicting demo appointment; scheduling dates use local Pakistan time.
    record = requests[4]
    from .services.workflow import book_appointment
    from datetime import datetime
    book_appointment(record, center, datetime.combine(today+timedelta(days=1),time(10)),
        datetime.combine(today+timedelta(days=1),time(10,30)), record.customer.user_id)
    folder = Path(current_app.config["UPLOAD_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)
    filename = "demo-sample.png"
    data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j4QAAAABJRU5ErkJggg==")
    (folder / filename).write_bytes(data)
    add(RepairAttachment, repair_request_id=requests[0].id, uploaded_by_user_id=requests[0].customer.user_id,
        file_name="demo-placeholder.png", file_path=filename, mime_type="image/png", file_size=len(data))
    notify(admin.id, "Welcome to Smart Repair", "Your demo workspace includes 40 related data models and repairs in several workflow stages.")
    notify(admin.id, "Stock needs attention", "USB-C charging ports and laptop cooling fans are at or below reorder level.")
    db.session.commit()
    return True
