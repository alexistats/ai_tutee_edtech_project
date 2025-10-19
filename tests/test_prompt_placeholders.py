from pathlib import Path

PROMPT_PATH = Path("app/prompts/system_ai_student.md")
REQUIRED_PLACEHOLDERS = (
    "{{KNOWLEDGE_LEVEL}}",
    "{{TARGET_SUBSKILLS}}",
    "{{MISCONCEPTIONS}}",
    "{{RELEASE_ANSWERS_POLICY}}",
    "{{TONE}}",
    "{{TURN_BUDGET}}",
)


def test_prompt_file_exists():
    assert PROMPT_PATH.exists(), "system prompt file is missing"


def test_prompt_contains_placeholders():
    content = PROMPT_PATH.read_text()
    for token in REQUIRED_PLACEHOLDERS:
        assert token in content, f"Missing placeholder: {token}"
