from worldsmith.ai.orchestrator import extract_json

def test_extract_fenced_json():
    assert extract_json('```json\n{"a":1}\n```') == {'a':1}
