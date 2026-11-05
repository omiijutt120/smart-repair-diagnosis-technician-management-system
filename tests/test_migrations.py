from pathlib import Path

from sqlalchemy import inspect, text

from smart_repair import create_app
from smart_repair.extensions import db
from smart_repair.models import MODELS, User


def test_fresh_database_migrates_seeds_and_matches_metadata(tmp_path):
    app = create_app({"TESTING":True,"SECRET_KEY":"fresh-setup-test", "WTF_CSRF_ENABLED":False,
        "SQLALCHEMY_DATABASE_URI":"sqlite:///"+str(tmp_path/"fresh.db"),
        "UPLOAD_FOLDER":str(tmp_path/"uploads")})
    runner = app.test_cli_runner()
    result = runner.invoke(args=["db","upgrade"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(args=["seed"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert set(inspect(db.engine).get_table_names()) == set(MODELS) | {"alembic_version"}
        assert User.query.count() == 5
        assert db.session.execute(text("PRAGMA foreign_key_check")).all() == []
    assert runner.invoke(args=["seed"]).exit_code == 0
    with app.app_context():
        assert User.query.count() == 5
    result = runner.invoke(args=["db","check"])
    assert result.exit_code == 0,result.output
