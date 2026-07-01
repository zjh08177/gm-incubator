import pytest

from gm import config
from gm.analysis import pipeline
from gm.analysis.engine import Analyzer

pytestmark = pytest.mark.skipif(config.stockfish_path() is None,
                                reason="stockfish not installed")


def test_hung_queen_flagged_end_to_end():
    # 3.Qxe5?? grabs a pawn defended by the c6-knight; ...Nxe5 wins the queen.
    pgn = '[TimeControl "60"]\n\n1. e4 e5 2. Qh5 Nc6 3. Qxe5 Nxe5 *\n'
    with Analyzer(depth=12) as a:
        rows = pipeline.analyze_game(pgn, "white", a, depth=12)
    q = next(r for r in rows if r["ply"] == 5)   # 3.Qxe5 by White
    assert q["is_mine"] == 1
    assert q["severity"] == "blunder"
    assert q["error_type"] == "dropped_material"


def test_clean_opening_not_overflagged():
    # A quiet, sound mini-game: White should have no blunders.
    pgn = '[TimeControl "60"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *\n'
    with Analyzer(depth=12) as a:
        rows = pipeline.analyze_game(pgn, "white", a, depth=12)
    mine_blunders = [r for r in rows if r["is_mine"] and r["severity"] == "blunder"]
    assert mine_blunders == []
