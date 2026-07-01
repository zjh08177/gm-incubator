from gm.stats import weaknesses


def test_ranks_by_winprob_lost_desc(seeded):
    ranked = weaknesses.rank(seeded)
    cats = [r["category"] for r in ranked]
    assert cats[0] == "dropped_material"        # 0.4+0.15 = 0.55 total
    assert "missed_tactic" in cats
    assert all("example" in r for r in ranked)


def test_only_counts_my_moves(seeded):
    ranked = weaknesses.rank(seeded)
    dropped = next(r for r in ranked if r["category"] == "dropped_material")
    assert dropped["count"] == 2                # opponent's dropped piece excluded


def test_had_time_only_filters_low_clock(seeded):
    ranked = weaknesses.rank(seeded, had_time_only=True)
    dropped = next(r for r in ranked if r["category"] == "dropped_material")
    assert dropped["count"] == 1               # the low_clock mistake removed
