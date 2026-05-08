import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture
def client():
    """Fresh app instance per test — avoids shared _job_store state between tests."""
    app = create_app()
    with TestClient(app) as c:
        yield c
