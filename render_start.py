"""Initialize and serve the free Render academic demonstration.

Migrations and seed run at runtime, before accepting traffic. The free Render
filesystem can reset, so each fresh instance needs to initialize its database.
"""
import os
from pathlib import Path

from flask_migrate import upgrade
from waitress import serve

from smart_repair import create_app

ROOT = Path(__file__).resolve().parent


def main():
    if not os.environ.get("SECRET_KEY"):
        raise RuntimeError("Set SECRET_KEY in Render Environment settings before starting.")
    try:
        port = int(os.getenv("PORT", "10000"))
    except ValueError as error:
        raise RuntimeError("PORT must be a whole number.") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("PORT must be between 1 and 65535.")
    app = create_app()
    with app.app_context():
        upgrade(directory=str(ROOT / "migrations"))
        if os.getenv("SEED_DEMO", "true").lower() == "true":
            from smart_repair.seed import seed_database
            seed_database()
    print(f"Smart Repair ready on 0.0.0.0:{port}", flush=True)
    serve(app, host="0.0.0.0", port=port, threads=4, url_scheme="https")


if __name__ == "__main__":
    main()
