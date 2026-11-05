# Final verification

Verified locally on **6 November 2026**, Windows, Python 3.12.10, Node 26.13.0, SQLite and Microsoft Edge (headless via Playwright).

| Check | Actual result |
|---|---|
| `python -m pytest -q` | **30 passed in 62.26 seconds**, no warnings (includes Render startup checks) |
| `flask --app app db upgrade` | Committed initial migration applied successfully |
| `flask --app app db check` | No new upgrade operations detected |
| `python -m pip check` | No broken requirements found |
| Fresh database acceptance test | Creates 40 domain tables + Alembic version metadata; seed works twice without duplicates; ORM metadata matches migrated schema |
| Relationship and seed test | All 40 domain tables populated; all belong to one connected foreign-key graph; SQLite `foreign_key_check` returns no violations |
| `npm.cmd run test:browser` | Passed: actual login for all three roles, dashboards, diagnosis results, repair intake submission, mobile navigation and responsive screens |
| Browser errors | No JavaScript errors or failed HTTP responses in the final browser run |
| Mobile layout | 390 × 844 viewport; dashboard, devices, diagnosis, request form, appointments and repairs fit the viewport; wide tables scroll internally |
| Submission screenshots | 11 PNG captures saved in `docs/screenshots/` |
| Render startup | Requires an environment secret; migrates a fresh database, seeds idempotently and passes `0.0.0.0`, Render's `PORT` and HTTPS scheme to Waitress |

Render deployment files are prepared and tested locally. No hosted Render deployment or public Render URL has been created or verified in this session. See `RENDER_DEPLOYMENT.md` for the chosen free-demo setup and its ephemeral storage limitations.

The browser check submits one labelled “Browser QA” request to the local demo database. Backend tests use temporary databases and never erase the working database. The development server used for browser verification is stopped after checks; start it again with `start.cmd`.

## Screenshot index

- [Landing page](screenshots/landing.png)
- [Administrator dashboard](screenshots/admin-dashboard.png)
- [Customer dashboard](screenshots/customer-dashboard.png)
- [Technician dashboard](screenshots/technician-dashboard.png)
- [Diagnosis results](screenshots/diagnosis-results.png)
- [Repair tracking](screenshots/repair-tracking.png)
- [Admin CRUD list](screenshots/admin-crud.png)
- [Inventory](screenshots/inventory.png)
- [Mobile dashboard](screenshots/mobile-dashboard.png)
- [Mobile diagnosis](screenshots/mobile-diagnosis.png)
- [All 40 database models](screenshots/database-schema.png)

The scope and safe historical CRUD exceptions are documented in `PRD_COMPLIANCE.md`, `CRUD_COVERAGE.md` and README. No live payment gateway, trained AI model, external messaging integration or production deployment is claimed.
