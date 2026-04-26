"""Integration tests for the Lesson Generation endpoint."""
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock
from app.api.main import app

MOCK_LESSON_JSON = """{"title":"Fractions at the Braai","story_hook":"Mama is making pap for 4 cousins.","visual_anchor":"[whole] -> [1/2][1/2]","steps":[{"heading":"What is a Half?","body":"Cut into 2 equal parts.","visual":"🟡🟡","sa_example":"Cut a koeksister in half."},{"heading":"What is a Quarter?","body":"Cut into 4 equal parts.","visual":"🍕","sa_example":"A quarter of a pizza at the tuck shop."}],"practice":[{"question":"Sipho eats 1 of 4 pieces. What fraction?","options":["1/2","1/4","1/3","2/4"],"correct":1,"hint":"Count the total pieces.","feedback":"Yebo! Sharp sharp!"},{"question":"Ntombi cuts a cake into 2 equal pieces. What is each piece?","options":["1/4","1/3","1/2","2/1"],"correct":2,"hint":"Two equal pieces.","feedback":"Lekker work!"},{"question":"A pizza has 8 slices. Thabo eats 2. What fraction did he eat?","options":["2/8","1/4","1/2","8/2"],"correct":0,"hint":"Eaten over total.","feedback":"Haibo, well done!"}],"try_it":{"title":"Paper Folding","materials":["paper","pen"],"instructions":"1. Fold paper in half.\\n2. Open it — you have 2 equal halves!\\n3. Fold again for quarters."},"xp":35,"badge":"Fraction Fan"}"""


@pytest.mark.asyncio
@pytest.mark.integration
class TestLessonGeneration:

    async def test_generate_lesson_success(self):
        with patch("app.api.services.lesson_service.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = MOCK_LESSON_JSON
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/lessons/generate", json={
                    "learner_id": "00000000-0000-0000-0000-000000000001",
                    "subject_code": "MATH",
                    "subject_label": "Mathematics",
                    "topic": "Fractions",
                    "grade": 3,
                    "home_language": "English",
                    "learning_style_primary": "visual",
                    "mastery_prior": 0.38,
                    "has_gap": True,
                    "gap_grade": 2,
                })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "lesson" in data
        assert data["lesson"]["title"] == "Fractions at the Braai"
        assert len(data["lesson"]["practice"]) == 3

    async def test_learner_id_never_in_llm_call(self):
        """POPIA: learner_id must NEVER appear in the LLM prompt."""
        learner_id = "00000000-0000-0000-0000-000000000001"
        captured_prompts = []

        async def capture_prompt(system, user, **kwargs):
            captured_prompts.append({"system": system, "user": user})
            return MOCK_LESSON_JSON

        with patch("app.api.services.lesson_service.call_llm", side_effect=capture_prompt):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                await client.post("/api/v1/lessons/generate", json={
                    "learner_id": learner_id,
                    "subject_code": "MATH",
                    "subject_label": "Mathematics",
                    "topic": "Fractions",
                    "grade": 3,
                })

        for prompt in captured_prompts:
            assert learner_id not in prompt["system"], "Learner ID found in system prompt — POPIA violation!"
            assert learner_id not in prompt["user"], "Learner ID found in user prompt — POPIA violation!"

    async def test_generate_lesson_llm_failure_returns_503(self):
        with patch("app.api.services.lesson_service.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = RuntimeError("All LLM providers failed")
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/lessons/generate", json={
                    "learner_id": "00000000-0000-0000-0000-000000000001",
                    "subject_code": "MATH",
                    "subject_label": "Mathematics",
                    "topic": "Fractions",
                    "grade": 3,
                })
        assert response.status_code == 503
