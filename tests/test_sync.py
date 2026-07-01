import json
from pathlib import Path

from gm import sync

FIX = Path(__file__).parent / "fixtures" / "month_sample.json"


class FakeAnalyzer:
    def analyse(self, board):
        return (0, list(board.legal_moves)[0].uci())


def _months():
    return [json.loads(FIX.read_text())["games"]]


def test_first_sync_inserts_then_reruns_skip(conn):
    r1 = sync.sync(conn, "eric", "bullet", FakeAnalyzer(), months=_months())
    assert r1["analyzed"] == 2
    n = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    assert n == 2
    r2 = sync.sync(conn, "eric", "bullet", FakeAnalyzer(), months=_months())
    assert r2["analyzed"] == 0 and r2["skipped"] == 2   # idempotent


def test_time_class_filter(conn):
    months = _months()
    months[0][0]["time_class"] = "rapid"   # exclude one
    r = sync.sync(conn, "eric", "bullet", FakeAnalyzer(), months=months)
    assert r["analyzed"] == 1


def test_full_reanalyzes_existing(conn):
    sync.sync(conn, "eric", "bullet", FakeAnalyzer(), months=_months())
    r = sync.sync(conn, "eric", "bullet", FakeAnalyzer(), months=_months(), full=True)
    assert r["analyzed"] == 2 and r["skipped"] == 0
    n = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    assert n == 2   # no duplicates
