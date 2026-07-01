# gm v1 — Live Acceptance Record

Exit gate for the MVP. Run on real Chess.com account `zjh08177` with Stockfish 18.
**Result: PASSED (2026-06-30).**

Environment: Stockfish 18 (`/opt/homebrew/bin/stockfish`), Python 3.14, `.venv`, depth 12.

| # | Gate | Expected | Result | Pass |
|---|------|----------|--------|------|
| 1 | Live sync (real API + engine) | `analyzed > 0` | `{fetched:4, analyzed:4}` on real bullet games | ✅ |
| 2 | Idempotency | existing games never re-analyzed, no dupes | re-runs skip existing (`skipped=8`); 8 games/8 distinct/462 moves | ✅ |
| 3 | Oracle (`gm accept`) | `n≥20`, `rho < -0.6` | `n=24, rho=-0.859` | ✅ |
| 4 | Negative control | `abs(shuffled_rho) < 0.3` | `shuffled_rho=-0.126` | ✅ |
| 5 | Spot check (low-accuracy game) | flagged blunders are real eval swings | acc 41.7% game: ply46 dropped_material −0.22WP, ply48 allowed_tactic −0.25WP | ✅ |
| 6 | False-positive control | high-accuracy game not over-flagged | acc 83.4% game: **0** my-blunders | ✅ |
| 7 | Bad input | clean error, KB uncorrupted | `Chess.com user '...' not found.` exit 1, 0 games written | ✅ |
| 8 | Coach dogfood | routes to CLI, facts grounded | grounded weakness summary from `gm weaknesses --json` (see below) | ✅ |

## Oracle detail (gates 3–4)

24 accuracy-bearing bullet games analyzed with our pipeline. Our per-game average
win%-loss vs Chess.com's own accuracy score: **Spearman ρ = −0.859** (strong
inverse — games their engine scores low-accuracy are games our engine scores
high-loss). Shuffling the accuracy labels collapses it to **−0.126**, proving the
correlation is real signal, not an artifact. This is out-of-band validation of the
whole analysis chain against an independent engine.

## Gate 8 — coach grounding (real data, 24 games)

`gm weaknesses --json` → allowed_tactic (120 events, 16.8 WP lost), dropped_material
(99, 15.8), missed_tactic (9, 3.2). Had-time subset: 114 / 90 / 9 respectively —
i.e. ~95% of the top errors happened with time on the clock, so they are judgment
gaps, not pure speed. Missed-own-tactics is rare; the leak is defensive (allowing
the opponent's tactics and hanging pieces). Every number traces to a CLI call.

## Known gaps (deferred, non-blocking)

- Repertoire report displays ECO codes (B15) not names — real chess.com PGNs omit
  the `[Opening]` tag; the raw `eco` URL carries the name (v1.1). Coach skill
  translates ECO→name from general knowledge, so the interactive path is unaffected.
- `--max-games` caps *new analyses*, so re-runs re-fetch archives from the start
  (UUID-skip keeps it correct); month-level incremental fetch is deferred.
