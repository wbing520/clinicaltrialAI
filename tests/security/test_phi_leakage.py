from src.llm.prompt_engineering.templates import sanitize_prompt

def test_no_phi_in_prompt():
    text = "Name: John Doe, Phone: 555-1212, Note: chest pain"
    out = sanitize_prompt(text)
    assert "John" not in out and "555" not in out
