"""Static-markdown visual encodings for the profile report.

Pure string helpers — magnitude bars, trend sparklines, severity glyphs,
collapsibles — with no I/O. Rationale in `research-report-design.md`
(§ static-markdown visual toolkit).
"""

GREEN, YELLOW, ORANGE, RED = "🟩", "🟨", "🟧", "🟥"
_SPARK = "▁▂▃▄▅▆▇█"
_MID = _SPARK[(len(_SPARK) - 1) // 2]


def bar(frac: float, width: int = 10, fill: str = "█", empty: str = "░") -> str:
    """Block-char magnitude bar; `frac` clamped to [0, 1]."""
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else frac
    n = round(frac * width)
    return fill * n + empty * (width - n)


def sparkline(values) -> str:
    """Word-sized trend over 8 levels (min..max); None values are skipped."""
    vals = [v for v in values if v is not None]
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return _MID * len(vals)
    span, top = hi - lo, len(_SPARK) - 1
    return "".join(_SPARK[int((v - lo) / span * top + 0.5)] for v in vals)


def stacked_wdl(w: int, d: int, l: int, width: int = 10) -> str:
    """Proportion bar (win ▓ · draw ▒ · loss ░) plus W/D/L percentages."""
    g = w + d + l
    if g == 0:
        return "░" * width + " (no games)"
    wn, dn = round(w / g * width), round(d / g * width)
    ln = max(0, width - wn - dn)
    return (f"{'▓' * wn}{'▒' * dn}{'░' * ln} "
            f"W{round(w / g * 100)}% D{round(d / g * 100)}% L{round(l / g * 100)}%")


def score_glyph(score: float) -> str:
    """Win-rate style ramp — higher is better."""
    if score >= 0.52:
        return GREEN
    if score >= 0.48:
        return YELLOW
    if score >= 0.44:
        return ORANGE
    return RED


def rank_glyph(index: int, total: int) -> str:
    """Worst-first ranking → red at the top, green at the tail."""
    if total <= 1:
        return RED
    frac = index / (total - 1)
    if frac <= 0.25:
        return RED
    if frac <= 0.5:
        return ORANGE
    if frac <= 0.75:
        return YELLOW
    return GREEN


def share_glyph(share: float) -> str:
    """Fraction of a total where higher is worse."""
    if share >= 0.40:
        return RED
    if share >= 0.20:
        return ORANGE
    if share >= 0.10:
        return YELLOW
    return GREEN


def details(summary: str, body: str, open: bool = False) -> str:
    """Collapsible block (renders in Obsidian and GitHub)."""
    tag = "<details open>" if open else "<details>"
    return f"{tag}<summary>{summary}</summary>\n\n{body}\n\n</details>"
