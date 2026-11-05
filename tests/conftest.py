import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smart_repair import create_app
from smart_repair.extensions import db
from smart_repair.seed import seed_database


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "isolated-test-secret", "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.db"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads")})
    @app.before_request
    def fresh_test_user():
        # Tests hold an app context for direct ORM assertions across requests.
        from flask import g
        g.pop("_login_user", None)
    with app.app_context():
        db.create_all()
        seed_database()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    def authenticate(role="admin"):
        client.post("/auth/logout")
        response = client.post("/auth/login", data={"email": f"{role}@smartrepair.test", "password": "RepairDemo123!"})
        assert response.status_code == 302, response.data.decode()[:500]
        return client
    return authenticate
