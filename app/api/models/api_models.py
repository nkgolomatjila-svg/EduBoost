"""EduBoost SA — Shared API request/response models."""
from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorResponse(StrictSchema):
    error: str
    code: str
    details: dict[str, Any] | None = None


class LearnerCreateRequest(StrictSchema):
    grade: int = Field(ge=0, le=7)
    home_language: str = Field(default="eng", min_length=2, max_length=10)
    avatar_id: int = Field(default=0, ge=0, le=11)
    learning_style: dict[str, float] = Field(
        default_factory=lambda: {"visual": 0.6, "auditory": 0.2, "kinesthetic": 0.2}
    )


class LearnerUpdateRequest(StrictSchema):
    grade: int | None = Field(default=None, ge=0, le=7)
    avatar_id: int | None = Field(default=None, ge=0, le=11)
    streak_days: int | None = Field(default=None, ge=0)
    total_xp: int | None = Field(default=None, ge=0)
    overall_mastery: float | None = Field(default=None, ge=0.0, le=1.0)


class LearnerCreateResponse(StrictSchema):
    learner_id: UUID
    grade: int


class LearnerUpdateResponse(StrictSchema):
    updated: bool


class DeletionRequestResponse(StrictSchema):
    status: Literal["deletion_requested"]
    learner_id: UUID
    note: str


class SubjectMasteryEntry(StrictSchema):
    subject_code: str
    grade_level: int | None = None
    mastery_score: float | None = None
    concepts_mastered: list[str] | None = None
    concepts_in_progress: list[str] | None = None
    knowledge_gaps: list[dict[str, Any]] | None = None


class SubjectMasteryResponse(StrictSchema):
    learner_id: UUID
    mastery: list[SubjectMasteryEntry]


class DiagnosticRequest(StrictSchema):
    learner_id: UUID
    subject_code: str
    grade: int = Field(ge=0, le=7)
    max_questions: int = Field(default=10, ge=1, le=20)


class DiagnosticSessionSummary(StrictSchema):
    questions_administered: int
    theta: float
    sem: float
    gap_probe_active: bool


class DiagnosticRunResponse(StrictSchema):
    success: bool
    gap_report: dict[str, Any]
    session_summary: DiagnosticSessionSummary


class DiagnosticItem(StrictSchema):
    item_id: str
    question_text: str
    options: list[str]
    story_context: str | None = None
    difficulty_label: str | None = None


class DiagnosticItemsResponse(StrictSchema):
    subject: str
    grade: int
    items: list[DiagnosticItem]
    count: int


class GuardianLoginRequest(StrictSchema):
    email: str = Field(min_length=3, max_length=320)
    learner_pseudonym_id: str = Field(min_length=1)


class TokenResponse(StrictSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LearnerSessionRequest(StrictSchema):
    learner_id: str = Field(min_length=1)


class LearnerSessionResponse(StrictSchema):
    session_token: str
    expires_in: int


class LessonRequest(StrictSchema):
    learner_id: UUID
    subject_code: str
    subject_label: str
    topic: str
    grade: int = Field(ge=0, le=7)
    home_language: str = "English"
    learning_style_primary: str = "visual"
    mastery_prior: float = Field(default=0.5, ge=0.0, le=1.0)
    has_gap: bool = False
    gap_grade: int | None = None


class LessonFeedback(StrictSchema):
    learner_id: UUID
    lesson_id: str
    rating: int = Field(ge=1, le=5)
    modality_preference: str | None = None
    completion_pct: float = Field(ge=0.0, le=1.0)
    time_spent_seconds: int = Field(ge=0)


class LessonMeta(StrictSchema):
    stamp_status: str
    stamp_id: str | None = None
    ether_archetype: str | None = None
    constitutional_health: float | None = None
    latency_ms: int | None = None


class LessonGenerationResponse(StrictSchema):
    success: bool
    lesson: dict[str, Any]
    meta: LessonMeta


class CachedLessonResponse(StrictSchema):
    success: bool
    lesson: dict[str, Any]
    source: str


class StudyPlanRequest(StrictSchema):
    learner_id: UUID
    grade: int = Field(ge=0, le=7)
    knowledge_gaps: list[dict[str, Any]] = Field(default_factory=list)
    subjects_mastery: dict[str, float] = Field(default_factory=dict)
    gap_ratio: float = Field(default=0.4, ge=0.3, le=0.6)


class StudyPlanGenerationResponse(StrictSchema):
    success: bool
    plan: dict[str, Any]


class CurrentStudyPlanResponse(StrictSchema):
    success: bool
    plan: dict[str, Any]


class ParentReportRequest(StrictSchema):
    learner_id: UUID
    grade: int = Field(ge=0, le=7)
    streak_days: int = Field(default=0, ge=0)
    total_xp: int = Field(default=0, ge=0)
    subjects_mastery: dict[str, float] = Field(default_factory=dict)
    gaps: list[dict[str, Any]] = Field(default_factory=list)


class ParentReportResponse(StrictSchema):
    success: bool
    report: dict[str, Any]


class ConsentRequest(StrictSchema):
    learner_id: UUID
    guardian_email: str = Field(min_length=3, max_length=320)
    consent_version: int = Field(default=1, ge=1)
    consented: bool


class ConsentResponse(StrictSchema):
    recorded: bool
    popia_compliant: bool


class LearnerProgressResponse(StrictSchema):
    success: bool
    grade: int
    streak_days: int
    total_xp: int
    overall_mastery: float
    subjects: dict[str, float]
