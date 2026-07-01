# gm — local chess knowledge base + Claude Code coach

Sync your Chess.com games into a local SQLite knowledge base with Stockfish
per-move analysis, then let Claude Code coach you from it — recurring
weaknesses, opening repertoire, and ad-hoc questions grounded in your own games.

Status: **design approved, not yet implemented.**

## Prerequisites

- Python 3.11+
- Stockfish (`brew install stockfish`; or set `$STOCKFISH_PATH`)

## Design

Full PRD lives in the vault:
`Projects/personal/gm-incubator/prd-chess-coach.md`
