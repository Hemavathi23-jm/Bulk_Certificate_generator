import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
import app.database as database_module
import app.services as services_module
from main import app

# In-memory test database with StaticPool so all connections share the same memory instance
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    # Override database session maker across modules
    services_module.SessionLocal = TestingSessionLocal
    database_module.SessionLocal = TestingSessionLocal

    # Create tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Clean teardown
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
