def by_color(conn, color: str) -> list[dict]:
    games = conn.execute(
        "SELECT uuid, eco, opening_name, result FROM games WHERE color=?", (color,)).fetchall()
    buckets: dict[str, dict] = {}
    for g in games:
        key = g["opening_name"] or g["eco"] or "Unknown"
        b = buckets.setdefault(key, {"opening": key, "eco": g["eco"],
                                     "games": 0, "wdl": [0, 0, 0], "uuids": []})
        b["games"] += 1
        b["wdl"][{"win": 0, "draw": 1, "loss": 2}[g["result"]]] += 1
        b["uuids"].append(g["uuid"])
    out = []
    for b in buckets.values():
        w, d, l = b["wdl"]
        b["score"] = round((w + 0.5 * d) / max(1, b["games"]), 3)
        marks = ",".join("?" * len(b["uuids"]))
        row = conn.execute(f"""SELECT MIN(ply) AS p FROM moves
            WHERE is_mine=1 AND severity IS NOT NULL AND phase='opening'
              AND game_uuid IN ({marks})""", b["uuids"]).fetchone()
        b["break_ply"] = row["p"]
        del b["uuids"]
        out.append(b)
    return sorted(out, key=lambda r: r["games"], reverse=True)
