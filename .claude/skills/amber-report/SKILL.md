---
name: amber-report
description: Render any structured report or analysis as a rich, self-contained HTML artifact in the AMBER LEDGER design system (ink-on-paper amber-monochrome dossier). Use when asked to "make this a report / HTML / dashboard / artifact", when presenting a data-heavy analysis, or — for this repo — whenever gm-coach produces a weaknesses / repertoire / stats / game report. Produces one CSP-safe HTML file, published via the Artifact tool.
---

# amber-report

Turn structured data + your judgment into a **single self-contained HTML report**
in the AMBER LEDGER visual system, then publish it as an Artifact. One file,
system fonts, inline CSS/JS — no CDN, no build, renders offline under the strict
Artifact CSP.

**The one rule that carries the whole look:** AMBER = *cost / attention / look here*.
OLIVE = *fine / neutral*. Spend saturated color in exactly one place — the thing
the reader must act on. A healthy stat is quiet; a leak is amber. Never add a
green/red palette; invert instead (a strong result is quiet olive, not green).

## When to use

- The user asks to "make a report / dashboard / HTML / artifact" out of some data or analysis.
- You're about to dump a big markdown table or a long data-heavy answer — a report reads better.
- **gm-coach**: any time you produce a *report* (not a quick chat answer) — a weaknesses
  breakdown, a repertoire audit, a stats overview, a game review. See the mapping below.

Don't use it for a one-line answer or a quick prose reply — that's chat, not a report.

## Workflow (every time)

1. **Get the data.** For gm-coach, run the `gm … --json` calls first (facts are KB-gated —
   never invent a number). Otherwise gather the real content; no lorem.
2. **Pick components** from the catalog below that fit the data's shape.
3. **Write the file** to your scratchpad dir (e.g. `…/scratchpad/<slug>.html`). Structure:
   - a `<title>`,
   - a `<style>` block containing the **entire** contents of `reference/amber-ledger.css`
     inlined verbatim (you cannot `<link>` it — CSP blocks it and skill files aren't served),
   - the report body using the component markup,
   - if you used a chart, a `<script>` block with the **entire** contents of
     `reference/amber-charts.js` inlined, then your `AmberChart.line/bars/scatter(...)` calls.
   - Do NOT add `<!doctype>`, `<html>`, `<head>`, or `<body>` — the Artifact wrapper adds them.
4. **Publish** with the `Artifact` tool: `favicon:"📟"`, a one-sentence `description`.
   Read `artifact-design` once if you want to push the craft further.
5. **Self-check before publish** (these are the failures that actually happen):
   - No external resource loads (`<link>`, `<img src=http>`, webfont URL, `fetch`, CDN). Text/URLs shown *as text* are fine.
   - Body never scrolls sideways: wrap wide tables/ledgers in `<div class="scroll">`; long URLs get `overflow-wrap:anywhere`.
   - Amber small text uses `--amber-ink` (the plain `--amber` fails AA below ~18px).
   - Charts are enhancement — the report must read with JS stripped.

## Component catalog

All markup examples assume the CSS from `reference/amber-ledger.css` is inlined.
Full worked example: `reference/example-weaknesses.html` (a real gm Weakness Report).

| Component | Use for | Key classes |
|---|---|---|
| **frontmatter** | a `$ command …` header + status chip, CLI-native | `.frontmatter .prompt`, `.chip`, `.scan` |
| **verdict** | the one-line answer, up top, large mono | `.verdict h1`, `.lede`, `.cursor` |
| **eyebrow** | a section header with a rank kicker | `.eyebrow .rank`, `h2`, `.note` |
| **ranked ledger** | rank items by a metric; bar + optional threshold splits `.sig` (amber) from `.noise` (olive) | `.ledger`, `.axis`, `.lrow.sig/.noise`, `.track`, `.lfill` |
| **stat grid** | KPI cards for an overview; `.flag` the one needing attention | `.statgrid`, `.stat.flag`, `.num`, `.sub` |
| **data table** | rows with inline magnitude bars or W-D-L stacked bars | `.dtable`, `.bar>i`, `.wdl>.w/.d/.l`, `tr.flag` |
| **deep-dive record** | an expanded write-up of one item | `.rec`, `.rec-h .rk/.nm/.tag`, `.cmd` |
| **callout** | the "what to do" / recommendation box | `.callout .row .arw/.txt` |
| **figure** | a canvas chart (trend/distribution) + caption | `.fig canvas`, `.figcap`, `.legend` |
| **footer** | method / provenance colophon | `.foot` |

### Ledger mechanics (the signature component)
- Rank rows by the metric; set each `.lfill` width to `metric/max * 100%` inline.
- `.lrow.sig` = amber, expanded, note inline (the ones that matter). `.lrow.noise` =
  olive, dimmed, note behind a `<details class="off">`. This makes the page self-sort.
- Optional threshold line: add `.thr` to each `.track` and set `--thr` (e.g. `--thr:40%`)
  on the `.ledger`; label the two zones in `.axis .track-lbl`.
- Retune columns once via `--cols` on `.ledger`. Add a per-row `style="--i:N"` for the
  staggered type-in, and add `class="ledger lit"` + the tiny bootstrap script (see example)
  to trigger it. Bars render full-width with no JS and under reduced-motion.

## gm-coach report mapping

When gm-coach produces a report, translate the `gm --json` shape like this:

| `gm` report | AMBER LEDGER shape |
|---|---|
| `gm weaknesses --json` | **ranked ledger** — rank by `winprob_lost`; each row's worst example (`game_uuid` ply `san`) as the note; the had-time set is a second ledger. Amber = the top cost(s). |
| `gm repertoire --json` | **data table** per color — Opening · Games · Score `.bar` · W-D-L `.wdl`; `tr.flag` the leaks (score < ~0.45) in amber, strong lines quiet olive. |
| `gm stats --json` | **verdict** + **stat grid** (rating per time class, win%, blunder/flag rate — `.flag` the defensive-leak stat) + optional rating-trend **figure** (`AmberChart.line`). |
| `gm game <uuid>` | **verdict** (the lesson) + a **deep-dive record**; optionally an eval **figure** (`AmberChart.line` over plies). |

Keep the coaching voice: the report still **leads with a verdict and ends with one rep**
(gm-coach R1/R5). The HTML is the evidence layer under your judgment — it does not replace
the coaching decision, it displays the facts it rests on. Facts stay KB-gated.
