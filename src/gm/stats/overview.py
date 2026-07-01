from gm.stats import tc_filter


def summary(conn, time_class: str | None = None) -> dict:
    gf, gfa = tc_filter(time_class)                 # games-table filter
    mf, mfa = tc_filter(time_class, moves=True)     # moves-table filter
    games = conn.execute(f"SELECT COUNT(*) FROM games WHERE 1=1{gf}", gfa).fetchone()[0]
    tc = {r["time_class"]: r["n"] for r in conn.execute(
        f"SELECT time_class, COUNT(*) n FROM games WHERE 1=1{gf} GROUP BY time_class", gfa)}
    latest = conn.execute(
        f"SELECT my_rating FROM games WHERE 1=1{gf} ORDER BY end_time DESC LIMIT 1", gfa).fetchone()
    phase_loss = {r["phase"]: round(r["avg"], 3) for r in conn.execute(
        f"""SELECT phase, AVG(winprob_delta) avg FROM moves
           WHERE is_mine=1{mf} GROUP BY phase""", mfa)}
    clock = {r["clock_bucket"]: r["n"] for r in conn.execute(
        f"""SELECT clock_bucket, COUNT(*) n FROM moves
           WHERE is_mine=1 AND severity IS NOT NULL{mf} GROUP BY clock_bucket""", mfa)}
    return {"games": games, "by_time_class": tc,
            "rating_latest": latest[0] if latest else None,
            "phase_loss": phase_loss, "clock_split": clock}
