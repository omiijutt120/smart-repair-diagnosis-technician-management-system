from smart_repair.extensions import db
from .base import Record, fk, money, utcnow


class DeviceCategory(Record, db.Model):
    __tablename__ = "device_categories"
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class DeviceBrand(Record, db.Model):
    __tablename__ = "device_brands"
    name = db.Column(db.String(80), unique=True, nullable=False)
    website = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class DeviceModel(Record, db.Model):
    __tablename__ = "device_models"
    brand_id = fk("device_brands")
    category_id = fk("device_categories")
    model_name = db.Column(db.String(100), nullable=False)
    release_year = db.Column(db.Integer)
    brand = db.relationship("DeviceBrand")
    category = db.relationship("DeviceCategory")
    __table_args__ = (db.UniqueConstraint("brand_id", "model_name"),)


class CustomerDevice(Record, db.Model):
    __tablename__ = "customer_devices"
    customer_id = fk("customer_profiles")
    device_model_id = fk("device_models")
    serial_number = db.Column(db.String(100))
    purchase_date = db.Column(db.Date)
    nickname = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text)
    model = db.relationship("DeviceModel")
    customer = db.relationship("CustomerProfile")


class SymptomCategory(Record, db.Model):
    __tablename__ = "symptom_categories"
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Symptom(Record, db.Model):
    __tablename__ = "symptoms"
    category_id = fk("symptom_categories")
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    default_severity = db.Column(db.String(20), default="Medium", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    category = db.relationship("SymptomCategory")


class DiagnosticRule(Record, db.Model):
    __tablename__ = "diagnostic_rules"
    title = db.Column(db.String(150), nullable=False)
    category_id = fk("device_categories", nullable=True)
    probable_fault = db.Column(db.String(200), nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    suggested_action = db.Column(db.Text, nullable=False, default="Book a technician inspection.")
    severity = db.Column(db.String(20), nullable=False, default="Medium")
    estimated_minutes = db.Column(db.Integer, nullable=False, default=60)
    confidence_score = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    priority = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    category = db.relationship("DeviceCategory")
    mappings = db.relationship("DiagnosticRuleSymptom", back_populates="rule")


class DiagnosticRuleSymptom(Record, db.Model):
    __tablename__ = "diagnostic_rule_symptoms"
    rule_id = fk("diagnostic_rules")
    symptom_id = fk("symptoms")
    weight = db.Column(db.Integer, nullable=False, default=1)
    is_required = db.Column(db.Boolean, nullable=False, default=False)
    rule = db.relationship("DiagnosticRule", back_populates="mappings")
    symptom = db.relationship("Symptom")
    __table_args__ = (db.UniqueConstraint("rule_id", "symptom_id"),
                      db.CheckConstraint("weight > 0", name="positive_weight"))


class DiagnosticResult(Record, db.Model):
    __tablename__ = "diagnostic_results"
    repair_request_id = fk("repair_requests")
    rule_id = fk("diagnostic_rules", nullable=True)
    result_summary = db.Column(db.Text, nullable=False)
    confidence_score = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    suggested_action = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    rule = db.relationship("DiagnosticRule")


class Service(Record, db.Model):
    __tablename__ = "services"
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text)
    base_price = money()
    estimated_minutes = db.Column(db.Integer, nullable=False, default=60)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    required_skill_id = fk("skills", nullable=True)
    __table_args__ = (db.CheckConstraint("base_price >= 0", name="price_nonnegative"),)
