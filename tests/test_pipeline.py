from gm.analysis import pipeline


class FakeAnalyzer:
    """Returns a fixed eval per FEN so the pipeline is deterministic."""

    def __init__(self, table):
        self.table = table

    def analyse(self, board):
        return self.table.get(board.fen(), (0, list(board.legal_moves)[0].uci()))


def test_pipeline_marks_my_moves_and_computes_delta():
    pgn = '[TimeControl "60"]\n\n1. e4 {[%clk 0:01:00]} e5 {[%clk 0:00:59]} 2. Nf3 *\n'
    rows = pipeline.analyze_game(pgn, color="white", analyzer=FakeAnalyzer({}), depth=1)
    assert rows[0]["is_mine"] == 1        # 1.e4 is White = mine
    assert rows[1]["is_mine"] == 0        # 1...e5 is Black
    assert all(r["winprob_delta"] >= 0 for r in rows)
    assert all(r["phase"] == "opening" for r in rows)
    assert rows[0]["clock_bucket"] == "had_time"
