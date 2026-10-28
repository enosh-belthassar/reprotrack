"""Test fixtures and database isolation for ReproTrack."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Force APP_ENV=test
os.environ["APP_ENV"] = "test"
os.environ["LOGIN_WINDOW_MINUTES"] = "15"
os.environ["LOGIN_MAX_FAILURES"] = "5"
os.environ["TOKEN_TTL_HOURS"] = "8"

from backend.app.core.permissions import GlobalRole, ProjectRole
from backend.app.core.security import hash_password
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models.project import Project, ProjectMember
from backend.app.models.user import User

# In-memory SQLite engine with StaticPool so all connections share the same memory DB
TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db: Session) -> User:
    user = User(
        display_name="Global Admin",
        email_normalized="admin@reprotrack.test",
        password_hash=hash_password("AdminSecurePass123!"),
        global_role=GlobalRole.GLOBAL_ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def dev_user(db: Session) -> User:
    user = User(
        display_name="Jane Developer",
        email_normalized="dev@reprotrack.test",
        password_hash=hash_password("DevSecurePass123!"),
        global_role=GlobalRole.USER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def tester_user(db: Session) -> User:
    user = User(
        display_name="Bob Tester",
        email_normalized="tester@reprotrack.test",
        password_hash=hash_password("TesterSecurePass123!"),
        global_role=GlobalRole.USER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def viewer_user(db: Session) -> User:
    user = User(
        display_name="Alice Viewer",
        email_normalized="viewer@reprotrack.test",
        password_hash=hash_password("ViewerSecurePass123!"),
        global_role=GlobalRole.USER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_project(
    db: Session, admin_user: User, dev_user: User, tester_user: User, viewer_user: User
) -> Project:
    proj = Project(
        key="PRJ",
        name="Test Suite Project",
        description="Integration testing project",
        created_by_id=admin_user.id,
        next_issue_number=1,
    )
    db.add(proj)
    db.flush()

    memberships = [
        ProjectMember(project_id=proj.id, user_id=admin_user.id, role=ProjectRole.PROJECT_ADMIN),
        ProjectMember(project_id=proj.id, user_id=dev_user.id, role=ProjectRole.DEVELOPER),
        ProjectMember(project_id=proj.id, user_id=tester_user.id, role=ProjectRole.TESTER),
        ProjectMember(project_id=proj.id, user_id=viewer_user.id, role=ProjectRole.VIEWER),
    ]
    db.add_all(memberships)
    db.commit()
    db.refresh(proj)
    return proj


def get_auth_token(client: TestClient, identifier: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    assert res.status_code == 200, f"Login failed for {identifier}: {res.text}"
    return res.json()["token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
