"""EduBoost SA — Constitutional types (Legislature contracts)."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuleCategory(str, Enum):
    POPIA = "POPIA"
    CAPS = "CAPS"
    CHILD = "CHILD"
    PII = "PII"
    LANGUAGE = "LANGUAGE"


class RuleSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionType(str, Enum):
    GENERATE_LESSON = "GENERATE_LESSON"
    RUN_DIAGNOSTIC = "RUN_DIAGNOSTIC"
    STORE_FEEDBACK = "STORE_FEEDBACK"
    GENERATE_STUDY_PLAN = "GENERATE_STUDY_PLAN"
    GENERATE_PARENT_REPORT = "GENERATE_PARENT_REPORT"
    RECORD_CONSENT = "RECORD_CONSENT"


class ActionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class StampStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"


class EventType(str, Enum):
    ACTION_SUBMITTED = "ACTION_SUBMITTED"
    STAMP_ISSUED = "STAMP_ISSUED"
    STAMP_REJECTED = "STAMP_REJECTED"
    CONSTITUTIONAL_VIOL = "CONSTITUTIONAL_VIOL"
    LLM_CALL_COMPLETED = "LLM_CALL_COMPLETED"
    LLM_CALL_FAILED = "LLM_CALL_FAILED"
    ETHER_PROFILE_HIT = "ETHER_PROFILE_HIT"
    ETHER_PROFILE_MISS = "ETHER_PROFILE_MISS"
    DIAGNOSTIC_RUN = "DIAGNOSTIC_RUN"
    STUDY_PLAN_GENERATED = "STUDY_PLAN_GENERATED"
    PARENT_REPORT_GENERATED = "PARENT_REPORT_GENERATED"
    CONSENT_RECORDED = "CONSENT_RECORDED"


class EtherArchetype(str, Enum):
    KETER = "KETER"
    CHOKHMAH = "CHOKHMAH"
    BINAH = "BINAH"
    CHESED = "CHESED"
    GEVURAH = "GEVURAH"
    TIFERET = "TIFERET"
    NETZACH = "NETZACH"
    HOD = "HOD"
    YESOD = "YESOD"
    MALKUTH = "MALKUTH"


class ConstitutionalRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    category: RuleCategory
    severity: RuleSeverity
    check_prompt: str
    source: str
    applies_to: frozenset[ActionType]
    is_active: bool = True


class ExecutiveAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_type: ActionType
    learner_id_hash: str
    grade: int = Field(ge=0, le=7)
    params: dict[str, Any]
    claimed_rules: list[str]
    status: ActionStatus = ActionStatus.PENDING
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    @field_validator("params")
    @classmethod
    def _reject_pii_in_params(cls, v: dict[str, Any]) -> dict[str, Any]:
        forbidden_keys = {"learner_id", "guardian_email", "email", "phone", "sa_id"}
        for key in v:
            lk = key.lower()
            if lk in forbidden_keys or ("learner" in lk and "id" in lk):
                raise ValueError("PII pattern in params keys is forbidden")
            if lk == "guardian_email":
                raise ValueError("PII pattern in params keys is forbidden")
        blob = str(v).lower()
        if re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", blob):
            raise ValueError("PII pattern detected in params values")
        return v


class JudiciaryStamp(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_id: str
    status: StampStatus
    rules_evaluated: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    reasoning: str = ""
    latency_ms: int = 0


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: EventType
    pillar: str
    action_id: Optional[str] = None
    learner_hash: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EtherToneParams(BaseModel):
    model_config = ConfigDict(frozen=True)

    warmth_level: float = Field(default=0.65, ge=0.0, le=1.0)
    challenge_tolerance: float = Field(default=0.55, ge=0.0, le=1.0)
    pacing: str = "moderate"
    preferred_modality: str = "visual"
    encouragement_freq: str = "moderate"
    sa_cultural_depth: str = "moderate"
    repetition_factor: float = Field(default=1.2, ge=1.0)


class LearnerEtherProfile(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    learner_hash: str
    archetype: EtherArchetype
    tone_params: EtherToneParams
    confidence_score: float = 0.3
    data_points: int = 0
    expires_at: Optional[datetime] = None

    def to_prompt_modifier(self) -> str:
        return (
            f"[LEARNER PROFILE — {self.archetype.value}]\n"
            f"Warmth={self.tone_params.warmth_level:.2f}, pacing={self.tone_params.pacing}, "
            f"modality={self.tone_params.preferred_modality}."
        )


class OperationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    stamp_status: str = "PENDING"
    constitutional_health: float = Field(default=0.0, ge=0.0, le=1.0)
    stamp_id: Optional[str] = None
    ether_archetype: Optional[str] = None
    latency_ms: int = 0
