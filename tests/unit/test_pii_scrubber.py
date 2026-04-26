"""Unit tests for the Inference Gateway PII scrubber."""
import pytest
from app.api.services.inference_gateway import scrub_pii, scrub_dict


class TestPIIScrubber:
    def test_removes_sa_id_number(self):
        text = "Learner ID: 9001015009087 completed lesson"
        result = scrub_pii(text)
        assert "9001015009087" not in result
        assert "[SA_ID]" in result

    def test_removes_email_address(self):
        text = "Contact parent at nomvula.dlamini@gmail.com for report"
        result = scrub_pii(text)
        assert "nomvula.dlamini@gmail.com" not in result
        assert "[EMAIL]" in result

    def test_removes_sa_mobile_number(self):
        text = "Guardian phone: 0823456789"
        result = scrub_pii(text)
        assert "0823456789" not in result
        assert "[PHONE]" in result

    def test_preserves_non_pii_content(self):
        text = "Grade 3 learner scored 75% on fractions assessment."
        result = scrub_pii(text)
        assert "Grade 3" in result
        assert "75%" in result
        assert "fractions" in result

    def test_scrubs_dict_recursively(self):
        data = {
            "grade": 3,
            "subject": "MATH",
            "guardian_note": "Call 0823456789",
        }
        result = scrub_dict(data)
        assert result["grade"] == 3
        assert result["subject"] == "MATH"
        assert "0823456789" not in result["guardian_note"]

    def test_does_not_alter_lesson_content(self):
        lesson_text = '{"title": "Fractions at the Braai", "xp": 35}'
        result = scrub_pii(lesson_text)
        assert "Fractions at the Braai" in result
        assert "35" in result
