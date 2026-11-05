from pathlib import Path
from html import escape

from sqlalchemy.schema import CreateTable

from .models import MODELS
from .extensions import db


def generate_schema_docs():
    root = Path(__file__).resolve().parent.parent / "docs"
    root.mkdir(exist_ok=True)
    mermaid = ["erDiagram"]
    for name, model in MODELS.items():
        mermaid.append(f"    {name} {{")
        for col in model.__table__.columns:
            if col.primary_key or col.foreign_keys:
                mermaid.append(f"        int {col.name} {'PK' if col.primary_key else 'FK'}")
        mermaid.append("    }")
        for fk in model.__table__.foreign_keys:
            mermaid.append(f'    {fk.column.table.name} ||--o{{ {name} : "{fk.parent.name}"')
    (root / "ERD.md").write_text("# Database: 40 related domain models\n\n```mermaid\n" + "\n".join(mermaid) + "\n```\n", encoding="utf-8")
    schema = "\n\n".join(str(CreateTable(t).compile(db.engine)) + ";" for t in db.metadata.sorted_tables)
    (root / "schema.sql").write_text("\n".join(line.rstrip() for line in schema.splitlines()).strip() + "\n", encoding="utf-8")
    from .admin.policy import EDIT_FIELDS, WORKFLOW_GUIDE
    rows = ["# CRUD and history coverage", "", "All 40 resources have an administrator paginated list and detail view. Every mutation requires an administrator role and CSRF, or an explicitly owned customer/technician workflow.", "", "| # | Model / table | Create and update | Controlled removal |", "|---|---|---|---|"]
    for index,(name,model) in enumerate(MODELS.items(),1):
        action = WORKFLOW_GUIDE.get(name, "Validated administrator form; customer devices and profiles also have ownership-protected forms.")
        removal = "Archive/deactivate with a reason; unreferenced association and draft lines can be deleted. Linked records are restricted."
        if name in {"repair_status_history", "repair_part_usages"}:
            removal = "Append-only: retained permanently. Corrections use notes, permitted transitions or compensating stock adjustments."
        elif name == "payments":
            removal = "Refund with a reason before job completion; retain the original payment. Completed-job refunds require offline manager review."
        elif name == "inventory_transactions":
            removal = "Reverse opening/adjustment stock with a compensating transaction and a reason; receipts/usages retain source history."
        elif name == "invoices":
            removal = "Void an unpaid invoice with a reason; no destructive deletion. A voided invoice remains the one final invoice for that job."
        elif name == "technician_assignments":
            removal = "Reassign to close the old assignment and link the replacement to the work order."
        rows.append(f"| {index} | `{name}` / {model.__name__} | {action} | {removal} |")
    rows += ["", "Core historical fields cannot be arbitrarily edited. This implements the PRD's safe CRUD exceptions rather than allowing invalid financial/stock/status changes.", "", "Archive metadata and per-record audit logs store the actor, UTC time and reason. The 40 domain tables are separate from Alembic's migration-version metadata table."]
    (root / "CRUD_COVERAGE.md").write_text("\n".join(rows), encoding="utf-8")
    cards = []
    for i,(name,model) in enumerate(MODELS.items(),1):
        fields = "".join(f"<li><code>{escape(c.name)}</code><span>{'PK' if c.primary_key else '→ '+escape(next(iter(c.foreign_keys)).target_fullname) if c.foreign_keys else escape(str(c.type))}</span></li>" for c in model.__table__.columns if c.name not in {"audit_log","archive_reason","archived_at"})
        cards.append(f'<article><header><span>{i:02}</span><h2>{name}</h2></header><ul>{fields}</ul></article>')
    html = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Smart Repair · 40-model schema</title><style>body{margin:0;background:#f6f7f8;font:12px Segoe UI,Arial;color:#333}body>header{padding:40px;background:#0a0a0d;color:white}h1{font-size:30px;margin:0 0 10px}body>header p{color:#b7ff3c}main{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;padding:25px}article{background:white;border:1px solid #ddd;border-radius:10px;overflow:hidden;align-self:start}article header{display:flex;align-items:center;gap:10px;background:#141a0e;color:white;padding:14px}article header span{color:#b7ff3c}h2{font-size:12px;margin:0}ul{list-style:none;padding:10px 14px;margin:0}li{display:flex;justify-content:space-between;gap:10px;font-size:9px;padding:7px 0;border-bottom:1px solid #f1f2f3}li span{color:#829167;font-size:8px;overflow-wrap:anywhere}@media(max-width:900px){main{grid-template-columns:repeat(2,1fr)}}@media print{main{grid-template-columns:repeat(4,1fr)}article{break-inside:avoid}}</style><header><h1>40 models. One connected repair system.</h1><p>SRDTMS · Physical schema and explicit foreign-key relationships · SQLite / SQLAlchemy</p><small>PK = primary key. Arrows identify the referenced table and column. Full ER diagram: ERD.md.</small></header><main>'+"".join(cards)+"</main></html>"
    (root / "database-schema.html").write_text(html, encoding="utf-8")
