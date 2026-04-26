"""
EduBoost SA — IRT Adaptive Engine
Computerised Adaptive Testing using 2-Parameter Logistic (2PL) IRT model.
Finds the learner's exact knowledge floor via gap-probe cascade.
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

import numpy as np
from scipy.optimize import minimize_scalar


class SubjectCode(str, Enum):
    MATH = "MATH"
    ENG = "ENG"
    LIFE = "LIFE"
    NS = "NS"
    SS = "SS"


@dataclass
class Item:
    item_id: str
    subject: SubjectCode
    grade: int
    concept_code: str
    difficulty_b: float
    discrimination_a: float
    question_text: str
    options: List[str]
    correct_index: int
    story_context: str = ""
    difficulty_label: str = "Medium"


@dataclass
class Response:
    item_id: str
    is_correct: bool
    time_on_task_ms: int
    hint_used: bool = False


@dataclass
class AssessmentSession:
    learner_grade: int
    subject: SubjectCode
    current_grade: int = field(init=False)
    theta: float = 0.0
    sem: float = 1.5
    responses: List[Response] = field(default_factory=list)
    gap_probe_active: bool = False
    gap_probe_grades: List[int] = field(default_factory=list)

    def __post_init__(self):
        self.current_grade = self.learner_grade


# ── IRT Core Functions ────────────────────────────────────────────────────────

def p_correct(theta: float, a: float, b: float) -> float:
    return 1.0 / (1.0 + math.exp(-a * (theta - b)))


def fisher_information(theta: float, a: float, b: float) -> float:
    p = p_correct(theta, a, b)
    return (a ** 2) * p * (1 - p)


def update_theta_mle(responses: List[Response], items: Dict[str, Item]) -> tuple:
    if not responses:
        return 0.0, 1.5

    def neg_log_likelihood(theta):
        ll = 0.0
        for r in responses:
            item = items.get(r.item_id)
            if not item:
                continue
            p = p_correct(theta, item.discrimination_a, item.difficulty_b)
            p = max(1e-10, min(1 - 1e-10, p))
            ll += math.log(p) if r.is_correct else math.log(1 - p)
        return -ll

    result = minimize_scalar(neg_log_likelihood, bounds=(-4, 4), method="bounded")
    theta_hat = result.x

    total_info = sum(
        fisher_information(theta_hat, items[r.item_id].discrimination_a, items[r.item_id].difficulty_b)
        for r in responses
        if r.item_id in items
    )
    sem = 1.0 / math.sqrt(total_info) if total_info > 0 else 1.5
    return float(theta_hat), float(sem)


def select_next_item(
    session: AssessmentSession,
    available_items: List[Item],
    administered_ids: set,
) -> Optional[Item]:
    eligible = [
        item for item in available_items
        if item.item_id not in administered_ids
        and item.grade == session.current_grade
        and item.subject == session.subject
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda item: fisher_information(session.theta, item.discrimination_a, item.difficulty_b))


def should_stop(session: AssessmentSession, max_questions: int = 20) -> bool:
    return session.sem < 0.3 or len(session.responses) >= max_questions


def check_gap_trigger(session: AssessmentSession, grade_floor: float = -1.5) -> bool:
    return session.theta < grade_floor and not session.gap_probe_active


def activate_gap_probe(session: AssessmentSession) -> bool:
    probe_grade = session.current_grade - 1
    if probe_grade < 0:
        return False
    session.current_grade = probe_grade
    session.gap_probe_active = True
    session.gap_probe_grades.append(probe_grade)
    session.theta = 0.0
    session.sem = 1.5
    return True


def compute_mastery_score(theta: float) -> float:
    return float(np.clip((theta + 4) / 8, 0.0, 1.0))


def build_gap_report(session: AssessmentSession) -> dict:
    mastery = compute_mastery_score(session.theta)
    has_gap = session.gap_probe_active or mastery < 0.6
    return {
        "subject": session.subject.value,
        "assessed_grade": session.learner_grade,
        "mastered_at_grade": session.current_grade,
        "theta": round(session.theta, 3),
        "sem": round(session.sem, 3),
        "mastery_score": round(mastery, 3),
        "mastery_pct": round(mastery * 100),
        "has_gap": has_gap,
        "gap_severity": round(1.0 - mastery, 3) if has_gap else 0.0,
        "gap_grade_levels": session.learner_grade - session.current_grade,
        "probe_grades_visited": session.gap_probe_grades,
        "questions_administered": len(session.responses),
        "correct_count": sum(1 for r in session.responses if r.is_correct),
    }


# ── In-memory item bank ────────────────────────────────────────────────────────

SAMPLE_ITEMS: List[Item] = [
    Item("GR3_MATH_FRAC_01", SubjectCode.MATH, 3, "GR3_MATH_FRAC",
         -0.5, 1.2, "Sipho cuts his pizza into 4 equal pieces and eats 1. What fraction did he eat?",
         ["1/2", "1/4", "1/3", "4/1"], 1,
         "At the school tuck shop, Sipho buys a small pizza.", "Easy"),
    Item("GR3_MATH_FRAC_02", SubjectCode.MATH, 3, "GR3_MATH_FRAC",
         0.3, 1.4, "Ntombi has 12 apples. She takes half. How many does she take?",
         ["4", "6", "8", "3"], 1,
         "Gogo has a fruit bowl with 12 apples on the stoep.", "Easy"),
    Item("GR3_MATH_FRAC_03", SubjectCode.MATH, 3, "GR3_MATH_FRAC",
         0.9, 1.6, "A chocolate bar has 8 pieces. Thabo eats 2/8 of it. How many pieces?",
         ["2", "4", "6", "1"], 0,
         "Thabo bought a Cadbury chocolate at the café.", "Medium"),
    Item("GR2_MATH_ADD_01", SubjectCode.MATH, 2, "GR2_MATH_ADD",
         -1.0, 1.1, "What is 15 + 27?",
         ["42", "41", "43", "40"], 0,
         "Lindiwe is counting rands in her piggy bank.", "Easy"),
    Item("GR2_MATH_MULT_01", SubjectCode.MATH, 2, "GR2_MATH_MULT",
         0.5, 1.3, "What is 9 × 4?",
         ["36", "32", "38", "34"], 0,
         "There are 9 tables in the school hall, each with 4 chairs.", "Medium"),
    Item("GR3_ENG_SPELL_01", SubjectCode.ENG, 3, "GR3_ENG_SPELL",
         -0.8, 1.2, "Choose the correct spelling:",
         ["Elefant", "Elephant", "Elephent", "Elifant"], 1,
         "We're writing a story about animals on the veld.", "Easy"),
    Item("GR3_ENG_GRAM_01", SubjectCode.ENG, 3, "GR3_ENG_GRAM",
         0.2, 1.5, "Which word is a noun in: 'The lion ran fast'?",
         ["ran", "fast", "the", "lion"], 3,
         "Reading a story about Kruger National Park.", "Medium"),
    Item("GR3_LIFE_UBU_01", SubjectCode.LIFE, 3, "GR3_LIFE_UBU",
         -1.2, 1.0, "Ubuntu means:",
         ["I am strong", "I am because we are", "Work alone", "Be the best"], 1,
         "Your teacher is teaching about South African values.", "Easy"),
    Item("GR3_NS_ANIM_01", SubjectCode.NS, 3, "GR3_NS_ANIM",
         -0.6, 1.1, "Which animal is a herbivore?",
         ["Lion", "Crocodile", "Elephant", "Shark"], 2,
         "On a game drive in the Kruger, you spot many animals.", "Easy"),
    Item("GR3_SS_CAP_01", SubjectCode.SS, 3, "GR3_SS_CAP",
         0.1, 1.3, "What is the seat of government capital of South Africa?",
         ["Cape Town", "Johannesburg", "Pretoria", "Durban"], 2,
         "Learning about our beautiful country.", "Medium"),
]

ITEM_BANK: Dict[str, Item] = {item.item_id: item for item in SAMPLE_ITEMS}
