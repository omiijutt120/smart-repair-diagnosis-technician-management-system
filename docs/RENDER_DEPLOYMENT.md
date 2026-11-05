# Render: free academic demo

This project includes `render.yaml`, `.python-version` and `render_start.py` for the user's selected **free demo** deployment. These files prepare deployment; they do not create a Render service or publish a live URL by themselves.

## 1. Upload the source to GitHub

Create a GitHub repository, then upload the application source. `app.py`, `render_start.py`, `render.yaml`, `.python-version`, `requirements.txt`, `config.py`, `smart_repair/` and `migrations/` must be in the repository root (not under an extra ZIP wrapper directory).

Exclude `.venv/`, `node_modules/`, `.env`, `instance/`, local database files and `dist/`. They are already listed in `.gitignore`. The `.env.example` placeholder file is safe to include. This repo needs Python only on Render; the Node package is optional local browser QA tooling.

## 2. Deploy using the Blueprint

1. Sign in to [Render Dashboard](https://dashboard.render.com/).
2. Choose **New → Blueprint** and connect your GitHub repository.
3. Select the branch containing `render.yaml` and review the proposed service.
4. The Blueprint declares one **Free Python Web Service**, with no paid disk or paid database. Deploy the Blueprint.
5. Wait for the service to become **Live**, then open the actual `https://...onrender.com` URL returned by Render.

Render generates `SECRET_KEY` from the Blueprint. HTTPS cookies are enabled. Python is pinned to 3.12.10 in `.python-version`.

## Alternative: create the Web Service manually

Choose **New → Web Service**, connect the repository, and use:

| Setting | Value |
|---|---|
| Language/runtime | Python 3 |
| Branch | Your source branch, usually `main` |
| Root Directory | Leave empty when `app.py` is at the repository root |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python render_start.py` |
| Instance Type | Free |
| Health Check Path | `/auth/login` |

Add these environment variables:

| Key | Value |
|---|---|
| `SECRET_KEY` | Generate a random secret; do not use the `.env.example` placeholder |
| `SESSION_COOKIE_SECURE` | `true` |
| `SEED_DEMO` | `true` |
| `PYTHONUNBUFFERED` | `1` |

Generate a secret locally, then paste the result into Render's secret environment field (not GitHub):

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

`PORT` is supplied by Render. The startup script binds Waitress to `0.0.0.0:$PORT`, applies the committed migrations, and idempotently loads demo records before it accepts requests. Use this script instead of `python app.py`, which is configured for local development on loopback.

## 3. Check the live demo

All demonstration accounts use `RepairDemo123!`:

| Role | Email |
|---|---|
| Administrator | `admin@smartrepair.test` |
| Technician | `tech@smartrepair.test` |
| Customer | `customer@smartrepair.test` |

Open the deployed URL, sign in with each role, run customer diagnosis, create a repair request, then inspect that request as admin. These are intentionally shared demonstration accounts. Use fictional test records for this public demo.

## Free-plan limitations

- Render Free web services can spin down after 15 minutes without inbound traffic. The next visit can take about a minute to wake the app.
- Local SQLite data, attachments and filesystem sessions can disappear on a restart, redeploy or spin-down. The startup script recreates the fictional initial dataset when needed; it does not recover newly entered records or uploads.
- This configuration does not provision PostgreSQL, object storage or a persistent disk. Preserving user records requires a separate persistence setup. Merely moving the SQLite path does not make a free filesystem persistent.
- This is a public academic demonstration, not a deployment for real customer or payment records.

## Troubleshooting

| Symptom | Check |
|---|---|
| `No open ports detected` | Start Command must be `python render_start.py`; inspect startup errors before the server binds |
| `Set SECRET_KEY...` | Set/generate the secret in Render Environment; do not publish the secret in source |
| Python/package installation failure | Confirm `.python-version` is uploaded and that a conflicting `PYTHON_VERSION` environment variable is not selecting another version |
| Missing tables | Keep the complete `migrations/` directory in GitHub and use the supplied startup script |
| Login redirects in a loop | Open Render's HTTPS URL, with cookies allowed; `SESSION_COOKIE_SECURE=true` is correct for HTTPS |
| Previously entered records disappear | Expected on the selected Free SQLite demo; see persistence limitations above |

## Official references

- [Render Web Services](https://render.com/docs/web-services)
- [Render Blueprint reference](https://render.com/docs/blueprint-spec)
- [Setting Python version](https://render.com/docs/python-version)
- [Free instance limitations](https://render.com/docs/free)
- [Persistent disk options](https://render.com/docs/disks)
- [Waitress server documentation](https://docs.pylonsproject.org/projects/waitress/en/latest/runner.html)
