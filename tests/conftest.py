import os

os.environ["DATABASE_URL"] = "sqlite:///./test_social_studio.db"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    return TestClient(app)
