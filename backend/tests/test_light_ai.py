from app.services.leads.light_ai import run_light_ai
from app.services.llm.base import LLMResult
from app.services.llm.logged import LoggedLLMCall


async def test_run_light_ai_returns_company_description_from_json(monkeypatch):
    captured_prompt = ""

    class FakeClient:
        model = "test-model"

    async def fake_logged_chat(client, messages, **kwargs):
        nonlocal captured_prompt
        captured_prompt = messages[0].content
        return LLMResult(
            content=(
                '{"industry":"Automation","city":"Ekaterinburg",'
                '"description":"Компания внедряет промышленную автоматизацию для производственных линий.",'
                '"is_commercial":true,"is_relevant_to_icp":true,'
                '"relevance_score":72,"pass_to_deep_ai":true}'
            )
        )

    monkeypatch.setattr("app.services.leads.light_ai.get_llm_client", lambda purpose, **kwargs: FakeClient())
    monkeypatch.setattr("app.services.leads.light_ai.logged_chat", fake_logged_chat)

    result = await run_light_ai(
        title="Prom Tech",
        meta_description="Industrial automation",
        h1="Prom Tech",
        about_text="О компании Prom Tech внедряет промышленную автоматизацию.",
        visible_text_snippet="Hero text",
        email="sales@prom.test",
        phone="+7 343 222-33-44",
        icp_description="automation clients",
        city="Ekaterinburg",
        log=LoggedLLMCall(),
    )

    assert "About section: О компании Prom Tech внедряет промышленную автоматизацию." in captured_prompt
    assert "Запрещено писать общую зацепку" in captured_prompt
    assert result.description == "Компания внедряет промышленную автоматизацию для производственных линий."
    assert result.pass_to_deep_ai is True
