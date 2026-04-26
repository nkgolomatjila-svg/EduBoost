"""
EduBoost SA — SQLAlchemy Database Models
POPIA: PII columns are AES-256 encrypted at rest via Supabase Vault
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, SmallInteger, JSON, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.api.core.database import Base


class LearnerIdentity(Base):
    """PII SILO — accessible ONLY via parent JWT. Never joined to learning tables in LLM context."""
    __tablename__ = "learner_identities"

    identity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pseudonym_id = Column(UUID(as_uuid=True), ForeignKey("learners.learner_id"), unique=True, nullable=False)
    full_name_encrypted = Column(Text)
    date_of_birth_encrypted = Column(Text)
    guardian_email_encrypted = Column(Text, nullable=False)
    consent_version = Column(SmallInteger, nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), nullable=False)
    data_deletion_requested = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_learner_identities_pseudonym", "pseudonym_id"),
    )


class Learner(Base):
    """PSEUDONYMOUS PROFILE — safe for application use. Contains ZERO directly identifying information."""
    __tablename__ = "learners"

    learner_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grade = Column(SmallInteger, nullable=False)
    home_language = Column(String(10), default="eng")
    avatar_id = Column(SmallInteger, default=0)
    learning_style = Column(JSON, default={"visual": 0.6, "auditory": 0.2, "kinesthetic": 0.2})
    overall_mastery = Column(Float, default=0.0)
    streak_days = Column(SmallInteger, default=0)
    total_xp = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    subject_mastery = relationship("SubjectMastery", back_populates="learner", cascade="all, delete-orphan")
    session_events = relationship("SessionEvent", back_populates="learner", cascade="all, delete-orphan")
    study_plans = relationship("StudyPlan", back_populates="learner", cascade="all, delete-orphan")
    diagnostic_sessions = relationship("DiagnosticSession", back_populates="learner", cascade="all, delete-orphan")
    learner_badges = relationship("LearnerBadge", back_populates="learner", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("grade >= 0 AND grade <= 7", name="ck_learner_grade"),
        CheckConstraint("overall_mastery >= 0.0 AND overall_mastery <= 1.0", name="ck_mastery_range"),
        Index("ix_learners_last_active", "last_active_at"),
    )


class SubjectMastery(Base):
    __tablename__ = "subject_mastery"

    mastery_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.learner_id", ondelete="CASCADE"), nullable=False)
    subject_code = Column(String(20), nullable=False)
    grade_level = Column(SmallInteger, nullable=False)
    mastery_score = Column(Float, default=0.0)
    concepts_mastered = Column(ARRAY(String), default=[])
    concepts_in_progress = Column(ARRAY(String), default=[])
    knowledge_gaps = Column(JSON, default=[])
    last_assessed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    learner = relationship("Learner", back_populates="subject_mastery")

    __table_args__ = (
        CheckConstraint("mastery_score >= 0.0 AND mastery_score <= 1.0", name="ck_subject_mastery_range"),
        Index("ix_subject_mastery_learner", "learner_id"),
    )


class SessionEvent(Base):
    __tablename__ = "session_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.learner_id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    lesson_id = Column(String(50))
    event_type = Column(String(30))
    content_modality = Column(String(20))
    is_correct = Column(Boolean, nullable=True)
    time_on_task_ms = Column(Integer, nullable=True)
    difficulty_level = Column(Float, nullable=True)
    post_mastery_delta = Column(Float, nullable=True)
    lesson_efficacy_score = Column(Float, nullable=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())

    learner = relationship("Learner", back_populates="session_events")

    __table_args__ = (
        Index("ix_session_events_learner", "learner_id"),
        Index("ix_session_events_occurred", "occurred_at"),
        Index("ix_session_events_session", "session_id"),
    )


class StudyPlan(Base):
    __tablename__ = "study_plans"

    plan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.learner_id", ondelete="CASCADE"), nullable=False)
    week_start = Column(DateTime(timezone=True), nullable=False)
    schedule = Column(JSON, nullable=False)
    gap_ratio = Column(Float, default=0.4)
    week_focus = Column(String(200))
    generated_by = Column(String(20), default="ALGORITHM")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    learner = relationship("Learner", back_populates="study_plans")

    __table_args__ = (
        Index("ix_study_plans_learner", "learner_id"),
    )


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_type = Column(String(30), nullable=False)
    version = Column(Integer, default=1)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    avg_les_score = Column(Float, nullable=True)
    sample_size = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_prompt_templates_type_active", "template_type", "is_active"),
    )


class ConsentAudit(Base):
    __tablename__ = "consent_audit"

    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pseudonym_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String(30), nullable=False)
    consent_version = Column(SmallInteger)
    guardian_email_hash = Column(String(64))
    ip_address_hash = Column(String(64))
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())


class DiagnosticSession(Base):
    """Tracks diagnostic assessment sessions and outcomes."""
    __tablename__ = "diagnostic_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.learner_id", ondelete="CASCADE"), nullable=False)
    subject_code = Column(String(20), nullable=False)
    grade_level = Column(SmallInteger, nullable=False)
    status = Column(String(20), default="in_progress")  # in_progress, completed, abandoned
    theta_estimate = Column(Float)
    standard_error = Column(Float)
    items_administered = Column(Integer, default=0)
    items_total = Column(Integer, default=20)
    final_mastery_score = Column(Float)
    knowledge_gaps = Column(JSON, default=[])
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    learner = relationship("Learner", back_populates="diagnostic_sessions")
    responses = relationship("DiagnosticResponse", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_diagnostic_sessions_learner", "learner_id"),
    )


class DiagnosticResponse(Base):
    """Individual item responses within a diagnostic session."""
    __tablename__ = "diagnostic_responses"

    response_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("diagnostic_sessions.session_id", ondelete="CASCADE"), nullable=False)
    item_id = Column(String(50), nullable=False)
    learner_response = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_taken_ms = Column(Integer)
    theta_before = Column(Float)
    theta_after = Column(Float)
    sem_before = Column(Float)
    sem_after = Column(Float)
    information_gain = Column(Float)
    responded_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("DiagnosticSession", back_populates="responses")

    __table_args__ = (
        Index("ix_diagnostic_responses_session", "session_id"),
    )


class Badge(Base):
    """Available badges in the gamification system."""
    __tablename__ = "badges"

    badge_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    badge_key = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon_url = Column(String(200))
    xp_value = Column(Integer, default=0)
    grade_band = Column(String(20))  # R-3 or 4-7
    badge_type = Column(String(30))  # streak, mastery, milestone, discovery
    threshold = Column(Integer)  # e.g., 7 for 7-day streak
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LearnerBadge(Base):
    """Earned badges by learners."""
    __tablename__ = "learner_badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.learner_id", ondelete="CASCADE"), nullable=False)
    badge_id = Column(UUID(as_uuid=True), ForeignKey("badges.badge_id"), nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    evidence = Column(JSON)

    learner = relationship("Learner")
    badge = relationship("Badge")

    __table_args__ = (
        Index("ix_learner_badges_learner", "learner_id"),
    )


class ItemBank(Base):
    """IRT item bank for diagnostic assessments."""
    __tablename__ = "item_bank"

    item_id = Column(String(50), primary_key=True)
    subject_code = Column(String(20), nullable=False)
    grade_level = Column(SmallInteger, nullable=False)
    concept_code = Column(String(50))
    difficulty = Column(Float, nullable=False)
    discrimination = Column(Float, nullable=False)
    guessing = Column(Float, default=0.25)
    content = Column(Text, nullable=False)
    options = Column(JSON)  # For multiple choice
    correct_answer = Column(Text)
    rubric = Column(Text)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    calibrated_at = Column(DateTime(timezone=True), nullable=True)
    calibration_sample_size = Column(Integer, default=0)

    __table_args__ = (
        Index("ix_item_bank_subject_grade", "subject_code", "grade_level"),
        Index("ix_item_bank_concept", "concept_code"),
    )


class AuditEvent(Base):
    """Immutable audit events for compliance."""
    __tablename__ = "audit_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)
    pillar = Column(String(30))
    actor_id = Column(String(100))
    learner_id = Column(UUID(as_uuid=True), nullable=True)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    details = Column(JSON)
    request_id = Column(String(100))
    ip_address_hash = Column(String(64))
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_audit_events_learner", "learner_id"),
        Index("ix_audit_events_occurred", "occurred_at"),
        Index("ix_audit_events_type", "event_type"),
    )
