"""
EduBoost SA — Lesson Generation Service
Builds CAPS-aligned, SA-contextual lessons using the Inference Gateway.
No PII flows into prompts.
"""
import hashlib
import json
import random
import time
from typing import Optional, Tuple
from pydantic import BaseModel, Field, ValidationError

from app.api.services.inference_gateway import call_llm, parse_json_response
import structlog

log = structlog.get_logger()


# ============================================================================
# Lesson Caching System
# ============================================================================

class LessonCache:
    """Simple in-memory TTL cache for generated lessons."""
    
    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 1000):
        self._cache: dict[str, tuple[dict, float]] = {}
        self._ttl = ttl_seconds
        self._max_entries = max_entries
    
    def _generate_key(self, params: LessonParams) -> str:
        """Generate cache key from lesson parameters."""
        key_data = {
            "grade": params.grade,
            "subject_code": params.subject_code,
            "subject_label": params.subject_label,
            "topic": params.topic,
            "home_language": params.home_language,
            "learning_style_primary": params.learning_style_primary,
            "mastery_prior": params.mastery_prior,
            "has_gap": params.has_gap,
            "gap_grade": params.gap_grade,
            "sa_theme": params.sa_theme,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]
    
    def get(self, params: LessonParams) -> Optional[GeneratedLesson]:
        """Get cached lesson if available and not expired."""
        key = self._generate_key(params)
        if key in self._cache:
            lesson_data, cached_at = self._cache[key]
            if time.time() - cached_at < self._ttl:
                log.info("lesson_cache.hit", key=key[:8], topic=params.topic)
                return GeneratedLesson.model_validate(lesson_data)
            else:
                # Expired - remove from cache
                del self._cache[key]
                log.info("lesson_cache.expired", key=key[:8])
        return None
    
    def set(self, params: LessonParams, lesson: GeneratedLesson) -> None:
        """Cache a generated lesson."""
        # Simple eviction: remove oldest if at capacity
        if len(self._cache) >= self._max_entries:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
            log.info("lesson_cache.evicted", key=oldest_key[:8])
        
        key = self._generate_key(params)
        self._cache[key] = (lesson.model_dump(), time.time())
        log.info("lesson_cache.stored", key=key[:8], topic=params.topic)
    
    def clear(self) -> int:
        """Clear all cached lessons. Returns count of entries cleared."""
        count = len(self._cache)
        self._cache.clear()
        log.info("lesson_cache.cleared", count=count)
        return count
    
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "entries": len(self._cache),
            "max_entries": self._max_entries,
            "ttl_seconds": self._ttl,
        }


# Global cache instance (1 hour TTL, 1000 max entries)
_lesson_cache = LessonCache(ttl_seconds=3600, max_entries=1000)


def get_lesson_cache() -> LessonCache:
    """Get the global lesson cache instance."""
    return _lesson_cache


class LLMOutputValidationError(Exception):
    """
    Raised when LLM output fails Pydantic schema validation
    (Phase 1, item #6). Routers should map this to HTTP 422.
    """

    def __init__(self, message: str, errors: list | None = None, raw: str | None = None):
        super().__init__(message)
        self.errors = errors or []
        self.raw = (raw or "")[:500]

SA_THEMES = [
    "sharing food at a family braai",
    "buying sweets at a tuck shop",
    "counting animals on a game reserve",
    "travelling between SA cities",
    "growing a vegetable garden",
    "playing soccer on a dusty field",
    "going to a spaza shop",
    "collecting water at a communal tap",
]

GRADES = {0: "Grade R", 1: "Grade 1", 2: "Grade 2", 3: "Grade 3",
          4: "Grade 4", 5: "Grade 5", 6: "Grade 6", 7: "Grade 7"}

LEARNING_STYLES = ["visual", "auditory", "kinesthetic"]


class LessonParams(BaseModel):
    """Anonymised pedagogical parameters — safe to pass to LLM."""
    grade: int = Field(ge=0, le=7)
    subject_code: str
    subject_label: str
    topic: str
    home_language: str = "English"
    learning_style_primary: str = "visual"
    mastery_prior: float = Field(default=0.5, ge=0.0, le=1.0)
    has_gap: bool = False
    gap_grade: Optional[int] = None
    sa_theme: Optional[str] = None


class GeneratedLesson(BaseModel):
    title: str
    story_hook: str
    visual_anchor: str = ""
    steps: list
    practice: list
    try_it: Optional[dict] = None
    xp: int = 35
    badge: Optional[str] = None


SYSTEM_PROMPT = """You are EduBoost, a warm South African educational assistant for primary school learners (Grade R–7).
You strictly follow the CAPS (Curriculum and Assessment Policy Statement) curriculum.

RULES:
1. NEVER include any learner name, ID, email or personal information in responses.
2. Use authentic South African contexts: rands/cents, braai, ubuntu, spaza shops, SA animals (kudu, springbok, protea), SA cities and townships.
3. Vocabulary must match the grade level. Grade R-2: very simple, max 8 words/sentence. Grade 3-5: 12 words. Grade 6-7: 15 words.
4. For VISUAL learners: use ASCII/Unicode diagrams, spatial metaphors, and emoji-rich explanations.
5. For AUDITORY learners: use rhymes, repetition, and verbal mnemonics.
6. For KINESTHETIC learners: emphasise hands-on Try It activities.
7. Always root abstract concepts in concrete, everyday SA examples.
8. Respond ONLY with valid JSON. No prose outside JSON."""


def build_lesson_prompts(params: LessonParams) -> Tuple[str, str]:
    """Build LLM prompts from anonymised lesson parameters only."""
    grade_name = GRADES.get(params.grade, "Grade 3")
    sa_theme = params.sa_theme or random.choice(SA_THEMES)
    style = params.learning_style_primary

    difficulty_note = ""
    if params.has_gap and params.gap_grade is not None:
        gap_name = GRADES.get(params.gap_grade, grade_name)
        difficulty_note = (
            f"NOTE: This learner has a knowledge gap at {gap_name} level. "
            f"Start from {gap_name} fundamentals before progressing to {grade_name} content."
        )

    user_prompt = f"""Generate a complete interactive CAPS lesson. Return ONLY valid JSON.

LESSON PARAMETERS:
- Grade: {grade_name}
- Subject: {params.subject_label}
- Topic: {params.topic}
- Home Language: {params.home_language}
- Primary Learning Style: {style}
- SA Context Theme: {sa_theme}
- Prior Mastery Level: {round(params.mastery_prior * 100)}%
{difficulty_note}

Return this EXACT JSON structure (no extra fields, no markdown):
{{
  "title": "lesson title with SA flavour (max 10 words)",
  "story_hook": "1-2 sentence SA story opener to engage the learner (max 60 words)",
  "visual_anchor": "ASCII or Unicode diagram illustrating the core concept (use line breaks \\n)",
  "steps": [
    {{
      "heading": "step title",
      "body": "explanation in simple language (max 80 words)",
      "visual": "emoji or short diagram for this step",
      "sa_example": "concrete SA real-world example"
    }}
  ],
  "practice": [
    {{
      "question": "question text with SA context",
      "options": ["option A", "option B", "option C", "option D"],
      "correct": 0,
      "hint": "brief hint without giving away the answer",
      "feedback": "encouraging feedback using SA phrases (Yebo!/Sharp sharp!/Lekker!)"
    }}
  ],
  "try_it": {{
    "title": "activity title",
    "materials": ["household item 1", "household item 2"],
    "instructions": "numbered steps using everyday SA household items (max 80 words)"
  }},
  "xp": 35,
  "badge": "optional badge name if this completes a set (or null)"
}}

Rules:
- Include exactly 2 steps
- Include exactly 3 practice questions
- Keep language appropriate for {grade_name}
- All examples must use South African contexts"""

    return SYSTEM_PROMPT, user_prompt


async def generate_lesson_from_prompts(system_prompt: str, user_prompt: str) -> GeneratedLesson:
    text = await call_llm(system_prompt, user_prompt, max_tokens=1600)
    try:
        data = parse_json_response(text)
    except (ValueError, json.JSONDecodeError) as e:
        log.warning("lesson_service.invalid_json", error=str(e))
        raise LLMOutputValidationError(
            "LLM did not return valid JSON", errors=[{"msg": str(e)}], raw=text
        ) from e
    try:
        return GeneratedLesson.model_validate(data)
    except ValidationError as e:
        log.warning("lesson_service.schema_mismatch", errors=e.errors())
        raise LLMOutputValidationError(
            "LLM output failed lesson schema validation",
            errors=e.errors(),
            raw=text,
        ) from e


async def generate_lesson(params: LessonParams) -> GeneratedLesson:
    """
    Generate a complete CAPS-aligned lesson.
    params must contain ZERO learner PII.
    
    Uses caching to avoid regenerating identical lessons.
    """
    # Check cache first
    cache = get_lesson_cache()
    cached_lesson = cache.get(params)
    if cached_lesson is not None:
        return cached_lesson
    
    # Generate new lesson
    grade_name = GRADES.get(params.grade, "Grade 3")
    system_prompt, user_prompt = build_lesson_prompts(params)
    log.info("lesson_service.generate", grade=grade_name, subject=params.subject_code, topic=params.topic)
    lesson = await generate_lesson_from_prompts(system_prompt, user_prompt)
    
    # Cache the generated lesson
    cache.set(params, lesson)
    
    return lesson


async def generate_study_plan(
    grade: int,
    knowledge_gaps: list,
    subjects_mastery: dict,
) -> dict:
    """
    Generate a CAPS-aligned weekly study plan.
    Accepts only anonymised mastery data — no learner PII.
    """
    grade_name = GRADES.get(grade, "Grade 3")
    gaps_summary = ", ".join([f"{g['subject']} at {GRADES.get(g.get('gap_grade', grade), grade_name)} level" for g in knowledge_gaps]) if knowledge_gaps else "none detected"

    system = "You are a CAPS curriculum planner. Create personalised weekly study plans. Return ONLY valid JSON."
    user = f"""Create a one-week study plan.

Grade: {grade_name}
Knowledge Gaps: {gaps_summary}
Subject Mastery: {', '.join([f'{k}: {v}%' for k, v in subjects_mastery.items()])}

Return JSON:
{{
  "week_focus": "brief focus description (max 12 words)",
  "gap_ratio": 0.4,
  "days": {{
    "Mon": [{{"code": "SUBJ_TOPIC", "label": "Short name", "emoji": "emoji", "type": "gap-fill", "minutes": 15}}],
    "Tue": [...],
    "Wed": [...],
    "Thu": [...],
    "Fri": [...],
    "Sat": [{{"code": "REV", "label": "Weekend Review", "emoji": "⭐", "type": "grade-level", "minutes": 20}}],
    "Sun": []
  }}
}}

- 2-3 sessions per weekday, 1 on Saturday, none Sunday
- Mix "gap-fill" and "grade-level" types
- gap_ratio: proportion of gap-fill sessions (0.0-1.0)"""

    text = await call_llm(system, user, max_tokens=900)
    return parse_json_response(text)


async def generate_parent_report(
    grade: int,
    streak_days: int,
    total_xp: int,
    subjects_mastery: dict,
    gaps: list,
) -> dict:
    """
    Generate a parent-facing progress report.
    Uses only aggregate, anonymised metrics — no learner name or PII.
    """
    grade_name = GRADES.get(grade, "Grade 3")

    system = "You are an educational progress report generator for South African parents. Be warm, encouraging, and use SA cultural references. Return only JSON."
    user = f"""Generate a parent progress report.

Grade: {grade_name}
Learning Streak: {streak_days} days
Total XP Earned: {total_xp}
Subject Mastery: {', '.join([f'{k}: {v}%' for k, v in subjects_mastery.items()])}
Knowledge Gaps: {', '.join([g.get('subject', '') for g in gaps]) or 'none'}

Return JSON:
{{
  "summary": "2 encouraging sentences about progress",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "areas_to_improve": ["area 1", "area 2"],
  "recommendation": "1-2 sentence practical tip a SA parent can do at home",
  "next_milestones": ["milestone 1", "milestone 2"]
}}"""

    text = await call_llm(system, user, max_tokens=700)
    return parse_json_response(text)
