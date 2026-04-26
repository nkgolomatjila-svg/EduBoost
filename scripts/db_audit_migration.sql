-- EduBoost SA — Supplementary indexes (applied after core init in Docker)
-- POPIA / audit query performance

CREATE INDEX IF NOT EXISTS ix_consent_audit_occurred ON consent_audit(occurred_at);
CREATE INDEX IF NOT EXISTS ix_consent_audit_pseudonym ON consent_audit(pseudonym_id);
CREATE INDEX IF NOT EXISTS ix_prompt_templates_active ON prompt_templates(is_active) WHERE is_active = TRUE;
