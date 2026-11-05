from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from smart_repair.extensions import db
from .base import Record, fk, utcnow


class Role(Record, db.Model):
    __tablename__ = "roles"
    name = db.Column(db.String(40), nullable=False, unique=True)
    description = db.Column(db.Text)
    is_system = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class User(UserMixin, Record, db.Model):
    __tablename__ = "users"
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(25), unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    roles = db.relationship("Role", secondary="user_roles", viewonly=True, lazy="selectin")
    customer = db.relationship("CustomerProfile", uselist=False, back_populates="user")
    technician = db.relationship("TechnicianProfile", uselist=False, back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, name):
        return self.is_active and not self.archived_at and any(r.name == name and not r.archived_at for r in self.roles)

    @property
    def role_name(self):
        return next((r for r in ("Admin", "Technician", "Customer") if self.has_role(r)), "Customer")


class UserRole(Record, db.Model):
    __tablename__ = "user_roles"
    user_id = fk("users")
    role_id = fk("roles")
    assigned_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "role_id"),)


class CustomerProfile(Record, db.Model):
    __tablename__ = "customer_profiles"
    user_id = fk("users", unique=True)
    address = db.Column(db.Text)
    city = db.Column(db.String(80))
    preferred_contact = db.Column(db.String(20), nullable=False, default="Email")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    user = db.relationship("User", back_populates="customer")


class ServiceCenter(Record, db.Model):
    __tablename__ = "service_centers"
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(25))
    opening_time = db.Column(db.Time, nullable=False)
    closing_time = db.Column(db.Time, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    __table_args__ = (db.CheckConstraint("closing_time > opening_time", name="hours_order"),)


class TechnicianProfile(Record, db.Model):
    __tablename__ = "technician_profiles"
    user_id = fk("users", unique=True)
    service_center_id = fk("service_centers")
    employee_code = db.Column(db.String(40), unique=True, nullable=False)
    experience_years = db.Column(db.Integer, nullable=False, default=0)
    bio = db.Column(db.Text)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    hire_date = db.Column(db.Date)
    user = db.relationship("User", back_populates="technician")
    center = db.relationship("ServiceCenter")
    skills = db.relationship("TechnicianSkill", back_populates="technician")
    __table_args__ = (db.CheckConstraint("experience_years >= 0", name="experience_nonnegative"),)


class Skill(Record, db.Model):
    __tablename__ = "skills"
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class TechnicianSkill(Record, db.Model):
    __tablename__ = "technician_skills"
    technician_id = fk("technician_profiles")
    skill_id = fk("skills")
    proficiency_level = db.Column(db.Integer, nullable=False, default=3)
    technician = db.relationship("TechnicianProfile", back_populates="skills")
    skill = db.relationship("Skill")
    __table_args__ = (db.UniqueConstraint("technician_id", "skill_id"),
                      db.CheckConstraint("proficiency_level BETWEEN 1 AND 5", name="proficiency_range"))
