"""phase2 baseline - Create all core tables

Revision ID: 0001_phase2_baseline
Revises: 
Create Date: 2026-04-25 00:00:00

Tables:
- learner_identities (PII silo)
- learners (pseudonymous profiles)
- subject_mastery (per-subject mastery tracking)
- session_events (learning activity log)
- study_plans (generated study plans)
- prompt_templates (LLM prompt management)
- consent_audit (POPIA consent tracking)
- diagnostic_sessions (diagnostic attempt tracking)
- diagnostic_responses (individual item responses)
- badges (available badges)
- learner_badges (earned badges)
- item_bank (IRT diagnostic items)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_phase2_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Learner Identities (PII SILO)
    op.create_table(
        "learner_identities",
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pseudonym_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learners.learner_id"), unique=True, nullable=False),
        sa.Column("full_name_encrypted", sa.Text),
        sa.Column("date_of_birth_encrypted", sa.Text),
        sa.Column("guardian_email_encrypted", sa.Text, nullable=False),
        sa.Column("consent_version", sa.SmallInteger, nullable=False),
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_deletion_requested", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_learner_identities_pseudonym", "learner_identities", ["pseudonym_id"])

    # Learners (Pseudonymous)
    op.create_table(
        "learners",
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grade", sa.SmallInteger, nullable=False),
        sa.Column("home_language", sa.String(10), default="eng"),
        sa.Column("avatar_id", sa.SmallInteger, default=0),
        sa.Column("learning_style", postgresql.JSON, default={"visual": 0.6, "auditory": 0.2, "kinesthetic": 0.2}),
        sa.Column("overall_mastery", sa.Float, default=0.0),
        sa.Column("streak_days", sa.SmallInteger, default=0),
        sa.Column("total_xp", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("grade >= 0 AND grade <= 7", name="ck_learner_grade"),
        sa.CheckConstraint("overall_mastery >= 0.0 AND overall_mastery <= 1.0", name="ck_mastery_range"),
    )
    op.create_index("ix_learners_last_active", "learners", ["last_active_at"])

    # Subject Mastery
    op.create_table(
        "subject_mastery",
        sa.Column("mastery_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learners.learner_id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_code", sa.String(20), nullable=False),
        sa.Column("grade_level", sa.SmallInteger, nullable=False),
        sa.Column("mastery_score", sa.Float, default=0.0),
        sa.Column("concepts_mastered", postgresql.ARRAY(sa.String), default=[]),
        sa.Column("concepts_in_progress", postgresql.ARRAY(sa.String), default=[]),
        sa.Column("knowledge_gaps", postgresql.JSON, default=[]),
        sa.Column("last_assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("mastery_score >= 0.0 AND mastery_score <= 1.0", name="ck_subject_mastery_range"),
    )
    op.create_index("ix_subject_mastery_learner", "subject_mastery", ["learner_id"])

    # Session Events
    op.create_table(
        "session_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learners.learner_id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", sa.String(50)),
        sa.Column("event_type", sa.String(30)),
        sa.Column("content_modality", sa.String(20)),
        sa.Column("is_correct", sa.Boolean, nullable=True),
        sa.Column("time_on_task_ms", sa.Integer, nullable=True),
        sa.Column("difficulty_level", sa.Float, nullable=True),
        sa.Column("post_mastery_delta", sa.Float, nullable=True),
        sa.Column("lesson_efficacy_score", sa.Float, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_session_events_learner", "session_events", ["learner_id"])
    op.create_index("ix_session_events_occurred", "session_events", ["occurred_at"])
    op.create_index("ix_session_events_session", "session_events", ["session_id"])

    # Study Plans
    op.create_table(
        "study_plans",
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learners.learner_id", ondelete="CASCADE"), nullable=False),
        sa.Column("week_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schedule", postgresql.JSON, nullable=False),
        sa.Column("gap_ratio", sa.Float, default=0.4),
        sa.Column("week_focus", sa.String(200)),
        sa.Column("generated_by", sa.String(20), default="ALGORITHM"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_study_plans_learner", "study_plans", ["learner_id"])

    # Prompt Templates
    op.create_table(
        "prompt_templates",
        sa.Column("template_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_type", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("user_prompt_template", sa.Text, nullable=False),
        sa.Column("avg_les_score", sa.Float, nullable=True),
        sa.Column("sample_size", sa.Integer, default=0),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_prompt_templates_type_active", "prompt_templates", ["template_type", "is_active"])

    # Consent Audit
    op.create_table(
        "consent_audit",
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pseudonym_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("consent_version", sa.SmallInteger),
        sa.Column("guardian_email_hash", sa.String(64)),
        sa.Column("ip_address_hash", sa.String(64)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Diagnostic Sessions
    op.create_table(
        "diagnostic_sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learners.learner_id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_code", sa.String(20), nullable=False),
        sa.Column("grade_level", sa.SmallInteger, nullable=False),
        sa.Column("status", sa.String(20), default="in_progress"),
        sa.Column("theta_estimate", sa.Float),
        sa.Column("standard_error", sa.Float),
        sa.Column("items_administered", sa.Integer, default=0),
        sa.Column("items_total", sa.Integer, default=20),
        sa.Column("final_mastery_score", sa.Float),
        sa.Column("knowledge_gaps", postgresql.JSON, default=[]),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_diagnostic_sessions_learner", "diagnostic_sessions", ["learner_id"])

    # Diagnostic Responses
    op.create_table(
        "diagnostic_responses",
        sa.Column("response_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("diagnostic_sessions.session_id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(50), nullable=False),
        sa.Column("learner_response", sa.Text, nullable=False),
        sa.Column("is_correct", sa.Boolean, nullable=False),
        sa.Column("time_taken_ms", sa.Integer),
        sa.Column("theta_before", sa.Float),
        sa.Column("theta_after", sa.Float),
        sa.Column("sem_before", sa.Float),
        sa.Column("sem_after", sa.Float),
        sa.Column("information_gain", sa.Float),
        sa.Column("responded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_diagnostic_responses_session", "diagnostic_responses", ["session_id"])

    # Badges
    op.create_table(
        "badges",
        sa.Column("badge_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("badge_key", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("icon_url", sa.String(200)),
        sa.Column("xp_value", sa.Integer, default=0),
        sa.Column("grade_band", sa.String(20)),  # R-3 or 4-7
        sa.Column("badge_type", sa.String(30)),  # streak, mastery, milestone, discovery
        sa.Column("threshold", sa.Integer),  # e.g., 7 for 7-day streak
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Learner Badges
    op.create_table(
        "learner_badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learners.learner_id", ondelete="CASCADE"), nullable=False),
        sa.Column("badge_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("badges.badge_id"), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("evidence", postgresql.JSON),
    )
    op.create_index("ix_learner_badges_learner", "learner_badges", ["learner_id"])

    # Item Bank (IRT Diagnostic Items)
    op.create_table(
        "item_bank",
        sa.Column("item_id", sa.String(50), primary_key=True),
        sa.Column("subject_code", sa.String(20), nullable=False),
        sa.Column("grade_level", sa.SmallInteger, nullable=False),
        sa.Column("concept_code", sa.String(50)),
        sa.Column("difficulty", sa.Float, nullable=False),
        sa.Column("discrimination", sa.Float, nullable=False),
        sa.Column("guessing", sa.Float, default=0.25),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("options", postgresql.JSON),  # For multiple choice
        sa.Column("correct_answer", sa.Text),
        sa.Column("rubric", sa.Text),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calibration_sample_size", sa.Integer, default=0),
    )
    op.create_index("ix_item_bank_subject_grade", "item_bank", ["subject_code", "grade_level"])
    op.create_index("ix_item_bank_concept", "item_bank", ["concept_code"])

    # Audit Events
    op.create_table(
        "audit_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("pillar", sa.String(30)),
        sa.Column("actor_id", sa.String(100)),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("details", postgresql.JSON),
        sa.Column("request_id", sa.String(100)),
        sa.Column("ip_address_hash", sa.String(64)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_events_learner", "audit_events", ["learner_id"])
    op.create_index("ix_audit_events_occurred", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_type", "audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("item_bank")
    op.drop_table("learner_badges")
    op.drop_table("badges")
    op.drop_table("diagnostic_responses")
    op.drop_table("diagnostic_sessions")
    op.drop_table("consent_audit")
    op.drop_table("prompt_templates")
    op.drop_table("study_plans")
    op.drop_table("session_events")
    op.drop_table("subject_mastery")
    op.drop_table("learners")
    op.drop_table("learner_identities")
