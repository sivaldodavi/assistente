from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path: Path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only",
        "DATA_DIR": str(tmp_path),
        "DATABASE": str(tmp_path / "test.sqlite3"),
        "ALLOW_DEV_AUTH": True,
    })


@pytest.fixture()
def client(app):
    return app.test_client()
