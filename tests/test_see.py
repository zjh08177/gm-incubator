import chess

from gm.analysis import see


def test_free_capture_is_positive():
    # White rook takes undefended black pawn on a7.
    b = chess.Board("8/p7/8/8/8/8/8/R3K2k w - - 0 1")
    mv = chess.Move.from_uci("a1a7")
    assert see.see_capture(b, mv) > 0


def test_bad_capture_is_negative():
    # White queen takes a pawn on d5 that is defended by the c6 pawn -> loses the queen.
    b = chess.Board("4k3/8/2p5/3p4/8/3Q4/8/4K3 w - - 0 1")
    mv = chess.Move.from_uci("d3d5")
    assert see.see_capture(b, mv) < 0


def test_hanging_after_detects_free_piece():
    # Black to move can grab an undefended white knight on e4.
    b = chess.Board("4k3/8/8/8/4N3/8/8/4K2q b - - 0 1")
    assert see.hanging_after(b) is True
