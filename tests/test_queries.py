from gm.stats import overview, queries


def test_overview_counts(seeded):
    s = overview.summary(seeded)
    assert s["games"] == 2
    assert s["by_time_class"]["bullet"] == 2


def test_search_games_by_result(seeded):
    losses = queries.search_games(seeded, result="loss")
    assert [g["uuid"] for g in losses] == ["gA"]


def test_find_positions_by_category(seeded):
    hits = queries.find_positions(seeded, error_type="missed_tactic")
    assert len(hits) == 1 and hits[0]["game_uuid"] == "gB"


def test_find_positions_had_time_filter(seeded):
    hits = queries.find_positions(seeded, error_type="dropped_material", had_time=True)
    assert len(hits) == 1                      # excludes the low_clock one


def test_one_game_returns_moves(seeded):
    g = queries.one_game(seeded, "gA")
    assert g["uuid"] == "gA"
    assert len(g["moves"]) >= 1
