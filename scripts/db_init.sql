-- EduBoost SA — Database Initialisation
-- Run automatically by Docker on first start

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Learners (pseudonymous — no PII)
CREATE TABLE IF NOT EXISTS learners (
    learner_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    grade SMALLINT NOT NULL CHECK (grade BETWEEN 0 AND 7),
    home_language VARCHAR(10) DEFAULT 'eng',
    avatar_id SMALLINT DEFAULT 0,
    learning_style JSONB DEFAULT '{"visual":0.6,"auditory":0.2,"kinesthetic":0.2}',
    overall_mastery FLOAT DEFAULT 0.0 CHECK (overall_mastery BETWEEN 0.0 AND 1.0),
    streak_days SMALLINT DEFAULT 0,
    total_xp INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW()
);

-- PII Silo (guardian-only access via RLS)
CREATE TABLE IF NOT EXISTS learner_identities (
    identity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pseudonym_id UUID UNIQUE NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
    full_name_encrypted TEXT,
    date_of_birth_encrypted TEXT,
    guardian_email_encrypted TEXT NOT NULL,
    consent_version SMALLINT NOT NULL,
    consent_timestamp TIMESTAMPTZ NOT NULL,
    data_deletion_requested BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subject Mastery
CREATE TABLE IF NOT EXISTS subject_mastery (
    mastery_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learner_id UUID NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
    subject_code VARCHAR(20) NOT NULL,
    grade_level SMALLINT NOT NULL,
    mastery_score FLOAT DEFAULT 0.0 CHECK (mastery_score BETWEEN 0.0 AND 1.0),
    concepts_mastered TEXT[] DEFAULT '{}',
    concepts_in_progress TEXT[] DEFAULT '{}',
    knowledge_gaps JSONB DEFAULT '[]',
    last_assessed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_subject_mastery_learner_subject UNIQUE (learner_id, subject_code)
);

-- Session Events (telemetry for RLHF)
CREATE TABLE IF NOT EXISTS session_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learner_id UUID NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    lesson_id VARCHAR(50),
    event_type VARCHAR(30),
    content_modality VARCHAR(20),
    is_correct BOOLEAN,
    time_on_task_ms INTEGER,
    difficulty_level FLOAT,
    post_mastery_delta FLOAT,
    lesson_efficacy_score FLOAT,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

-- Study Plans
CREATE TABLE IF NOT EXISTS study_plans (
    plan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    learner_id UUID NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
    week_start TIMESTAMPTZ NOT NULL,
    schedule JSONB NOT NULL,
    gap_ratio FLOAT DEFAULT 0.4,
    week_focus VARCHAR(200),
    generated_by VARCHAR(20) DEFAULT 'ALGORITHM',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Prompt Templates (RLHF)
CREATE TABLE IF NOT EXISTS prompt_templates (
    template_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_type VARCHAR(30) NOT NULL,
    version INTEGER DEFAULT 1,
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,
    avg_les_score FLOAT,
    sample_size INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- POPIA Consent Audit (immutable)
CREATE TABLE IF NOT EXISTS consent_audit (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pseudonym_id UUID NOT NULL,
    event_type VARCHAR(30) NOT NULL,
    consent_version SMALLINT,
    guardian_email_hash VARCHAR(64),
    ip_address_hash VARCHAR(64),
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_learners_last_active ON learners(last_active_at);
CREATE INDEX IF NOT EXISTS ix_subject_mastery_learner ON subject_mastery(learner_id);
CREATE INDEX IF NOT EXISTS ix_session_events_learner ON session_events(learner_id);
CREATE INDEX IF NOT EXISTS ix_session_events_occurred ON session_events(occurred_at);
CREATE INDEX IF NOT EXISTS ix_study_plans_learner ON study_plans(learner_id);

-- Row Level Security (Supabase)
ALTER TABLE learner_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE learners ENABLE ROW LEVEL SECURITY;
ALTER TABLE subject_mastery ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE learner_identities IS 'PII SILO: Guardian-only access. NEVER join to LLM query context.';
COMMENT ON TABLE learners IS 'Pseudonymous learner profiles. Safe for application use.';
