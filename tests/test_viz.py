from gm import viz


def test_bar_endpoints_and_width():
    assert viz.bar(0) == "░" * 10
    assert viz.bar(1) == "█" * 10
    assert viz.bar(0.5) == "█" * 5 + "░" * 5
    assert viz.bar(0.3, width=20) == "█" * 6 + "░" * 14


def test_bar_clamps():
    assert viz.bar(-1) == "░" * 10
    assert viz.bar(5) == "█" * 10


def test_sparkline_trend():
    assert viz.sparkline([]) == ""
    assert viz.sparkline([5, 5, 5]) == "▄▄▄"          # flat -> mid level, length preserved
    s = viz.sparkline([1, 2, 3, 4, 5, 6, 7, 8])
    assert s[0] == "▁" and s[-1] == "█" and len(s) == 8
    assert viz.sparkline([3, None, 9]) and "None" not in viz.sparkline([3, None, 9])


def test_stacked_wdl_sums_to_width_and_labels():
    out = viz.stacked_wdl(6, 2, 2, width=10)
    bar = out.split(" ")[0]
    assert len(bar) == 10
    assert "W60%" in out and "D20%" in out and "L20%" in out


def test_stacked_wdl_zero_games():
    assert "no games" in viz.stacked_wdl(0, 0, 0)


def test_score_glyph_bands():
    assert viz.score_glyph(0.60) == "🟩"
    assert viz.score_glyph(0.50) == "🟨"
    assert viz.score_glyph(0.46) == "🟧"
    assert viz.score_glyph(0.40) == "🟥"


def test_rank_glyph_worst_first():
    assert viz.rank_glyph(0, 3) == "🟥"     # worst
    assert viz.rank_glyph(2, 3) == "🟩"     # best
    assert viz.rank_glyph(0, 1) == "🟥"     # singleton


def test_share_glyph_higher_is_worse():
    assert viz.share_glyph(0.50) == "🟥"
    assert viz.share_glyph(0.30) == "🟧"
    assert viz.share_glyph(0.15) == "🟨"
    assert viz.share_glyph(0.05) == "🟩"


def test_details_collapsible():
    d = viz.details("Title", "body text")
    assert "<details>" in d and "<summary>Title</summary>" in d and "body text" in d
    assert viz.details("T", "b", open=True).startswith("<details open>")
