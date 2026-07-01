"""Compose a complete player profile (markdown) from the KB."""
from gm import accept, report, viz
from gm.stats import overview, queries, repertoire, tc_filter, weaknesses

_IDX = {"win": 0, "draw": 1, "loss": 2}


def _wdl_score(wdl) -> float:
    g = sum(wdl)
    return (wdl[0] + 0.5 * wdl[1]) / g if g else 0.0


def _overall(conn, time_class=None) -> dict:
    gf, gfa = tc_filter(time_class)
    wdl = [0, 0, 0]
    for r in conn.execute(f"SELECT result, COUNT(*) n FROM games WHERE 1=1{gf} GROUP BY result", gfa):
        if r["result"] in _IDX:
            wdl[_IDX[r["result"]]] += r["n"]
    span = conn.execute(f"SELECT MIN(end_time) lo, MAX(end_time) hi FROM games WHERE 1=1{gf}", gfa).fetchone()
    rr = conn.execute(f"SELECT MIN(my_rating) lo, MAX(my_rating) hi FROM games "
                      f"WHERE my_rating IS NOT NULL{gf}", gfa).fetchone()
    latest = conn.execute(f"SELECT my_rating FROM games WHERE my_rating IS NOT NULL{gf} "
                          f"ORDER BY end_time DESC LIMIT 1", gfa).fetchone()
    return {"games": sum(wdl), "wdl": wdl, "score": _wdl_score(wdl),
            "span": (span["lo"], span["hi"]), "rating_lohi": (rr["lo"], rr["hi"]),
            "rating_latest": latest["my_rating"] if latest else None}


def _color_winrate(conn, time_class=None) -> dict:
    gf, gfa = tc_filter(time_class)
    out = {}
    for color in ("white", "black"):
        wdl = [0, 0, 0]
        for r in conn.execute(
                f"SELECT result, COUNT(*) n FROM games WHERE color=?{gf} GROUP BY result",
                (color, *gfa)):
            if r["result"] in _IDX:
                wdl[_IDX[r["result"]]] += r["n"]
        out[color] = {"games": sum(wdl), "wdl": wdl, "score": round(_wdl_score(wdl), 3)}
    return out


def _rating_by_month(conn, time_class=None) -> list[dict]:
    gf, gfa = tc_filter(time_class)
    rows = conn.execute(
        f"""SELECT strftime('%Y-%m', end_time, 'unixepoch') AS ym, my_rating AS r, end_time
           FROM games WHERE my_rating IS NOT NULL{gf} ORDER BY end_time""", gfa).fetchall()
    months: dict[str, dict] = {}
    for r in rows:
        b = months.setdefault(r["ym"], {"ym": r["ym"], "lo": r["r"], "hi": r["r"],
                                        "last": r["r"], "n": 0})
        b["lo"] = min(b["lo"], r["r"])
        b["hi"] = max(b["hi"], r["r"])
        b["last"] = r["r"]
        b["n"] += 1
    return list(months.values())


def _demote(md: str) -> str:
    """Push an embedded sub-report's headings down one level (# -> ##)."""
    return "\n".join("#" + ln if ln.startswith("#") else ln for ln in md.splitlines())


def _ts(t) -> str:
    if t is None:
        return "?"
    import datetime
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d")


def build(conn, time_class=None) -> str:
    o = _overall(conn, time_class)
    w, d, l = o["wdl"]
    lo_r, hi_r = o["rating_lohi"]
    traj = _rating_by_month(conn, time_class)
    tag = f" ({time_class})" if time_class else ""
    out = [
        f"# Chess Profile{tag}",
        "",
        f"**{o['games']:,} games** · {_ts(o['span'][0])} → {_ts(o['span'][1])} · "
        f"score **{o['score']:.2f}** (W-D-L {w:,}-{d:,}-{l:,})",
    ]
    if o["rating_latest"] is not None:
        series = [m["last"] for m in traj] or [o["rating_latest"]]
        delta = o["rating_latest"] - series[0]
        arrow = "▲" if delta > 0 else "▼" if delta < 0 else "→"
        out += ["",
                f"**{o['rating_latest']}** {viz.sparkline(series)} {arrow} {delta:+d} · "
                f"range {lo_r}–{hi_r}"]

    out += ["", "## Rating trend", ""]
    if traj:
        out.append(f"Month-end rating: `{viz.sparkline([m['last'] for m in traj])}` "
                   f"({traj[0]['ym']} → {traj[-1]['ym']})")
        tbl = ["| Month | Games | Low | High | Month-end |", "|---|--:|--:|--:|--:|"]
        tbl += [f"| {m['ym']} | {m['n']:,} | {m['lo']} | {m['hi']} | {m['last']} |" for m in traj]
        out += ["", viz.details("Full month-by-month table", "\n".join(tbl))]
    else:
        out.append("_(no rated games)_")

    ov = overview.summary(conn, time_class)
    out += ["", "## Where win% leaks (by phase)", ""]
    pl = ov["phase_loss"]
    if pl:
        items = sorted(pl.items(), key=lambda kv: kv[1], reverse=True)  # weakest first
        mx = max(v for _, v in items) or 1
        out += ["| | Phase | Win% lost/move | |", "|---|---|--:|---|"]
        out += [f"| {viz.rank_glyph(i, len(items))} | {ph} | {v * 100:.1f}% | {viz.bar(v / mx)} |"
                for i, (ph, v) in enumerate(items)]
    else:
        out.append("_(no analyzed moves)_")
    if ov["clock_split"]:
        out += ["", "Serious errors by clock: "
                + " · ".join(f"{k} {v:,}" for k, v in ov["clock_split"].items())]

    cw = _color_winrate(conn, time_class)
    out += ["", "## Results by color", "",
            "| | Color | Games | Score | W-D-L |", "|---|---|--:|---|---|"]
    for c in ("white", "black"):
        b = cw[c]
        ww, dd, ll = b["wdl"]
        out.append(f"| {viz.score_glyph(b['score'])} | {c.capitalize()} | {b['games']:,} "
                   f"| {b['score']:.2f} {viz.bar(b['score'])} | {viz.stacked_wdl(ww, dd, ll)} |")

    out += ["", _demote(report.repertoire_md(
        repertoire.by_color(conn, "white", time_class=time_class)[:12],
        repertoire.by_color(conn, "black", time_class=time_class)[:12]).rstrip())]
    out += ["", _demote(report.weaknesses_md(
        weaknesses.rank(conn, time_class=time_class),
        weaknesses.rank(conn, had_time_only=True, time_class=time_class)).rstrip())]

    top = queries.find_positions(conn, min_delta=0.0, time_class=time_class, limit=10)
    out += ["", "## Biggest single blunders", ""]
    if top:
        out += ["| Game | Ply | Move | Phase | Type | Win% lost |", "|---|--:|---|---|---|--:|"]
        out += [f"| `{p['game_uuid']}` | {p['ply']} | `{p['san']}` | {p['phase']} | "
                f"{p['error_type'] or 'other'} | {p['winprob_delta']:.2f} |" for p in top]
    else:
        out.append("_(none — no engine-analyzed moves yet)_")

    oracle = accept.correlate(conn, time_class)
    body = (f"Per-game win%-loss vs Chess.com accuracy: Spearman ρ={oracle['rho']} "
            f"(n={oracle['n']}, shuffled control {oracle['shuffled_rho']}, "
            f"gate {'PASS' if oracle['pass'] else 'n/a'}).")
    out += ["", "## Analysis validity", "", viz.details("Oracle detail", body)]
    return "\n".join(out) + "\n"
