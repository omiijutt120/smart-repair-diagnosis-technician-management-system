import secrets
import sqlite3
from pathlib import Path

import click
from cachelib.file import FileSystemCache
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException

from config import Config
from .extensions import csrf, db, login_manager, migrate, server_session


@event.listens_for(Engine, "connect")
def sqlite_integrity(connection, record):
    if isinstance(connection, sqlite3.Connection):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config["SECRET_KEY"]:
        secret_path = Path(app.instance_path) / ".local-secret"
        if not secret_path.exists():
            secret_path.write_text(secrets.token_hex(32), encoding="utf-8")
        app.config["SECRET_KEY"] = secret_path.read_text(encoding="utf-8").strip()
    app.config.setdefault("SESSION_CACHELIB", FileSystemCache(str(Path(app.instance_path) / "sessions"), threshold=1000, mode=0o600))
    db.init_app(app)
    migrate.init_app(app, db, compare_type=True, render_as_batch=True)
    csrf.init_app(app)
    login_manager.init_app(app)
    server_session.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    from .models import User, Notification, MODELS
    from .auth import bp as auth_bp
    from .customer import bp as customer_bp
    from .technician import bp as technician_bp
    from .admin import bp as admin_bp
    from .main import bp as main_bp
    from .services.workflow import BusinessError, local_datetime, local_now
    for blueprint in (auth_bp, customer_bp, technician_bp, admin_bp, main_bp):
        app.register_blueprint(blueprint)
    app.jinja_env.globals.update(min=min, max=max)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            user = db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None
        return user if user and user.is_active and not user.archived_at else None

    @app.before_request
    def serialize_sqlite_writes():
        # Reserve SQLite's write lock before reading business state on POST.
        # This prevents two concurrent reservations/payments reading the same balance.
        if request.method == "POST" and db.engine.dialect.name == "sqlite":
            connection = db.session.connection()
            if not connection.connection.driver_connection.in_transaction:
                connection.exec_driver_sql("BEGIN IMMEDIATE")

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'self'; form-action 'self'"
        if current_user.is_authenticated:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.context_processor
    def common_context():
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False, archived_at=None).count() if current_user.is_authenticated else 0
        return {"unread_count": unread, "now_local": local_now(), "model_registry": MODELS,
                "attr": getattr, "min": min, "max": max}

    @app.template_filter("money")
    def money_filter(value):
        return f"{value or 0:,.2f}"

    @app.template_filter("localtime")
    def time_filter(value, fmt="%d %b %Y, %H:%M"):
        return local_datetime(value).strftime(fmt) if value else "—"

    @app.template_filter("display")
    def display_filter(value):
        if value is None:
            return "—"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        return str(value)

    @app.errorhandler(BusinessError)
    def handle_business(error):
        db.session.rollback()
        return render_template("error.html", title="Action needs attention", code=422, message=str(error)), 422

    @app.errorhandler(IntegrityError)
    def handle_integrity(error):
        db.session.rollback()
        return render_template("error.html", title="Record could not be saved", code=409,
            message="This record conflicts with an existing value, a required field or linked history. Check unique fields and relationships before trying again."), 409

    @app.errorhandler(OperationalError)
    def handle_database(error):
        db.session.rollback()
        app.logger.error("Database operation failed: %s", error)
        return render_template("error.html", title="Database temporarily unavailable", code=503,
            message="Please retry in a moment. On first setup, run the database migration and seed commands in README.md."), 503

    @app.errorhandler(HTTPException)
    def handle_http(error):
        return render_template("error.html", title=error.name, code=error.code, message=error.description), error.code

    @app.errorhandler(500)
    def handle_unexpected(error):
        db.session.rollback()
        return render_template("error.html", title="Something went wrong", code=500,
            message="The action was not completed. Please return to your workspace and try again."), 500

    @app.cli.command("seed")
    def seed_command():
        """Load the idempotent, fictional demonstration dataset."""
        from .seed import seed_database
        seed_database()
        click.echo("Demo data ready. See README.md for local demonstration accounts.")

    @app.cli.command("schema-report")
    def schema_report():
        """Verify the 40 domain tables and generate the ERD and CRUD coverage."""
        from .documentation import generate_schema_docs
        generate_schema_docs()
        click.echo(f"{len(MODELS)} domain models. ERD and CRUD coverage written to docs/.")

    return app
