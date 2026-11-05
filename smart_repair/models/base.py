from datetime import datetime, timezone

from smart_repair.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fk(table, nullable=False, unique=False):
    return db.Column(db.Integer, db.ForeignKey(f"{table}.id", ondelete="RESTRICT"),
                     nullable=nullable, unique=unique, index=True)


def money(default=0):
    return db.Column(db.Numeric(10, 2), nullable=False, default=default)


class Record:
    id = db.Column(db.Integer, primary_key=True)
    archived_at = db.Column(db.DateTime)
    archive_reason = db.Column(db.Text)
    audit_log = db.Column(db.Text, nullable=False, default="")

    def __str__(self):
        for key in ("full_name", "name", "title", "request_code", "job_code", "invoice_number",
                    "estimate_number", "order_number", "model_name", "employee_code", "description"):
            value = getattr(self, key, None)
            if value:
                return f"{value} · #{self.id}"
        return f"{type(self).__name__} #{self.id}"

    def audit(self, actor_id, action):
        self.audit_log = (self.audit_log or "") + f"{utcnow().isoformat()} UTC | user {actor_id} | {action}\n"
