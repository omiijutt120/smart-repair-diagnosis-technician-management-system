import importlib

import pytest


def test_render_start_requires_a_configured_secret(monkeypatch):
    module = importlib.import_module("render_start")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="Set SECRET_KEY"):
        module.main()


def test_render_start_migrates_seeds_and_binds_render_port(monkeypatch, tmp_path):
    from smart_repair import create_app
    from smart_repair.extensions import db
    from smart_repair.models import MODELS, User
    from sqlalchemy import inspect

    module = importlib.import_module("render_start")
    app = create_app({"TESTING": True, "SECRET_KEY": "isolated-render-test",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "render.db"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads")})
    monkeypatch.setenv("SECRET_KEY", "isolated-render-test")
    monkeypatch.setenv("PORT", "10001")
    monkeypatch.setenv("SEED_DEMO", "true")
    monkeypatch.setattr(module, "create_app", lambda: app)
    served = []

    def capture_server(application, **options):
        served.append(options)
        with application.app_context():
            assert set(inspect(db.engine).get_table_names()) == set(MODELS) | {"alembic_version"}
            assert User.query.count() == 5
        assert application.test_client().get("/auth/login").status_code == 200

    monkeypatch.setattr(module, "serve", capture_server)
    module.main()
    module.main()
    assert served == [{"host": "0.0.0.0", "port": 10001, "threads": 4, "url_scheme": "https"}] * 2
