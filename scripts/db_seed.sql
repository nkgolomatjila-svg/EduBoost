-- EduBoost SA — Seed Data for Development
-- Sample learner (pseudonymous only — no real PII)

INSERT INTO learners (learner_id, grade, home_language, avatar_id, learning_style, overall_mastery, streak_days, total_xp)
VALUES
  ('00000000-0000-0000-0000-000000000001', 3, 'zul', 0, '{"visual":0.78,"auditory":0.14,"kinesthetic":0.08}', 0.55, 4, 175),
  ('00000000-0000-0000-0000-000000000002', 5, 'eng', 3, '{"visual":0.3,"auditory":0.5,"kinesthetic":0.2}', 0.72, 12, 620),
  ('00000000-0000-0000-0000-000000000003', 1, 'afr', 7, '{"visual":0.4,"auditory":0.2,"kinesthetic":0.4}', 0.38, 1, 35)
ON CONFLICT DO NOTHING;

INSERT INTO subject_mastery (learner_id, subject_code, grade_level, mastery_score, knowledge_gaps)
VALUES
  ('00000000-0000-0000-0000-000000000001','MATH',3,0.38,'[{"concept":"GR3_MATH_FRAC","gap_grade":2,"severity":0.62}]'::jsonb),
  ('00000000-0000-0000-0000-000000000001','ENG',3,0.62,'[]'::jsonb),
  ('00000000-0000-0000-0000-000000000001','LIFE',3,0.75,'[]'::jsonb),
  ('00000000-0000-0000-0000-000000000001','NS',3,0.55,'[]'::jsonb),
  ('00000000-0000-0000-0000-000000000001','SS',3,0.48,'[]'::jsonb)
ON CONFLICT (learner_id, subject_code) DO NOTHING;
