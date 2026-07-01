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


def test_endgame_conversion_only_for_quiet_positional_slip():
    # K+P: Kf4 keeps the pawn defended (no hang) but throws the win. Genuine conversion slip.
    b = chess.Board("8/8/4k3/4P3/4K3/8/8/8 w - - 0 60")
    cat = classify.classify(b, "e4f4", "e4d5", eval_best_cp=300,
                            eval_played_cp=0, severity="blunder", phase="endgame")
    assert cat == "endgame_conversion"


def test_endgame_hang_is_dropped_not_conversion():
    # Winning endgame, but the move hangs a piece -> dropped_material, NOT conversion.
    b = chess.Board("4k3/8/8/3p4/8/8/8/4KB2 w - - 0 60")
    cat = classify.classify(b, "f1c4", "e1e2", eval_best_cp=300,
                            eval_played_cp=100, severity="mistake", phase="endgame")
    assert cat == "dropped_material"


def test_endgame_walk_into_mate_is_not_conversion():
    # Was winning, then walked into forced mate -> allowed_tactic, NOT conversion.
    b = chess.Board("8/8/4k3/4P3/4K3/8/8/8 w - - 0 60")
    cat = classify.classify(b, "e4f4", "e4d5", eval_best_cp=250,
                            eval_played_cp=-99997, severity="blunder", phase="endgame")
    assert cat == "allowed_tactic"


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
