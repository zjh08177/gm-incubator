import chess
import pytest

from gm import config
from gm.analysis.engine import Analyzer

pytestmark = pytest.mark.skipif(config.stockfish_path() is None,
                                reason="stockfish not installed")


def test_finds_winning_capture_sign():
    # White to move; Qxd5 grabs an UNDEFENDED black queen (king can't recapture).
    b = chess.Board("4k3/8/8/3q4/8/8/8/3QK3 w - - 0 1")
    with Analyzer(depth=10) as a:
        cp, best = a.analyse(b)
    assert cp > 300
    assert best.startswith("d1d5")


def test_start_position_near_equal():
    b = chess.Board()
    with Analyzer(depth=10) as a:
        cp, best = a.analyse(b)
    assert -100 < cp < 100  # start position is near equal
