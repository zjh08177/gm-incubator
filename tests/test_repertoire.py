from gm.stats import repertoire


def test_groups_by_opening_and_scores(seeded):
    white = repertoire.by_color(seeded, "white")
    ital = next(r for r in white if r["opening"] == "Italian Game")
    assert ital["games"] == 1
    assert ital["wdl"] == [0, 0, 1]        # one loss
    assert ital["score"] == 0.0
    assert ital["break_ply"] == 5          # earliest opening/my error ply


def test_color_split(seeded):
    black = repertoire.by_color(seeded, "black")
    assert any(r["opening"] == "Sicilian Defense" for r in black)
    assert all(r["opening"] != "Italian Game" for r in black)
