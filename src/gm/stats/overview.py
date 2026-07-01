def summary(conn) -> dict:
    games = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    tc = {r["time_class"]: r["n"] for r in conn.execute(
        "SELECT time_class, COUNT(*) n FROM games GROUP BY time_class")}
    latest = conn.execute(
        "SELECT my_rating FROM games ORDER BY end_time DESC LIMIT 1").fetchone()
    phase_loss = {r["phase"]: round(r["avg"], 3) for r in conn.execute(
        """SELECT phase, AVG(winprob_delta) avg FROM moves
           WHERE is_mine=1 GROUP BY phase""")}
    clock = {r["clock_bucket"]: r["n"] for r in conn.execute(
        """SELECT clock_bucket, COUNT(*) n FROM moves
           WHERE is_mine=1 AND severity IS NOT NULL GROUP BY clock_bucket""")}
    return {"games": games, "by_time_class": tc,
            "rating_latest": latest[0] if latest else None,
            "phase_loss": phase_loss, "clock_split": clock}
