import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
  uuid TEXT PRIMARY KEY,
  url TEXT,
  end_time INTEGER,
  time_class TEXT,
  time_control TEXT,
  color TEXT,            -- eric's color: 'white'|'black'
  result TEXT,           -- 'win'|'loss'|'draw'
  my_rating INTEGER,
  opp_rating INTEGER,
  eco TEXT,
  opening_name TEXT,
  accuracy_self REAL,    -- chess.com accuracy for eric's side (nullable)
  pgn TEXT,
  analyzed_at INTEGER
);
CREATE TABLE IF NOT EXISTS moves (
  game_uuid TEXT REFERENCES games(uuid),
  ply INTEGER,
  san TEXT,
  fen_before TEXT,
  eval_best_cp INTEGER,     -- mover POV, value of best move
  best_move TEXT,           -- uci
  eval_played_cp INTEGER,   -- mover POV, value after played move
  winprob_delta REAL,       -- win% lost by mover, >=0
  clock_ms INTEGER,
  phase TEXT,               -- 'opening'|'middlegame'|'endgame'
  clock_bucket TEXT,        -- 'had_time'|'low_clock'
  error_type TEXT,          -- nullable category
  severity TEXT,            -- nullable 'inaccuracy'|'mistake'|'blunder'
  is_mine INTEGER,          -- 1 if eric's move
  PRIMARY KEY (game_uuid, ply)
);
CREATE TABLE IF NOT EXISTS sync_state (
  username TEXT,
  time_class TEXT,
  last_end_time INTEGER,
  PRIMARY KEY (username, time_class)
);
CREATE INDEX IF NOT EXISTS idx_moves_err ON moves(is_mine, severity, error_type);
"""


def connect(path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
