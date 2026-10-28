"""Database migration test verifying upgrade from an empty database."""

import os
import tempfile

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_migration_from_empty_database():
    """Verify that Alembic migrations run cleanly on a brand new database without errors."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = os.path.join(temp_dir, "mig_test.db")
        db_url = f"sqlite:///{temp_db_path}"

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # Run migration upgrade
        command.upgrade(alembic_cfg, "head")

        # Verify that all required tables were created
        engine = create_engine(db_url)
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        expected_tables = {
            "users",
            "sessions",
            "login_attempts",
            "projects",
            "project_members",
            "issues",
            "issue_comments",
            "issue_events",
            "verification_runs",
            "audit_events",
            "alembic_version",
        }
        try:
            assert expected_tables.issubset(table_names), (
                f"Missing tables: {expected_tables - table_names}"
            )
        finally:
            engine.dispose()
            import gc

            gc.collect()


def test_base_metadata_model_registry_completeness():
    """Verify that importing Base from backend.app.db.base has all 10 core tables registered."""
    from backend.app.db.base import Base

    registered_tables = set(Base.metadata.tables.keys())
    required_entities = {
        "users",
        "sessions",
        "login_attempts",
        "projects",
        "project_members",
        "issues",
        "issue_comments",
        "issue_events",
        "verification_runs",
        "audit_events",
    }
    assert required_entities.issubset(registered_tables), (
        f"Base.metadata is missing model registrations: {required_entities - registered_tables}"
    )
