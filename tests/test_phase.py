import chess

from gm.analysis import phase


def test_opening_early_full_board():
    assert phase.game_phase(chess.Board(), ply=2) == "opening"


def test_middlegame_full_board_later():
    assert phase.game_phase(chess.Board(), ply=30) == "middlegame"


def test_endgame_few_pieces():
    b = chess.Board("8/5k2/8/8/8/3K4/6R1/8 w - - 0 40")  # K+R vs K
    assert phase.game_phase(b, ply=80) == "endgame"
