# gm v1 — Live Acceptance Record

Exit gate for the MVP. Run on a real Chess.com account with Stockfish installed.
Fill each result; exit requires all gates + both negative controls to pass.

Environment: Stockfish 18 (`/opt/homebrew/bin/stockfish`), Python 3.14, `.venv`.

| # | Gate | Command | Expected | Result |
|---|------|---------|----------|--------|
| 1 | Live sync | `gm sync <user> --time-class bullet --max-games 60` | `analyzed > 0` | _pending_ |
| 2 | Idempotency | re-run step 1 | `analyzed == 0`, `skipped > 0` | _pending_ |
| 3 | Oracle | `gm accept` | `n>=20`, `rho < -0.6`, `pass: true` | _pending_ |
| 4 | Negative control | (from step 3) | `abs(shuffled_rho) < 0.3` | _pending_ |
| 5 | Spot check | `gm game <low-accuracy uuid>` vs chess.com Review | flagged blunders line up | _pending_ |
| 6 | False-positive control | `gm game <high-accuracy uuid>` | few/no `blunder` rows | _pending_ |
| 7 | Bad input | `gm sync no_such_user_zzz --time-class bullet` | clean error, KB uncorrupted | _pending_ |
| 8 | Coach dogfood | ask gm-coach "top 3 weaknesses?" | calls `gm weaknesses --json`, facts grounded | _pending_ |

## Notes

- **Oracle data dependency:** `gm accept` only counts games with a Chess.com
  `accuracies` value (i.e. games that received Game Review). If step 3 reports
  `n < 20`, raise `--max-games` or add months until ≥20 accuracy-bearing games
  are in the KB.
