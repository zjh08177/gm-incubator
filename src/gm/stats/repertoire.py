from gm.stats import tc_filter


def _family(name: str) -> str:
    """Roll a full opening name up to its first two words (the recognizable family)."""
    return " ".join(name.split()[:2]) if name else name


def by_color(conn, color: str, group: str = "opening",
             time_class: str | None = None) -> list[dict]:
    tc, tca = tc_filter(time_class)
    games = conn.execute(
        f"SELECT uuid, eco, opening_name, result FROM games WHERE color=?{tc}",
        (color, *tca)).fetchall()
    buckets: dict[str, dict] = {}
    for g in games:
        name = g["opening_name"] or g["eco"] or "Unknown"
        key = _family(name) if group == "family" else name
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
