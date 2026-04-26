"""Unit tests for the IRT Adaptive Engine."""
import pytest
import math
from app.api.ml.irt_engine import (
    p_correct, fisher_information, update_theta_mle,
    select_next_item, should_stop, check_gap_trigger,
    activate_gap_probe, compute_mastery_score, build_gap_report,
    AssessmentSession, Response, Item, SubjectCode, ITEM_BANK, SAMPLE_ITEMS,
)


class TestIRTCore:
    def test_p_correct_at_matching_difficulty(self):
        """When theta == b, probability should be 0.5 for any a."""
        assert abs(p_correct(0.5, 1.0, 0.5) - 0.5) < 0.001

    def test_p_correct_increases_with_theta(self):
        """Higher ability should give higher probability."""
        p_low = p_correct(-1.0, 1.0, 0.0)
        p_high = p_correct(1.0, 1.0, 0.0)
        assert p_high > p_low

    def test_fisher_information_peaks_at_difficulty(self):
        """Fisher information should peak when theta == b."""
        info_at_b = fisher_information(0.5, 1.2, 0.5)
        info_away = fisher_information(2.0, 1.2, 0.5)
        assert info_at_b > info_away

    def test_compute_mastery_score_range(self):
        """Mastery score should always be in [0, 1]."""
        for theta in [-4, -2, 0, 2, 4]:
            score = compute_mastery_score(theta)
            assert 0.0 <= score <= 1.0

    def test_compute_mastery_score_midpoint(self):
        """Theta of 0 should give approximately 0.5 mastery."""
        assert abs(compute_mastery_score(0.0) - 0.5) < 0.01


class TestThetaUpdate:
    def test_theta_increases_after_correct_answers(self):
        items = ITEM_BANK
        responses_correct = [Response("GR3_MATH_FRAC_01", True, 5000)]
        responses_wrong = [Response("GR3_MATH_FRAC_01", False, 5000)]
        theta_correct, _ = update_theta_mle(responses_correct, items)
        theta_wrong, _ = update_theta_mle(responses_wrong, items)
        assert theta_correct > theta_wrong

    def test_sem_decreases_with_more_responses(self):
        items = ITEM_BANK
        one_response = [Response("GR3_MATH_FRAC_01", True, 3000)]
        two_responses = [
            Response("GR3_MATH_FRAC_01", True, 3000),
            Response("GR3_MATH_FRAC_02", True, 4000),
        ]
        _, sem_one = update_theta_mle(one_response, items)
        _, sem_two = update_theta_mle(two_responses, items)
        assert sem_two < sem_one

    def test_empty_responses_returns_defaults(self):
        theta, sem = update_theta_mle([], ITEM_BANK)
        assert theta == 0.0
        assert sem == 1.5


class TestAdaptiveSelection:
    def test_selects_item_for_current_grade(self):
        session = AssessmentSession(learner_grade=3, subject=SubjectCode.MATH)
        item = select_next_item(session, SAMPLE_ITEMS, set())
        assert item is not None
        assert item.grade == 3

    def test_excludes_administered_items(self):
        session = AssessmentSession(learner_grade=3, subject=SubjectCode.MATH)
        first = select_next_item(session, SAMPLE_ITEMS, set())
        second = select_next_item(session, SAMPLE_ITEMS, {first.item_id})
        assert second is None or second.item_id != first.item_id


class TestStoppingRules:
    def test_stops_when_max_questions_reached(self):
        session = AssessmentSession(learner_grade=3, subject=SubjectCode.MATH)
        session.responses = [Response(f"q{i}", True, 1000) for i in range(20)]
        assert should_stop(session, max_questions=20) is True

    def test_stops_when_sem_low(self):
        session = AssessmentSession(learner_grade=3, subject=SubjectCode.MATH)
        session.sem = 0.2
        assert should_stop(session) is True

    def test_continues_when_sem_high(self):
        session = AssessmentSession(learner_grade=3, subject=SubjectCode.MATH)
        session.sem = 0.8
        session.responses = [Response("q1", True, 1000)]
        assert should_stop(session) is False


class TestGapProbe:
    def test_triggers_when_theta_below_floor(self):
        session = AssessmentSession(learner_grade=3, subject=SubjectCode.MATH)
        session.theta = -2.0
        assert check_gap_trigger(session) is True

    def test_does_not_trigger_above_floor(self):
        session = AssessmentSession(learner_grade=3, subject=SubjectCode.MATH)
        session.theta = 0.5
        assert check_gap_trigger(session) is False

    def test_probe_decrements_grade(self):
        session = AssessmentSession(learner_grade=3, subject=SubjectCode.MATH)
        session.theta = -2.0
        result = activate_gap_probe(session)
        assert result is True
        assert session.current_grade == 2
        assert session.gap_probe_active is True

    def test_probe_stops_at_grade_r(self):
        session = AssessmentSession(learner_grade=0, subject=SubjectCode.MATH)
        session.theta = -2.0
        result = activate_gap_probe(session)
        assert result is False  # Cannot go below Grade R


class TestGapReport:
    def test_report_has_required_fields(self):
        session = AssessmentSession(learner_grade=3, subject=SubjectCode.MATH)
        session.theta = -1.0
        session.responses = [Response("GR3_MATH_FRAC_01", False, 5000)]
        report = build_gap_report(session)
        required = ["subject", "assessed_grade", "theta", "mastery_score", "mastery_pct", "has_gap"]
        for field in required:
            assert field in report

    def test_low_mastery_flagged_as_gap(self):
        session = AssessmentSession(learner_grade=3, subject=SubjectCode.MATH)
        session.theta = -2.5
        report = build_gap_report(session)
        assert report["has_gap"] is True
        assert report["mastery_pct"] < 60
