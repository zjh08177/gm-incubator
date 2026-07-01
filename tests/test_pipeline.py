import chess

from gm.analysis import pipeline


class FakeAnalyzer:
    """Returns a fixed eval per FEN so the pipeline is deterministic."""

    def __init__(self, table):
        self.table = table

    def analyse(self, board):
        return self.table.get(board.fen(), (0, list(board.legal_moves)[0].uci()))


def test_pipeline_marks_my_moves_and_computes_delta():
    pgn = '[TimeControl "60"]\n\n1. e4 {[%clk 0:01:00]} e5 {[%clk 0:00:59]} 2. Nf3 *\n'
    rows = pipeline.analyze_game(pgn, color="white", analyzer=FakeAnalyzer({}))
    assert rows[0]["is_mine"] == 1        # 1.e4 is White = mine
    assert rows[1]["is_mine"] == 0        # 1...e5 is Black
    assert all(r["winprob_delta"] >= 0 for r in rows)
    assert all(r["phase"] == "opening" for r in rows)
    assert rows[0]["clock_bucket"] == "had_time"


def test_last_move_is_scored_not_forced_zero():
    # Game stops right after White's 1.e4 (as on an opponent timeout). The
    # terminal position is analysed so the last (mine) move gets a real eval.
    pgn = '[TimeControl "60"]\n\n1. e4 *\n'
    start = chess.Board().fen()
    after = chess.Board()
    after.push_san("e4")
    table = {start: (0, "e2e4"), after.fen(): (500, "a7a6")}  # +500 for Black after e4
    rows = pipeline.analyze_game(pgn, "white", FakeAnalyzer(table))
    assert len(rows) == 1
    assert rows[0]["is_mine"] == 1
    assert rows[0]["winprob_delta"] > 0.2      # would be 0.0 before the fix
    assert rows[0]["severity"] == "blunder"
