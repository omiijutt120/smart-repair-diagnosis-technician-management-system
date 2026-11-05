from smart_repair.extensions import db
from .base import Record, fk, money, utcnow


class RepairRequest(Record, db.Model):
    __tablename__ = "repair_requests"
    customer_id = fk("customer_profiles")
    customer_device_id = fk("customer_devices")
    service_center_id = fk("service_centers", nullable=True)
    required_skill_id = fk("skills", nullable=True)
    request_code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    issue_description = db.Column(db.Text, nullable=False)
    selected_symptoms = db.Column(db.Text, nullable=False, default="[]")
    preferred_date = db.Column(db.Date)
    urgency = db.Column(db.String(20), nullable=False, default="Normal")
    status = db.Column(db.String(40), nullable=False, default="Submitted", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    customer = db.relationship("CustomerProfile")
    device = db.relationship("CustomerDevice")
    center = db.relationship("ServiceCenter")
    job = db.relationship("RepairJob", uselist=False, back_populates="request")
    results = db.relationship("DiagnosticResult")
    attachments = db.relationship("RepairAttachment")
    appointments = db.relationship("Appointment", order_by="Appointment.scheduled_start.desc()")


class RepairAttachment(Record, db.Model):
    __tablename__ = "repair_attachments"
    repair_request_id = fk("repair_requests")
    uploaded_by_user_id = fk("users")
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Appointment(Record, db.Model):
    __tablename__ = "appointments"
    repair_request_id = fk("repair_requests")
    service_center_id = fk("service_centers")
    scheduled_start = db.Column(db.DateTime, nullable=False, index=True)
    scheduled_end = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(25), nullable=False, default="Scheduled")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    request = db.relationship("RepairRequest", back_populates="appointments")
    center = db.relationship("ServiceCenter")
    __table_args__ = (db.CheckConstraint("scheduled_end > scheduled_start", name="appointment_order"),)


class TechnicianAvailability(Record, db.Model):
    __tablename__ = "technician_availability"
    technician_id = fk("technician_profiles")
    available_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    technician = db.relationship("TechnicianProfile")
    __table_args__ = (db.UniqueConstraint("technician_id", "available_date", "start_time", "end_time"),
                      db.CheckConstraint("end_time > start_time", name="availability_order"))


class TechnicianAssignment(Record, db.Model):
    __tablename__ = "technician_assignments"
    repair_request_id = fk("repair_requests")
    technician_id = fk("technician_profiles")
    assigned_by_user_id = fk("users")
    assigned_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    status = db.Column(db.String(30), nullable=False, default="Active")
    notes = db.Column(db.Text)
    technician = db.relationship("TechnicianProfile")
    request = db.relationship("RepairRequest")


class RepairJob(Record, db.Model):
    __tablename__ = "repair_jobs"
    repair_request_id = fk("repair_requests", unique=True)
    service_center_id = fk("service_centers")
    job_code = db.Column(db.String(40), unique=True, nullable=False)
    assigned_assignment_id = fk("technician_assignments", nullable=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(40), nullable=False, default="Assigned", index=True)
    warranty_days = db.Column(db.Integer, nullable=False, default=30)
    internal_cost = money()
    request = db.relationship("RepairRequest", back_populates="job")
    assignment = db.relationship("TechnicianAssignment")
    history = db.relationship("RepairStatusHistory", order_by="RepairStatusHistory.changed_at")
    notes = db.relationship("RepairNote", order_by="RepairNote.created_at.desc()")
    estimates = db.relationship("Estimate", order_by="Estimate.created_at.desc()")
    invoice = db.relationship("Invoice", uselist=False, back_populates="job")
    reservations = db.relationship("PartReservation")
    usages = db.relationship("RepairPartUsage")
    services = db.relationship("RepairJobService")
    reviews = db.relationship("Review")


class RepairStatusHistory(Record, db.Model):
    __tablename__ = "repair_status_history"
    repair_job_id = fk("repair_jobs")
    changed_by_user_id = fk("users")
    old_status = db.Column(db.String(40), nullable=False)
    new_status = db.Column(db.String(40), nullable=False)
    note = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    actor = db.relationship("User")


class RepairNote(Record, db.Model):
    __tablename__ = "repair_notes"
    repair_job_id = fk("repair_jobs")
    author_user_id = fk("users")
    note_text = db.Column(db.Text, nullable=False)
    is_customer_visible = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    author = db.relationship("User")


class RepairJobService(Record, db.Model):
    __tablename__ = "repair_job_services"
    repair_job_id = fk("repair_jobs")
    service_id = fk("services")
    quantity = db.Column(db.Integer, nullable=False, default=1)
    agreed_unit_price = money()
    service = db.relationship("Service")
    __table_args__ = (db.UniqueConstraint("repair_job_id", "service_id"),
                      db.CheckConstraint("quantity > 0 AND agreed_unit_price >= 0", name="valid_service_amount"))
