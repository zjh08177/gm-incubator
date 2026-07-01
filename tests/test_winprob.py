from gm.analysis import winprob as w


def test_zero_is_half():
    assert abs(w.cp_to_winprob(0) - 0.5) < 1e-9


def test_monotonic_and_bounded():
    assert w.cp_to_winprob(300) > w.cp_to_winprob(100) > 0.5
    assert 0.0 < w.cp_to_winprob(-2000) < 0.5 < w.cp_to_winprob(2000) < 1.0


def test_loss_is_nonnegative_and_directional():
    assert w.loss(300, 300) == 0.0          # played the best move
    assert w.loss(300, -300) > 0.4          # threw away a winning position
    assert w.loss(-100, -120) >= 0.0        # never negative


def test_severity_thresholds():
    assert w.severity(0.03) is None
    assert w.severity(0.06) == "inaccuracy"
    assert w.severity(0.12) == "mistake"
    assert w.severity(0.30) == "blunder"
