from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "gm-coach" / "SKILL.md"


def test_skill_exists_and_declares_tools():
    text = SKILL.read_text()
    for cmd in ["gm weaknesses", "gm repertoire", "gm stats",
                "gm search-games", "gm find-positions", "gm game"]:
        assert cmd in text
    assert "never invent" in text.lower() or "do not invent" in text.lower()
    assert "--json" in text
