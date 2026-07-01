import chess

from gm.analysis import classify
from gm.analysis import winprob as w


def _sev(best, played):
    return w.severity(w.loss(best, played))


def test_no_error_no_category():
    # played == best, no severity -> None
    b = chess.Board()
    assert classify.classify(b, "e2e4", "e2e4", 20, 20, _sev(20, 20), "opening") is None


def test_dropped_material_when_move_hangs_piece():
    # White plays Bc4?? into a square the black d5-pawn attacks; ...dxc4 wins the bishop.
    b = chess.Board("4k3/8/8/3p4/8/8/8/4KB2 w - - 0 1")
    cat = classify.classify(b, played_uci="f1c4", best_uci="e1e2", eval_best_cp=0,
                            eval_played_cp=-300, severity="blunder", phase="middlegame")
    assert cat == "dropped_material"


def test_endgame_conversion_when_winning_endgame_slips():
    b = chess.Board("8/8/8/4k3/8/8/4P3/4K3 w - - 0 60")  # winning K+P endgame
    cat = classify.classify(b, "e2e4", "e1d1", eval_best_cp=300,
                            eval_played_cp=0, severity="blunder", phase="endgame")
    assert cat == "endgame_conversion"


def test_missed_tactic_when_best_was_winning_capture():
    # Best move is a big winning capture; played a quiet move instead.
    b = chess.Board("3qk3/8/8/8/8/8/8/3QK3 w - - 0 1")
    cat = classify.classify(b, "e1f1", "d1d8", eval_best_cp=900,
                            eval_played_cp=0, severity="blunder", phase="middlegame")
    assert cat == "missed_tactic"


def test_allowed_tactic_is_fallback_for_tactical_drop():
    b = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    cat = classify.classify(b, "e2e4", "d2d4", eval_best_cp=30,
                            eval_played_cp=-250, severity="mistake", phase="middlegame")
    assert cat == "allowed_tactic"
