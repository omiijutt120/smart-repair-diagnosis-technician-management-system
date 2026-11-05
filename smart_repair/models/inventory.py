from smart_repair.extensions import db
from .base import Record, fk, money, utcnow


class Supplier(Record, db.Model):
    __tablename__ = "suppliers"
    name = db.Column(db.String(120), nullable=False)
    contact_name = db.Column(db.String(100))
    phone = db.Column(db.String(25))
    email = db.Column(db.String(254))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class SparePart(Record, db.Model):
    __tablename__ = "spare_parts"
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    compatible_category_id = fk("device_categories", nullable=True)
    unit_cost = money()
    sale_price = money()
    quantity_on_hand = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, nullable=False, default=5)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    reservations = db.relationship("PartReservation", back_populates="part")
    __table_args__ = (db.CheckConstraint("quantity_on_hand >= 0 AND reorder_level >= 0 AND unit_cost >= 0 AND sale_price >= 0", name="stock_nonnegative"),)

    @property
    def available(self):
        return self.quantity_on_hand - sum(r.reserved_quantity for r in self.reservations if r.status == "Active")


class PurchaseOrder(Record, db.Model):
    __tablename__ = "purchase_orders"
    supplier_id = fk("suppliers")
    created_by_user_id = fk("users")
    order_number = db.Column(db.String(40), unique=True, nullable=False)
    order_date = db.Column(db.Date, nullable=False)
    expected_date = db.Column(db.Date)
    status = db.Column(db.String(25), nullable=False, default="Draft")
    total_amount = money()
    supplier = db.relationship("Supplier")
    items = db.relationship("PurchaseOrderItem", back_populates="order")


class PurchaseOrderItem(Record, db.Model):
    __tablename__ = "purchase_order_items"
    purchase_order_id = fk("purchase_orders")
    spare_part_id = fk("spare_parts")
    quantity_ordered = db.Column(db.Integer, nullable=False)
    unit_cost = money()
    quantity_received = db.Column(db.Integer, nullable=False, default=0)
    order = db.relationship("PurchaseOrder", back_populates="items")
    part = db.relationship("SparePart")
    __table_args__ = (db.CheckConstraint("quantity_ordered > 0 AND quantity_received >= 0 AND quantity_received <= quantity_ordered AND unit_cost >= 0", name="receipt_range"),)


class InventoryTransaction(Record, db.Model):
    __tablename__ = "inventory_transactions"
    spare_part_id = fk("spare_parts")
    performed_by_user_id = fk("users")
    transaction_type = db.Column(db.String(30), nullable=False)
    quantity_change = db.Column(db.Integer, nullable=False)
    reference_type = db.Column(db.String(40))
    reference_id = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    reversed_at = db.Column(db.DateTime)
    part = db.relationship("SparePart")


class PartReservation(Record, db.Model):
    __tablename__ = "part_reservations"
    repair_job_id = fk("repair_jobs")
    spare_part_id = fk("spare_parts")
    reserved_quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(25), nullable=False, default="Active")
    reserved_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    released_at = db.Column(db.DateTime)
    part = db.relationship("SparePart", back_populates="reservations")
    __table_args__ = (db.CheckConstraint("reserved_quantity > 0", name="reservation_positive"),)


class RepairPartUsage(Record, db.Model):
    __tablename__ = "repair_part_usages"
    repair_job_id = fk("repair_jobs")
    spare_part_id = fk("spare_parts")
    technician_id = fk("technician_profiles")
    reservation_id = fk("part_reservations", nullable=True, unique=True)
    quantity_used = db.Column(db.Integer, nullable=False)
    unit_cost_at_use = money()
    used_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    part = db.relationship("SparePart")
    __table_args__ = (db.CheckConstraint("quantity_used > 0 AND unit_cost_at_use >= 0", name="usage_positive"),)
