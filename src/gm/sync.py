import datetime
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from gm import chesscom, config
from gm.analysis import pipeline
from gm.analysis.engine import Analyzer


def _existing(conn, uuid) -> bool:
    return conn.execute("SELECT 1 FROM games WHERE uuid=?", (uuid,)).fetchone() is not None


def _insert(conn, g, rows):
    conn.execute("""INSERT INTO games
        (uuid,url,end_time,time_class,time_control,color,result,my_rating,opp_rating,
         eco,opening_name,accuracy_self,pgn,analyzed_at)
        VALUES (:uuid,:url,:end_time,:time_class,:time_control,:color,:result,:my_rating,
         :opp_rating,:eco,:opening_name,:accuracy_self,:pgn,:analyzed_at)""",
                 {**g, "analyzed_at": int(time.time())})
    conn.executemany("""INSERT INTO moves
        (game_uuid,ply,san,fen_before,eval_best_cp,best_move,eval_played_cp,winprob_delta,
         clock_ms,phase,clock_bucket,error_type,severity,is_mine)
        VALUES (:game_uuid,:ply,:san,:fen_before,:eval_best_cp,:best_move,:eval_played_cp,
         :winprob_delta,:clock_ms,:phase,:clock_bucket,:error_type,:severity,:is_mine)""",
                     [{**r, "game_uuid": g["uuid"]} for r in rows])


def _ym(end_time) -> tuple[int, int]:
    d = datetime.datetime.fromtimestamp(end_time, datetime.timezone.utc)
    return (d.year, d.month)


def _archive_ym(url: str) -> tuple[int, int]:
    p = url.rstrip("/").split("/")
    return (int(p[-2]), int(p[-1]))


def _read_watermark(conn, username, time_class) -> int:
    row = conn.execute("SELECT last_end_time FROM sync_state WHERE username=? AND time_class=?",
                       (username, time_class)).fetchone()
    return row[0] if row and row[0] is not None else 0


def _iter_months(username, months, since_ym=None):
    if months is not None:
        yield from months
        return
    for url in chesscom.get_archives(username):
        if since_ym is not None and _archive_ym(url) < since_ym:
            continue                           # month fully covered by a prior complete run
        yield chesscom.get_month(url)


def _analyze_one(conn, raw, username, analyzer, full):
    g = chesscom.normalize(raw, username)
    rows = pipeline.analyze_game(g["pgn"], g["color"], analyzer)
    if full:
        conn.execute("DELETE FROM moves WHERE game_uuid=?", (raw["uuid"],))
        conn.execute("DELETE FROM games WHERE uuid=?", (raw["uuid"],))
    _insert(conn, g, rows)
    conn.commit()                          # per-game commit = kill-safe


def sync(conn, username, time_class, analyzer,
         max_games=None, full=False, months=None) -> dict:
    """Idempotent by game UUID. full=True re-analyzes existing games.
    Standard chess only; a game that fails to analyze is counted and skipped,
    never aborting the run."""
    fetched = analyzed = skipped = failed = 0
    failures = []
    max_end = 0
    for raw_games in _iter_months(username, months):
        for raw in raw_games:
            if raw.get("time_class") != time_class or raw.get("rules", "chess") != "chess":
                continue
            fetched += 1
            max_end = max(max_end, raw.get("end_time", 0))
            if _existing(conn, raw["uuid"]) and not full:
                skipped += 1
                continue
            try:
                _analyze_one(conn, raw, username, analyzer, full)
                analyzed += 1
            except Exception as exc:           # isolate one poison game
                conn.rollback()
                failed += 1
                failures.append({"uuid": raw.get("uuid"), "error": str(exc)})
                continue
            if max_games and analyzed >= max_games:
                break
        if max_games and analyzed >= max_games:
            break
    _bump_watermark(conn, username, time_class, max_end)
    return {"fetched": fetched, "analyzed": analyzed, "skipped": skipped,
            "failed": failed, "failures": failures}


def backfill_openings(conn) -> dict:
    """Populate games.opening_name from each stored PGN's ECOUrl (human name,
    move-sequence-derived). Engine-free, idempotent, safe to re-run."""
    rows = conn.execute("SELECT uuid, pgn FROM games").fetchall()
    updated = 0
    for r in rows:
        name = chesscom._opening_from_pgn(r["pgn"])
        if name:
            conn.execute("UPDATE games SET opening_name=? WHERE uuid=?", (name, r["uuid"]))
            updated += 1
    conn.commit()
    return {"updated": updated, "total": len(rows)}


def _bump_watermark(conn, username, time_class, max_end) -> None:
    conn.execute("""INSERT INTO sync_state(username,time_class,last_end_time)
        VALUES(?,?,?) ON CONFLICT(username,time_class)
        DO UPDATE SET last_end_time=MAX(last_end_time, excluded.last_end_time)""",
                 (username, time_class, max_end))
    conn.commit()


# --- parallel path -----------------------------------------------------------
# python-chess's SimpleEngine.analyse() blocks on subprocess I/O (GIL released)
# while Stockfish computes in its own OS process, so N threads → N concurrent
# engines. Each thread owns a thread-local Analyzer; DB writes stay in the main
# thread (sqlite single-writer). Serial sync() above is untouched.

_tls = threading.local()


def _thread_analyzer(depth, path, pool):
    a = getattr(_tls, "analyzer", None)
    if a is None:
        a = Analyzer(depth=depth, path=path)
        a.__enter__()
        pool.append(a)                         # tracked for shutdown (see finally)
        _tls.analyzer = a
    return a


def sync_parallel(conn, username, time_class, depth=12, workers=8,
                  max_games=None, full=False, months=None, progress=None,
                  since_ym=None) -> dict:
    """Parallel analog of sync(): fans per-game engine analysis across `workers`
    threads, writes serially. `since_ym`=(year,month) floors the backfill window.
    Month-incremental: on a re-run after a prior complete pass, whole months
    below the stored watermark are also skipped (composes with since_ym)."""
    path = config.stockfish_path()
    if not path:
        raise RuntimeError("Stockfish not found; set STOCKFISH_PATH")
    watermark = 0 if (full or months is not None) else _read_watermark(conn, username, time_class)
    floor = since_ym
    if watermark:
        wm_ym = _ym(watermark)
        floor = max(floor, wm_ym) if floor else wm_ym

    fetched = skipped = 0
    max_end = 0
    tasks = []                                 # (g_meta, pgn, color)
    for raw_games in _iter_months(username, months, floor):
        for raw in raw_games:
            if raw.get("time_class") != time_class or raw.get("rules", "chess") != "chess":
                continue
            fetched += 1
            max_end = max(max_end, raw.get("end_time", 0))
            if _existing(conn, raw["uuid"]) and not full:
                skipped += 1
                continue
            g = chesscom.normalize(raw, username)
            tasks.append((g, g["pgn"], g["color"]))
            if max_games and len(tasks) >= max_games:
                break
        if max_games and len(tasks) >= max_games:
            break

    analyzed = failed = 0
    failures = []
    total = len(tasks)
    engines = []

    def _work(item):
        g, pgn, color = item
        a = _thread_analyzer(depth, path, engines)
        try:
            return g, pipeline.analyze_game(pgn, color, a), None
        except Exception as exc:               # isolate one poison game
            return g, None, str(exc)

    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for fut in as_completed([ex.submit(_work, t) for t in tasks]):
                g, rows, err = fut.result()
                if err is not None:
                    failed += 1
                    failures.append({"uuid": g["uuid"], "error": err})
                    continue
                if full:
                    conn.execute("DELETE FROM moves WHERE game_uuid=?", (g["uuid"],))
                    conn.execute("DELETE FROM games WHERE uuid=?", (g["uuid"],))
                _insert(conn, g, rows)
                conn.commit()                  # per-game commit = kill-safe
                analyzed += 1
                if progress and analyzed % progress == 0:
                    print(f"[sync] {analyzed}/{total} analyzed, {failed} failed "
                          f"({skipped} pre-existing)", flush=True)
    finally:
        for a in engines:
            try:
                a.__exit__()
            except Exception:
                pass

    _bump_watermark(conn, username, time_class, max_end)
    return {"fetched": fetched, "analyzed": analyzed, "skipped": skipped,
            "failed": failed, "failures": failures, "candidates": total}
