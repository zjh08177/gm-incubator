from gm.stats import tc_filter


def rank(conn, had_time_only: bool = False, time_class: str | None = None) -> list[dict]:
    clause = "AND clock_bucket='had_time'" if had_time_only else ""
    tc, tca = tc_filter(time_class, moves=True)
    q = f"""
      SELECT COALESCE(error_type,'other') AS category,
             COUNT(*) AS count, SUM(winprob_delta) AS lost
      FROM moves
      WHERE is_mine=1 AND severity IS NOT NULL {clause}{tc}
      GROUP BY category ORDER BY lost DESC"""
    out = []
    for row in conn.execute(q, tca):
        ex = conn.execute(f"""
          SELECT game_uuid, ply, san FROM moves
          WHERE is_mine=1 AND severity IS NOT NULL {clause}{tc}
            AND COALESCE(error_type,'other')=?
          ORDER BY winprob_delta DESC LIMIT 1""", (*tca, row["category"])).fetchone()
        out.append({
            "category": row["category"], "count": row["count"],
            "winprob_lost": round(row["lost"], 3),
            "example": dict(ex) if ex else None,
        })
    return out
