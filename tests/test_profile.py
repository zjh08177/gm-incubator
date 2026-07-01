from gm import profile


def test_profile_has_all_sections(seeded):
    md = profile.build(seeded)
    for heading in ("# Chess Profile", "## Opening Repertoire", "## Weakness Report",
                    "## Rating trend", "## Results by color", "## Where win% leaks"):
        assert heading in md, heading


def test_profile_reports_game_count_and_score(seeded):
    md = profile.build(seeded)
    assert "2 games" in md              # gA + gB in the seeded fixture
    # gA loss (white), gB win (black) -> overall score 0.5
    assert "0.50" in md


def test_profile_has_visual_encoding(seeded):
    md = profile.build(seeded)
    assert "█" in md or "░" in md                       # magnitude bars
    assert any(g in md for g in ("🟥", "🟧", "🟨", "🟩"))   # severity glyphs
    assert "<details>" in md                            # progressive disclosure


def test_color_winrate(seeded):
    cw = profile._color_winrate(seeded)
    assert cw["white"]["games"] == 1 and cw["white"]["wdl"] == [0, 0, 1]
    assert cw["black"]["games"] == 1 and cw["black"]["wdl"] == [1, 0, 0]


def test_profile_empty_db_does_not_crash(conn):
    md = profile.build(conn)
    assert "0 games" in md
