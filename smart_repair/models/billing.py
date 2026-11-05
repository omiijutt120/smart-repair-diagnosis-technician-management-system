from smart_repair.extensions import db
from .base import Record, fk, money, utcnow


class Estimate(Record, db.Model):
    __tablename__ = "estimates"
    repair_job_id = fk("repair_jobs")
    prepared_by_user_id = fk("users")
    estimate_number = db.Column(db.String(40), unique=True, nullable=False)
    labor_total = money()
    parts_total = money()
    tax_amount = money()
    discount_amount = money()
    grand_total = money()
    status = db.Column(db.String(25), nullable=False, default="Draft")
    valid_until = db.Column(db.Date, nullable=False)
    decided_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    lines = db.relationship("EstimateLine", back_populates="estimate")
    job = db.relationship("RepairJob", back_populates="estimates")
    __table_args__ = (db.CheckConstraint("labor_total >= 0 AND parts_total >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND grand_total >= 0", name="estimate_nonnegative"),)


class EstimateLine(Record, db.Model):
    __tablename__ = "estimate_lines"
    estimate_id = fk("estimates")
    service_id = fk("services", nullable=True)
    spare_part_id = fk("spare_parts", nullable=True)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = money()
    line_total = money()
    estimate = db.relationship("Estimate", back_populates="lines")
    __table_args__ = (db.CheckConstraint("(service_id IS NULL) != (spare_part_id IS NULL)", name="one_line_source"),
                      db.CheckConstraint("quantity > 0 AND unit_price >= 0 AND line_total >= 0", name="line_positive"))


class Invoice(Record, db.Model):
    __tablename__ = "invoices"
    repair_job_id = fk("repair_jobs", unique=True)
    estimate_id = fk("estimates", nullable=True)
    invoice_number = db.Column(db.String(40), unique=True, nullable=False)
    issued_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    due_date = db.Column(db.Date)
    subtotal = money()
    tax_amount = money()
    discount_amount = money()
    total_amount = money()
    status = db.Column(db.String(25), nullable=False, default="Unpaid")
    job = db.relationship("RepairJob", back_populates="invoice")
    estimate = db.relationship("Estimate")
    payments = db.relationship("Payment", back_populates="invoice")
    __table_args__ = (db.CheckConstraint("subtotal >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND total_amount >= 0", name="invoice_nonnegative"),)

    @property
    def paid(self):
        return sum((p.amount for p in self.payments if p.status == "Completed"), 0)

    @property
    def balance(self):
        return self.total_amount - self.paid


class Payment(Record, db.Model):
    __tablename__ = "payments"
    invoice_id = fk("invoices")
    received_by_user_id = fk("users", nullable=True)
    payment_reference = db.Column(db.String(80), unique=True)
    amount = money()
    method = db.Column(db.String(25), nullable=False)
    status = db.Column(db.String(25), nullable=False, default="Completed")
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    invoice = db.relationship("Invoice", back_populates="payments")
    __table_args__ = (db.CheckConstraint("amount > 0", name="payment_positive"),)


class Review(Record, db.Model):
    __tablename__ = "reviews"
    repair_job_id = fk("repair_jobs")
    customer_id = fk("customer_profiles")
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    __table_args__ = (db.UniqueConstraint("repair_job_id", "customer_id"),
                      db.CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"))


class Notification(Record, db.Model):
    __tablename__ = "notifications"
    user_id = fk("users")
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    channel = db.Column(db.String(20), nullable=False, default="In-app")
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    related_type = db.Column(db.String(40))
    related_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
