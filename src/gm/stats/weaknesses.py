def rank(conn, had_time_only: bool = False) -> list[dict]:
    clause = "AND clock_bucket='had_time'" if had_time_only else ""
    q = f"""
      SELECT COALESCE(error_type,'other') AS category,
             COUNT(*) AS count, SUM(winprob_delta) AS lost
      FROM moves
      WHERE is_mine=1 AND severity IS NOT NULL {clause}
      GROUP BY category ORDER BY lost DESC"""
    out = []
    for row in conn.execute(q):
        ex = conn.execute(f"""
          SELECT game_uuid, ply, san FROM moves
          WHERE is_mine=1 AND severity IS NOT NULL {clause}
            AND COALESCE(error_type,'other')=?
          ORDER BY winprob_delta DESC LIMIT 1""", (row["category"],)).fetchone()
        out.append({
            "category": row["category"], "count": row["count"],
            "winprob_lost": round(row["lost"], 3),
            "example": dict(ex) if ex else None,
        })
    return out
