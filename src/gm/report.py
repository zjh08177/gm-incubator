def _wk_table(rows):
    out = ["| Category | Count | Win% lost | Worst example |",
           "|---|---|---|---|"]
    for r in rows:
        ex = r["example"]
        cell = f'{ex["game_uuid"]} ply {ex["ply"]} ({ex["san"]})' if ex else "-"
        out.append(f'| {r["category"]} | {r["count"]} | {r["winprob_lost"]:.2f} | {cell} |')
    return "\n".join(out)


def weaknesses_md(ranked, had_time_ranked) -> str:
    return (
        "# Weakness Report\n\n"
        "## All errors (ranked by win% lost)\n\n" + _wk_table(ranked) +
        "\n\n## Had-time errors only (real knowledge gaps)\n\n" +
        _wk_table(had_time_ranked) + "\n")


def _rep_section(title, rows):
    out = [f"## {title}", "", "| Opening | Games | Score | W-D-L | Leaves book (ply) |",
           "|---|---|---|---|---|"]
    for r in rows:
        w, d, l = r["wdl"]
        bp = r["break_ply"] if r["break_ply"] is not None else "-"
        out.append(f'| {r["opening"]} | {r["games"]} | {r["score"]:.2f} | {w}-{d}-{l} | {bp} |')
    return "\n".join(out)


def repertoire_md(white, black) -> str:
    return ("# Opening Repertoire\n\n" + _rep_section("As White", white) +
            "\n\n" + _rep_section("As Black", black) + "\n")
