import datetime
import json
from pathlib import Path

import pytest

from gm import config, sync

FIX = Path(__file__).parent / "fixtures" / "month_sample.json"


def _months():
    return [json.loads(FIX.read_text())["games"]]


# --- hermetic: incremental helpers -------------------------------------------

def test_ym_from_end_time():
    ts = int(datetime.datetime(2025, 6, 15, tzinfo=datetime.timezone.utc).timestamp())
    assert sync._ym(ts) == (2025, 6)


def test_archive_ym_handles_trailing_slash():
    base = "https://api.chess.com/pub/player/x/games/2024/07"
    assert sync._archive_ym(base) == (2024, 7)
    assert sync._archive_ym(base + "/") == (2024, 7)


def test_iter_months_skips_archives_before_watermark(monkeypatch):
    archives = [f"https://api.chess.com/pub/player/x/games/{y}/{m:02d}"
                for (y, m) in [(2024, 5), (2024, 6), (2024, 7)]]
    calls = []
    monkeypatch.setattr(sync.chesscom, "get_archives", lambda u, client=None: archives)

    def fake_month(url, client=None):
        calls.append(sync._archive_ym(url))
        return [{"m": url}]

    monkeypatch.setattr(sync.chesscom, "get_month", fake_month)
    list(sync._iter_months("x", None, since_ym=(2024, 6)))
    assert calls == [(2024, 6), (2024, 7)]          # 2024-05 fetched-skipped


def test_read_watermark(conn):
    assert sync._read_watermark(conn, "eric", "bullet") == 0
    conn.execute("INSERT INTO sync_state(username,time_class,last_end_time) "
                 "VALUES('eric','bullet',123)")
    conn.commit()
    assert sync._read_watermark(conn, "eric", "bullet") == 123


# --- real engine: parallel path == serial result -----------------------------

pytestmark_engine = pytest.mark.skipif(config.stockfish_path() is None,
                                       reason="stockfish not installed")


@pytestmark_engine
def test_sync_parallel_matches_serial(conn):
    res = sync.sync_parallel(conn, "eric", "bullet", depth=8, workers=3,
                             months=_months())
    assert res["analyzed"] == 2 and res["failed"] == 0
    assert conn.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 2
    # every analyzed game got its moves rows
    assert conn.execute("SELECT COUNT(*) FROM moves").fetchone()[0] > 0
    # idempotent re-run skips both
    res2 = sync.sync_parallel(conn, "eric", "bullet", depth=8, workers=3,
                              months=_months())
    assert res2["analyzed"] == 0 and res2["skipped"] == 2


@pytestmark_engine
def test_sync_parallel_isolates_poison_game(conn, monkeypatch):
    real = sync.pipeline.analyze_game

    def flaky(pgn, color, analyzer):
        if "c5" in pgn:
            raise RuntimeError("boom")
        return real(pgn, color, analyzer)

    monkeypatch.setattr(sync.pipeline, "analyze_game", flaky)
    res = sync.sync_parallel(conn, "eric", "bullet", depth=8, workers=3,
                             months=_months())
    assert res["analyzed"] == 1 and res["failed"] == 1
    assert conn.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 1
