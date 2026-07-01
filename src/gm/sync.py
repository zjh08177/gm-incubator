import time

from gm import chesscom
from gm.analysis import pipeline


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


def _iter_months(username, months):
    if months is not None:
        yield from months
        return
    for url in chesscom.get_archives(username):
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
    conn.execute("""INSERT INTO sync_state(username,time_class,last_end_time)
        VALUES(?,?,?) ON CONFLICT(username,time_class)
        DO UPDATE SET last_end_time=MAX(last_end_time, excluded.last_end_time)""",
                 (username, time_class, max_end))
    conn.commit()
    return {"fetched": fetched, "analyzed": analyzed, "skipped": skipped,
            "failed": failed, "failures": failures}
