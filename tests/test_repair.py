from worldsmith.ai.repair import PlanRepairAgent


def test_repair_agent_uses_first_available_provider(monkeypatch):
    class FakeSettings:
        openai_key = "key"
        openai_model = "gpt"
        gemini_key = ""
        gemini_model = "gemini"
        ollama_url = "http://localhost:11434"
        ollama_model = "llama"
        ai_reasoning = "high"

    agent = PlanRepairAgent(FakeSettings())
    monkeypatch.setattr(agent, "_call", lambda provider, prompt: type("Resp", (), {"provider": provider, "text": '{"summary":"repaired","builds":[]}'})())
    events = []
    result = agent.repair({"builds": [{"type": "bad"}]}, [{"severity": "warning", "message": "overlap"}], events.append)
    assert result.provider == "openai"
    assert result.plan["summary"] == "repaired"
    assert any("revising" in event.lower() for event in events)
