"""Issue, IssueComment, IssueEvent, and VerificationRun models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, utc_now

if TYPE_CHECKING:
    from backend.app.models.project import Project
    from backend.app.models.user import User


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_key: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    steps_to_reproduce: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expected_result: Mapped[str] = mapped_column(Text, default="", nullable=False)
    actual_result: Mapped[str] = mapped_column(Text, default="", nullable=False)
    environment: Mapped[str | None] = mapped_column(String(255), nullable=True)

    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="REPORTED", nullable=False, index=True)

    reporter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    assignee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="issues")
    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_id])
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id])

    comments: Mapped[list["IssueComment"]] = relationship(
        "IssueComment",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="IssueComment.created_at.asc()",
    )
    events: Mapped[list["IssueEvent"]] = relationship(
        "IssueEvent",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="IssueEvent.created_at.asc()",
    )
    verification_runs: Mapped[list["VerificationRun"]] = relationship(
        "VerificationRun",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="VerificationRun.created_at.desc()",
    )

    __table_args__ = (
        Index("ix_issues_project_status", "project_id", "status"),
        Index("ix_issues_project_severity", "project_id", "severity"),
    )


class IssueComment(Base):
    __tablename__ = "issue_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    issue: Mapped["Issue"] = relationship("Issue", back_populates="comments")
    author: Mapped["User"] = relationship("User")


class IssueEvent(Base):
    __tablename__ = "issue_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # STATUS_CHANGE, ASSIGNMENT, COMMENT_ADDED, VERIFIED, REOPENED
    old_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    issue: Mapped["Issue"] = relationship("Issue", back_populates="events")
    actor: Mapped[Optional["User"]] = relationship("User")


class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tester_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    result: Mapped[str] = mapped_column(String(10), nullable=False)  # PASS, FAIL
    test_notes: Mapped[str] = mapped_column(Text, nullable=False)
    tested_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    issue: Mapped["Issue"] = relationship("Issue", back_populates="verification_runs")
    tester: Mapped["User"] = relationship("User")
