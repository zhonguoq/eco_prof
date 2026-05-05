import pytest
from lab.engine import db

@pytest.fixture(autouse=True)
def _db_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ECO_DB_DIR", str(tmp_path))
    db._connections.clear()
    db._DB_DIR = None
