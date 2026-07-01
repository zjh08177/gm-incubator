from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "gm-coach" / "SKILL.md"


def test_skill_exists_and_declares_tools():
    text = SKILL.read_text()
    for cmd in ["gm weaknesses", "gm repertoire", "gm stats",
                "gm search-games", "gm find-positions", "gm game"]:
        assert cmd in text
    assert "never invent" in text.lower() or "do not invent" in text.lower()
    assert "--json" in text


def test_skill_grants_reasoning_not_narration():
    """Lock the coach-redesign fix: reasoning is licensed, the narrator ban is gone."""
    text = SKILL.read_text()
    low = text.lower()
    # the root-cause bug: the old prompt banned the model's chess reasoning
    assert "never compute chess facts yourself" not in low
    # two-tier trust boundary + reasoning granted
    assert "trust boundary" in low
    assert "judgment is yours" in low
    # verdict-first answer contract R1–R8 present
    for r in ["R1", "R2", "R3", "R7", "R8"]:
        assert r in text
    # truth-over-sharpness: the defensive read is hedged, not sold as a measured trait
    assert "consistent with" in low
