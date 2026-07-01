def search_games(conn, result=None, opening=None, color=None, time_class=None,
                 limit=50) -> list[dict]:
    where, args = [], []
    if result:
        where.append("result=?")
        args.append(result)
    if color:
        where.append("color=?")
        args.append(color)
    if opening:
        where.append("opening_name LIKE ?")
        args.append(f"%{opening}%")
    if time_class:
        where.append("time_class=?")
        args.append(time_class)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(
        f"SELECT * FROM games {clause} ORDER BY end_time DESC LIMIT ?", (*args, limit))
    return [dict(r) for r in rows]


def find_positions(conn, error_type=None, phase=None, min_delta=0.0,
                   had_time=False, time_class=None, limit=50) -> list[dict]:
    where = ["is_mine=1", "severity IS NOT NULL", "winprob_delta>=?"]
    args = [min_delta]
    if error_type:
        where.append("error_type=?")
        args.append(error_type)
    if phase:
        where.append("phase=?")
        args.append(phase)
    if had_time:
        where.append("clock_bucket='had_time'")
    if time_class:
        where.append("game_uuid IN (SELECT uuid FROM games WHERE time_class=?)")
        args.append(time_class)
    rows = conn.execute(
        f"""SELECT game_uuid,ply,san,fen_before,error_type,severity,winprob_delta,phase
            FROM moves WHERE {' AND '.join(where)}
            ORDER BY winprob_delta DESC LIMIT ?""", (*args, limit))
    return [dict(r) for r in rows]


def one_game(conn, uuid) -> dict:
    g = conn.execute("SELECT * FROM games WHERE uuid=?", (uuid,)).fetchone()
    if g is None:
        return {}
    moves = conn.execute(
        "SELECT * FROM moves WHERE game_uuid=? ORDER BY ply", (uuid,)).fetchall()
    d = dict(g)
    d["moves"] = [dict(m) for m in moves]
    return d
