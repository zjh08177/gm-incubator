from gm import viz


def _wk_table(rows):
    total = sum(r["winprob_lost"] for r in rows) or 1
    mx = max((r["winprob_lost"] for r in rows), default=1) or 1
    out = ["| | Category | Win% lost | | Count | Worst example |",
           "|---|---|--:|---|--:|---|"]
    for i, r in enumerate(rows):
        ex = r["example"]
        cell = (f'`{ex["game_uuid"]}` ply {ex["ply"]} `{ex["san"]}`') if ex else "-"
        g = viz.share_glyph(r["winprob_lost"] / total)
        b = viz.bar(r["winprob_lost"] / mx)
        name = f'**{r["category"]}**' if i == 0 else r["category"]
        out.append(f'| {g} | {name} | {round(r["winprob_lost"]):,} | {b} '
                   f'| {r["count"]:,} | {cell} |')
    return "\n".join(out)


def weaknesses_md(ranked, had_time_ranked) -> str:
    return (
        "# Weakness Report\n\n"
        "## All errors (ranked by win% lost)\n\n" + _wk_table(ranked) +
        "\n\n## Had-time errors only (real knowledge gaps)\n\n" +
        _wk_table(had_time_ranked) + "\n")


def _rep_section(title, rows):
    out = [f"## {title}", "",
           "| | Opening | Games | Score | W-D-L |",
           "|---|---|--:|---|---|"]
    for r in rows:
        w, d, l = r["wdl"]
        eco = r.get("eco")
        name = f'{r["opening"]} · {eco}' if eco and eco != r["opening"] else r["opening"]
        out.append(f'| {viz.score_glyph(r["score"])} | {name} | {r["games"]:,} '
                   f'| {r["score"]:.2f} {viz.bar(r["score"])} | {viz.stacked_wdl(w, d, l)} |')
    return "\n".join(out)


def repertoire_md(white, black) -> str:
    return ("# Opening Repertoire\n\n" + _rep_section("As White", white) +
            "\n\n" + _rep_section("As Black", black) + "\n")
