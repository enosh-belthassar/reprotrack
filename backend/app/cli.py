"""Command-line interface for ReproTrack management, migrations, and administrator bootstrap."""

import sys

import click
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from backend.app.core.permissions import GlobalRole
from backend.app.core.security import hash_password
from backend.app.db.session import SessionLocal
from backend.app.models.user import User


@click.group()
def cli():
    """ReproTrack Command Line Interface."""


@cli.command("bootstrap-admin")
@click.option(
    "--email", prompt="Admin Email", help="Normalized email for the initial administrator"
)
@click.option("--name", prompt="Display Name", default="Administrator", help="Admin display name")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Password for administrator account (min 8 chars)",
)
def bootstrap_admin(email: str, name: str, password: str):
    """Securely bootstrap the initial global administrator account."""
    if len(password) < 8:
        click.echo("Error: Password must be at least 8 characters.", err=True)
        sys.exit(1)

    norm_email = email.strip().lower()
    db = SessionLocal()
    try:
        existing = db.execute(
            select(User).where(User.email_normalized == norm_email)
        ).scalar_one_or_none()
        if existing:
            if existing.global_role == GlobalRole.GLOBAL_ADMIN:
                click.echo(f"Notice: Administrator '{norm_email}' already exists.")
                return
            else:
                existing.global_role = GlobalRole.GLOBAL_ADMIN
                existing.is_active = True
                existing.password_hash = hash_password(password)
                db.commit()
                click.echo(f"Success: Promoted '{norm_email}' to Global Administrator.")
                return

        admin_user = User(
            display_name=name.strip(),
            email_normalized=norm_email,
            password_hash=hash_password(password),
            global_role=GlobalRole.GLOBAL_ADMIN,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        click.echo(f"Success: Global administrator '{norm_email}' created successfully.")
    finally:
        db.close()


@cli.command("migrate")
def migrate():
    """Run pending Alembic database migrations."""
    click.echo("Applying database migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    click.echo("Migrations successfully applied.")


@cli.command("seed-demo")
@click.confirmation_option(
    prompt="Are you sure you want to seed demo data into the current database?"
)
def seed_demo():
    """Seed clearly labeled demo data for local prototype testing."""
    from backend.app.core.db_utils import utc_now
    from backend.app.core.permissions import ProjectRole
    from backend.app.models.issue import Issue, IssueEvent, VerificationRun
    from backend.app.models.project import Project, ProjectMember

    db = SessionLocal()
    try:
        # 1. Check or create demo users
        users_data = [
            ("Admin Demo", "admin@demo.local", GlobalRole.GLOBAL_ADMIN),
            ("Dev Lead", "dev@demo.local", GlobalRole.USER),
            ("QA Engineer", "qa@demo.local", GlobalRole.USER),
            ("Viewer Guest", "viewer@demo.local", GlobalRole.USER),
        ]
        created_users = {}
        for d_name, email, role in users_data:
            u = db.execute(select(User).where(User.email_normalized == email)).scalar_one_or_none()
            if not u:
                u = User(
                    display_name=d_name,
                    email_normalized=email,
                    password_hash=hash_password("DemoPassword123!"),
                    global_role=role,
                    is_active=True,
                )
                db.add(u)
                db.flush()
            created_users[email] = u

        # 2. Check or create demo project
        proj = db.execute(select(Project).where(Project.key == "DEMO")).scalar_one_or_none()
        if not proj:
            proj = Project(
                key="DEMO",
                name="Demo Web Platform",
                description="Sample software project for testing bug reporting and verification lifecycle.",
                created_by_id=created_users["admin@demo.local"].id,
                next_issue_number=1,
            )
            db.add(proj)
            db.flush()

            # Add memberships
            memberships = [
                (created_users["admin@demo.local"].id, ProjectRole.PROJECT_ADMIN),
                (created_users["dev@demo.local"].id, ProjectRole.DEVELOPER),
                (created_users["qa@demo.local"].id, ProjectRole.TESTER),
                (created_users["viewer@demo.local"].id, ProjectRole.VIEWER),
            ]
            for uid, r in memberships:
                db.add(ProjectMember(project_id=proj.id, user_id=uid, role=r))
            db.flush()

            # Seed a few demo issues with different lifecycle statuses
            issues_data = [
                {
                    "title": "Authentication token expired message flashes unexpectedly",
                    "desc": "Users report sudden logout warning popup after 5 minutes.",
                    "steps": "1. Log into portal\n2. Idle for 5 minutes\n3. Observe warning toast",
                    "expected": "Session should stay active for configured TTL",
                    "actual": "Warning modal renders on heartbeat failure",
                    "env": "Chrome 122 on Windows 11",
                    "sev": "HIGH",
                    "prio": "HIGH",
                    "status": "REPORTED",
                    "reporter": created_users["qa@demo.local"].id,
                    "assignee": None,
                },
                {
                    "title": "Payment webhook double charges on network retry",
                    "desc": "Idempotency key header was ignored during retry requests.",
                    "steps": "1. Dispatch checkout request\n2. Simulate 504 Gateway Timeout\n3. Re-post charge",
                    "expected": "Webhook receives idempotency key and returns prior result",
                    "actual": "Two separate charge transactions were ledgered",
                    "env": "Staging Backend v0.4.1",
                    "sev": "CRITICAL",
                    "prio": "URGENT",
                    "status": "FIXED",
                    "reporter": created_users["qa@demo.local"].id,
                    "assignee": created_users["dev@demo.local"].id,
                },
                {
                    "title": "Reports table column headers truncated on 1080p display",
                    "desc": "DataGrid column auto-width causes last column to wrap.",
                    "steps": "1. Open Reports -> Status Breakdown\n2. View on 1920x1080 resolution",
                    "expected": "Columns display with sufficient padding",
                    "actual": "Reopened rate column text is clipped",
                    "env": "Firefox 124",
                    "sev": "LOW",
                    "prio": "LOW",
                    "status": "CLOSED",
                    "reporter": created_users["viewer@demo.local"].id,
                    "assignee": created_users["dev@demo.local"].id,
                },
            ]

            for idata in issues_data:
                key = f"{proj.key}-{proj.next_issue_number}"
                proj.next_issue_number += 1
                iss = Issue(
                    issue_key=key,
                    project_id=proj.id,
                    title=idata["title"],
                    description=idata["desc"],
                    steps_to_reproduce=idata["steps"],
                    expected_result=idata["expected"],
                    actual_result=idata["actual"],
                    environment=idata["env"],
                    severity=idata["sev"],
                    priority=idata["prio"],
                    status=idata["status"],
                    reporter_id=idata["reporter"],
                    assignee_id=idata["assignee"],
                    version=1,
                    resolved_at=utc_now() if idata["status"] in {"FIXED", "CLOSED"} else None,
                    closed_at=utc_now() if idata["status"] == "CLOSED" else None,
                )
                db.add(iss)
                db.flush()

                db.add(
                    IssueEvent(
                        issue_id=iss.id,
                        actor_id=idata["reporter"],
                        event_type="CREATED",
                        new_value=idata["status"],
                    )
                )

                if idata["status"] == "CLOSED":
                    db.add(
                        VerificationRun(
                            issue_id=iss.id,
                            tester_id=created_users["qa@demo.local"].id,
                            result="PASS",
                            test_notes="Verified column spacing across resolutions 1366x768 to 4K.",
                            tested_version="v0.4.2-rc1",
                        )
                    )

            db.commit()
            click.echo("Success: DEMO project and sample issues created.")
        else:
            click.echo("Notice: DEMO project already exists.")
    finally:
        db.close()


if __name__ == "__main__":
    cli()
