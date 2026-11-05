# PRD implementation and rubric evidence

Source: supplied *Smart Repair Diagnosis & Technician Management System PRD*, version 1.0, 14 pages. This file maps the implemented application to the requested features and explicitly records the safe history exceptions.

## Functional requirements

| PRD | Implementation |
|---|---|
| FR-01–03 | `auth/`, `security.py`, `main.profile`, hashed passwords, server-side sessions, roles, contact preferences |
| FR-04–05 | Catalogue CRUD; owned customer devices; category-labelled symptom checkboxes |
| FR-06–07 | Weighted editable rules, required symptoms, ranked results, transparent match calculations, no-match guidance and preliminary diagnosis disclaimer |
| FR-08–09 | Unique request codes, urgency, UTC timestamps, validated randomized uploads with private downloads |
| FR-10–11 | Customer appointments and technician availability; overlap, future-date and centre-hours checks; rescheduling audit |
| FR-12–13 | Skills/proficiency forms; centre, skill and availability checks; reassignment preserves prior assignment |
| FR-14–16 | Unique request-to-job work order; central transition map; actor/time history; explicitly customer-visible notes |
| FR-17 | Services, pricing, duration and optional skill reference |
| FR-18–19 | Suppliers, orders/items, one-time receipts, reservations/releases, actual usage, transactions and reversal of eligible adjustments; non-negative available stock |
| FR-20–21 | Multi-line draft estimates, server-calculated totals/tax/discount, expiry, sent status and ownership-protected timestamped approval/rejection |
| FR-22–23 | Unique one-per-job final invoices, manual/simulated payment records, partial settlement, overpayment checks and eligible refunds |
| FR-24–25 | In-app notifications with read/archive actions; one editable/withdrawable review per customer/completed job |
| FR-26–28 | Request search and status/date/centre/technician filters; role-scoped metrics; workload, stock and settled payment reports |
| FR-29–30 | 40 allow-listed list/detail resources, validated reference/draft forms, dedicated workflow mutations and per-record audit metadata; safe CRUD matrix in `CRUD_COVERAGE.md` |

## Acceptance tests T-01–T-20

| PRD test | Evidence in `tests/` |
|---|---|
| T-01–T-03 | Registration, password hashes, duplicate/invalid input, login and POST logout |
| T-04 | Customer IDOR checks for requests, invoices and attachments; technician assignment checks |
| T-05–T-06 | Matched weights, required-symptom gate, ranking, inactive rules, empty/no-match behavior and diagnosis PRG |
| T-07 | Appointment overlap/outside-hours rejection and availability overlap validation |
| T-08 | Skill and unavailable-technician rejection |
| T-09 | Valid transition appends actor/time/old/new; invalid/approval-bypass transitions blocked |
| T-10–T-12 | Over-reservation rejection; one-time receipt; consume reserved quantities once; release once |
| T-13–T-14 | Owned approval, server totals, invoice issuance, partial/full payment, overpayment prevention and paid completion |
| T-15 | Incomplete-job review and out-of-range rating rejection |
| T-16 | Exactly 40 populated models; connected FK graph; `foreign_key_check`; real fresh migration |
| T-17 | All 40 admin list/detail and eligible edit pages; catalogue CRUD; association deletion; protected finance/history; `CRUD_COVERAGE.md` defines each allowed workflow |
| T-18 | Every page inherits `base.html`; shared macros; all role pages render; browser screenshots |
| T-19 | POST missing CSRF returns 400; browser login/intake uses real CSRF tokens |
| T-20 | Fresh temporary DB upgrades through committed Alembic migration, seeds twice idempotently, and passes migration metadata check |

## Rubric deliverables

| Criterion | Evidence |
|---|---|
| Project setup & structure (10) | Application factory, domain packages, extensions, environment config, pinned dependencies and `start.cmd` |
| Routing & views (15) | Auth, customer, technician, admin and main blueprints; GET/POST separation; integer route converters |
| Jinja2 (15) | Shared base, blocks, macros, loops/conditionals, `url_for`, default escaping, empty states and flashes |
| Database & CRUD (20) | 40 explicit domain models, constraints, indexes, relationships, migration, ERD, SQL, safe CRUD policy and seeded usage |
| Forms, validation, sessions (15) | Flask-WTF/WTForms, global CSRF, field errors, PRG, server sessions, secure cookie options, role/ownership checks |
| Code quality (10) | Business services reused by views and seed; policy allow list; no raw interpolated SQL; clear separation of model domains |
| Functionality & testing (10) | End-to-end billing/repair tests, all-role route checks, real browser intake, responsive navigation and saved screenshots |
| Documentation (5) | README setup/demo/configuration/tests, sample accounts, model coverage, ERD, schema, screenshots and this mapping |

## Deliberate scope and history limits

- Diagnosis is advisory rule matching. No trained AI model or image-based fault detection is claimed.
- Payments are manual/simulated. No gateway or financial credential collection is implemented.
- Audit/history tables support append/corrective operations instead of destructive edits, per the PRD's integrity exception. Completed records remain traceable.
- Manual refunds are available before completed handover; completed-job refund review is an offline manager procedure. An unpaid final invoice can be voided; it stays retained as the one final invoice for that job.
- SQLite is the tested database. PostgreSQL configuration alone is not claimed to guarantee concurrency safety on PostgreSQL.
- Appointment capacity is one simultaneous booking per centre; this is documented in the booking UI and README.
- Instructor-specific submission metadata is outside the supplied requirements and is not invented.

See `VERIFICATION.md` for the actual final QA run and the screenshot directory for captured screens.
