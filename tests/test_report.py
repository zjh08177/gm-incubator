from gm import report


def test_weaknesses_md_has_headers_and_rows():
    ranked = [{"category": "dropped_material", "count": 2, "winprob_lost": 0.55,
               "example": {"game_uuid": "gA", "ply": 5, "san": "Ne3"}}]
    md = report.weaknesses_md(ranked, ranked)
    assert "# Weakness Report" in md
    assert "dropped_material" in md and "gA" in md


def test_repertoire_md_splits_colors():
    w = [{"opening": "Italian Game", "eco": "C50", "games": 1, "score": 0.0,
          "wdl": [0, 0, 1], "break_ply": 5}]
    md = report.repertoire_md(w, [])
    assert "As White" in md and "Italian Game" in md
