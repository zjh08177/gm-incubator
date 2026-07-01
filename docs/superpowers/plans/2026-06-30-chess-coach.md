# gm Chess Coach — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `gm` — a local SQLite knowledge base of Eric's Chess.com games with Stockfish per-move analysis, a query CLI, and a Claude Code coach skill — live-verified on his real account.

**Architecture:** Three layers. (1) Sync: Chess.com public API → PGN → Stockfish → classify → SQLite, incremental and idempotent. (2) KB: SQLite is the single source of truth; aggregates computed on read. (3) Tools: a query CLI (JSON/Markdown out) wrapped by a Claude Code skill; Claude narrates, never computes chess facts.

**Tech Stack:** Python 3.11+, `python-chess`, `httpx`, `typer`, `rich`, stdlib `sqlite3`, Stockfish binary.

## Global Constraints

- Python **3.11+**. `src/` layout package named `gm`.
- Deps only: `python-chess`, `httpx`, `typer`, `rich` (+ `pytest` dev). No scipy/numpy/pandas.
- Stockfish is an **external binary**; resolve via `$STOCKFISH_PATH` then `shutil.which("stockfish")`.
- Every network test uses **committed fixtures**, never a live call. Only Task 18 (live acceptance) hits the network.
- Engine-dependent tests **skip** (not fail) when Stockfish is absent.
- Chess.com HTTP calls MUST send a `User-Agent` header (API returns 403 without one).
- Win-loss magnitude is measured in **win-probability fraction** (0..1), not raw centipawns.
- Evals stored **from the mover's point of view** (positive = good for the side that just moved / is to move).
- `is_mine = 1` marks Eric's own moves; all weakness aggregation filters on it.

---

## File Structure

```
gm-incubator/
  pyproject.toml
  src/gm/
    __init__.py
    config.py            # paths + Stockfish discovery
    db.py                # sqlite connect + schema (idempotent)
    chesscom.py          # Chess.com API client + game normalization
    sync.py              # incremental, idempotent sync orchestration
    analysis/
      __init__.py
      winprob.py         # cp<->win% logistic, delta, severity
      phase.py           # phase tagging
      clock.py           # clock parse + bucket
      engine.py          # Stockfish wrapper
      see.py             # static exchange evaluation
      classify.py        # weakness categorizer
      pipeline.py        # analyze one game -> move rows
    stats/
      __init__.py
      overview.py        # gm stats
      weaknesses.py      # gm weaknesses
      repertoire.py      # gm repertoire
      queries.py         # search-games, find-positions, one game
    report.py            # markdown rendering
    accept.py            # L5 accuracy rank-correlation + negative control
    cli.py               # typer app
  tests/
    fixtures/
      month_sample.json  # trimmed real chess.com month payload
      games/*.pgn        # tiny hand-labeled games
    conftest.py          # seeded-KB + tmp-db fixtures
    test_*.py
  skills/gm-coach/SKILL.md
  docs/superpowers/plans/2026-06-30-chess-coach.md   # this file
```

**Layer → task map (exit gate per subtask):**

| Layer | Tasks | Gate |
|---|---|---|
| L0 scaffold | 1 | `pytest` + `gm --help` run |
| L1 sync+KB | 2,3,7,10 | schema idempotent · fixture parse · engine sign · sync idempotent |
| L2 classifier | 4,5,6,8,9 | mocked-eval unit tests + negative controls |
| L3 query CLI | 11,12,13,14,15 | seeded-KB → expected JSON/MD |
| L4 coach skill | 16 | scripted question routes to right tool, facts grounded |
| L5 live accept | 17,18 | ρ<−0.6 vs accuracies · shuffle control |ρ|≈0 · real-account run |

---

## L0 — Scaffold

### Task 1: Project scaffold + config

**Files:**
- Create: `pyproject.toml`, `src/gm/__init__.py`, `src/gm/config.py`, `src/gm/cli.py`, `tests/conftest.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `config.db_path() -> pathlib.Path`, `config.cache_dir() -> pathlib.Path`, `config.stockfish_path() -> str | None`
- Produces: `cli.app` (typer.Typer) with a working `--help`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "gm"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["python-chess>=1.11", "httpx>=0.27", "typer>=0.12", "rich>=13"]

[project.optional-dependencies]
dev = ["pytest>=8"]

[project.scripts]
gm = "gm.cli:app"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Write the failing test** — `tests/test_config.py`

```python
import os
from gm import config

def test_db_path_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("GM_DB", str(tmp_path / "x.sqlite"))
    assert config.db_path() == tmp_path / "x.sqlite"

def test_stockfish_env_override(monkeypatch):
    monkeypatch.setenv("STOCKFISH_PATH", "/usr/bin/stockfish")
    assert config.stockfish_path() == "/usr/bin/stockfish"

def test_stockfish_none_when_absent(monkeypatch):
    monkeypatch.delenv("STOCKFISH_PATH", raising=False)
    monkeypatch.setattr(config.shutil, "which", lambda _: None)
    assert config.stockfish_path() is None
```

- [ ] **Step 3: Run — expect FAIL** (`ModuleNotFoundError: gm.config`)

Run: `pip install -e ".[dev]" && pytest tests/test_config.py -v`

- [ ] **Step 4: Implement `src/gm/config.py`**

```python
import os
import shutil
from pathlib import Path

def _base() -> Path:
    return Path(os.environ.get("GM_HOME", Path.home() / ".gm"))

def db_path() -> Path:
    return Path(os.environ["GM_DB"]) if "GM_DB" in os.environ else _base() / "gm.sqlite"

def cache_dir() -> Path:
    d = Path(os.environ["GM_CACHE"]) if "GM_CACHE" in os.environ else _base() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d

def stockfish_path() -> str | None:
    return os.environ.get("STOCKFISH_PATH") or shutil.which("stockfish")
```

- [ ] **Step 5: Implement `src/gm/cli.py` (skeleton)**

```python
import typer
app = typer.Typer(help="gm — local chess knowledge base + coach", no_args_is_help=True)

@app.command()
def version():
    """Print version."""
    typer.echo("gm 0.1.0")

if __name__ == "__main__":
    app()
```

- [ ] **Step 6: Empty `tests/conftest.py`** (fixtures added in Task 2)

```python
# shared pytest fixtures; populated in later tasks
```

- [ ] **Step 7: Run — expect PASS + help works**

Run: `pytest tests/test_config.py -v && gm --help`
Expected: 3 passed; help lists `version`.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml src tests && git commit -m "feat: scaffold gm package + config"
```

---

## L1 — Sync + Knowledge Base

### Task 2: SQLite schema (idempotent)

**Files:**
- Create: `src/gm/db.py`, `tests/test_db.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- Produces: `db.connect(path) -> sqlite3.Connection` (Row factory, FKs on), `db.init_db(conn) -> None`
- Produces tables `games`, `moves`, `sync_state` (columns below — every later task depends on these names)

- [ ] **Step 1: Write the failing test** — `tests/test_db.py`

```python
from gm import db

def test_init_creates_tables(tmp_path):
    conn = db.connect(tmp_path / "t.sqlite")
    db.init_db(conn)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"games", "moves", "sync_state"} <= names

def test_init_is_idempotent(tmp_path):
    conn = db.connect(tmp_path / "t.sqlite")
    db.init_db(conn); db.init_db(conn)   # must not raise
    cols = {r[1] for r in conn.execute("PRAGMA table_info(moves)")}
    assert {"game_uuid","ply","winprob_delta","error_type","is_mine","clock_bucket","phase"} <= cols
```

- [ ] **Step 2: Run — expect FAIL** (`ModuleNotFoundError: gm.db`)

Run: `pytest tests/test_db.py -v`

- [ ] **Step 3: Implement `src/gm/db.py`**

```python
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
```

- [ ] **Step 4: Add shared fixtures to `tests/conftest.py`**

```python
import pytest
from gm import db as _db

@pytest.fixture
def conn(tmp_path):
    c = _db.connect(tmp_path / "test.sqlite")
    _db.init_db(c)
    return c
```

- [ ] **Step 5: Run — expect PASS**

Run: `pytest tests/test_db.py -v`

- [ ] **Step 6: Commit**

```bash
git add src/gm/db.py tests && git commit -m "feat: sqlite schema (games/moves/sync_state)"
```

### Task 3: Chess.com client + game normalization

**Files:**
- Create: `src/gm/chesscom.py`, `tests/test_chesscom.py`, `tests/fixtures/month_sample.json`

**Interfaces:**
- Produces: `chesscom.USER_AGENT`, `chesscom.get_archives(username, client) -> list[str]`, `chesscom.get_month(url, client) -> list[dict]`, `chesscom.normalize(raw, username) -> dict`
- `normalize` returns keys matching `games` columns: `uuid,url,end_time,time_class,time_control,color,result,my_rating,opp_rating,eco,opening_name,accuracy_self,pgn`

- [ ] **Step 1: Create `tests/fixtures/month_sample.json`** — one White win + one Black loss, minimal but real-shaped

```json
{"games": [
  {"uuid":"g1","url":"https://chess.com/game/g1","end_time":1717200000,
   "time_class":"bullet","time_control":"60","rated":true,"rules":"chess",
   "eco":"https://chess.com/openings/Italian-Game",
   "accuracies":{"white":83.1,"black":74.2},
   "white":{"username":"eric","rating":1450,"result":"win"},
   "black":{"username":"opp1","rating":1440,"result":"resigned"},
   "pgn":"[Event \"x\"]\n[ECO \"C50\"]\n[Opening \"Italian Game\"]\n[TimeControl \"60\"]\n\n1. e4 {[%clk 0:01:00]} e5 {[%clk 0:00:59]} 2. Nf3 {[%clk 0:00:58]} 1-0\n"},
  {"uuid":"g2","url":"https://chess.com/game/g2","end_time":1717300000,
   "time_class":"bullet","time_control":"60","rated":true,"rules":"chess",
   "eco":"https://chess.com/openings/Sicilian-Defense",
   "accuracies":{"white":91.0,"black":55.5},
   "white":{"username":"opp2","rating":1500,"result":"win"},
   "black":{"username":"eric","rating":1460,"result":"checkmated"},
   "pgn":"[Event \"y\"]\n[ECO \"B20\"]\n[Opening \"Sicilian Defense\"]\n[TimeControl \"60\"]\n\n1. e4 {[%clk 0:01:00]} c5 {[%clk 0:00:59]} 1-0\n"}
]}
```

- [ ] **Step 2: Write the failing test** — `tests/test_chesscom.py`

```python
import json
from pathlib import Path
from gm import chesscom

FIX = Path(__file__).parent / "fixtures" / "month_sample.json"

def test_normalize_white_win():
    raw = json.loads(FIX.read_text())["games"][0]
    g = chesscom.normalize(raw, "eric")
    assert g["uuid"] == "g1"
    assert g["color"] == "white"
    assert g["result"] == "win"
    assert g["my_rating"] == 1450 and g["opp_rating"] == 1440
    assert g["accuracy_self"] == 83.1
    assert g["opening_name"] == "Italian Game"
    assert g["time_class"] == "bullet"

def test_normalize_black_loss():
    raw = json.loads(FIX.read_text())["games"][1]
    g = chesscom.normalize(raw, "eric")
    assert g["color"] == "black"
    assert g["result"] == "loss"
    assert g["accuracy_self"] == 55.5

def test_username_match_is_case_insensitive():
    raw = json.loads(FIX.read_text())["games"][0]
    g = chesscom.normalize(raw, "ERIC")
    assert g["color"] == "white"
```

- [ ] **Step 3: Run — expect FAIL**

Run: `pytest tests/test_chesscom.py -v`

- [ ] **Step 4: Implement `src/gm/chesscom.py`**

```python
import re
import time
import httpx

USER_AGENT = "gm-chess-coach/0.1 (contact: ericzjh08177@gmail.com)"
_RESULT = {"win": "win"}  # everything else mapped below

def _client(client=None):
    return client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30)

def _get_json(url, client, retries=4):
    c = _client(client)
    for attempt in range(retries):
        r = c.get(url)
        if r.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()

def get_archives(username, client=None) -> list[str]:
    data = _get_json(f"https://api.chess.com/pub/player/{username}/games/archives", client)
    return data.get("archives", [])

def get_month(url, client=None) -> list[dict]:
    return _get_json(url, client).get("games", [])

def _result(chesscom_result: str) -> str:
    if chesscom_result == "win":
        return "win"
    if chesscom_result in {"agreed", "repetition", "stalemate", "insufficient",
                           "50move", "timevsinsufficient"}:
        return "draw"
    return "loss"

def _tag(pgn: str, name: str) -> str | None:
    m = re.search(rf'\[{name} "([^"]*)"\]', pgn or "")
    return m.group(1) if m else None

def normalize(raw: dict, username: str) -> dict:
    u = username.lower()
    mine, opp = ("white", "black") if raw["white"]["username"].lower() == u else ("black", "white")
    acc = raw.get("accuracies") or {}
    return {
        "uuid": raw["uuid"],
        "url": raw.get("url"),
        "end_time": raw.get("end_time"),
        "time_class": raw.get("time_class"),
        "time_control": raw.get("time_control"),
        "color": mine,
        "result": _result(raw[mine]["result"]),
        "my_rating": raw[mine].get("rating"),
        "opp_rating": raw[opp].get("rating"),
        "eco": _tag(raw.get("pgn", ""), "ECO"),
        "opening_name": _tag(raw.get("pgn", ""), "Opening"),
        "accuracy_self": acc.get(mine),
        "pgn": raw.get("pgn"),
    }
```

- [ ] **Step 5: Run — expect PASS**

Run: `pytest tests/test_chesscom.py -v`

- [ ] **Step 6: Commit**

```bash
git add src/gm/chesscom.py tests && git commit -m "feat: chess.com client + game normalization"
```

---

## L2 — Analysis & Classifier

### Task 4: Win-probability math + severity

**Files:**
- Create: `src/gm/analysis/__init__.py`, `src/gm/analysis/winprob.py`, `tests/test_winprob.py`

**Interfaces:**
- Produces: `winprob.cp_to_winprob(cp:int)->float`, `winprob.loss(best_cp:int, played_cp:int)->float`, `winprob.severity(loss:float)->str|None`, `winprob.MATE_CP=100000`

- [ ] **Step 1: Write the failing test** — `tests/test_winprob.py`

```python
from gm.analysis import winprob as w

def test_zero_is_half():
    assert abs(w.cp_to_winprob(0) - 0.5) < 1e-9

def test_monotonic_and_bounded():
    assert w.cp_to_winprob(300) > w.cp_to_winprob(100) > 0.5
    assert 0.0 < w.cp_to_winprob(-2000) < 0.5 < w.cp_to_winprob(2000) < 1.0

def test_loss_is_nonnegative_and_directional():
    assert w.loss(300, 300) == 0.0          # played the best move
    assert w.loss(300, -300) > 0.4          # threw away a winning position
    assert w.loss(-100, -120) >= 0.0        # never negative

def test_severity_thresholds():
    assert w.severity(0.03) is None
    assert w.severity(0.06) == "inaccuracy"
    assert w.severity(0.12) == "mistake"
    assert w.severity(0.30) == "blunder"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest tests/test_winprob.py -v`

- [ ] **Step 3: Implement `src/gm/analysis/winprob.py`**

```python
import math

MATE_CP = 100000
_K = 0.00368208  # lichess-derived logistic constant

def cp_to_winprob(cp: int) -> float:
    cp = max(-MATE_CP, min(MATE_CP, cp))
    return 1.0 / (1.0 + math.exp(-_K * cp))

def loss(best_cp: int, played_cp: int) -> float:
    return max(0.0, cp_to_winprob(best_cp) - cp_to_winprob(played_cp))

def severity(loss_val: float) -> str | None:
    if loss_val > 0.20:
        return "blunder"
    if loss_val > 0.10:
        return "mistake"
    if loss_val > 0.05:
        return "inaccuracy"
    return None
```

- [ ] **Step 4: Run — expect PASS.** Run: `pytest tests/test_winprob.py -v`
- [ ] **Step 5: Commit.** `git add src/gm/analysis && git commit -m "feat: win-prob math + severity"`

### Task 5: Phase tagging

**Files:** Create `src/gm/analysis/phase.py`, `tests/test_phase.py`

**Interfaces:** Produces `phase.game_phase(board: chess.Board, ply: int) -> str`

- [ ] **Step 1: Write the failing test**

```python
import chess
from gm.analysis import phase

def test_opening_early_full_board():
    assert phase.game_phase(chess.Board(), ply=2) == "opening"

def test_middlegame_full_board_later():
    assert phase.game_phase(chess.Board(), ply=30) == "middlegame"

def test_endgame_few_pieces():
    b = chess.Board("8/5k2/8/8/8/3K4/6R1/8 w - - 0 40")  # K+R vs K
    assert phase.game_phase(b, ply=80) == "endgame"
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_phase.py -v`
- [ ] **Step 3: Implement `src/gm/analysis/phase.py`**

```python
import chess

def game_phase(board: chess.Board, ply: int) -> str:
    pieces = chess.popcount(board.occupied)  # includes both kings
    if pieces <= 10:
        return "endgame"
    if ply <= 20:  # first 10 full moves
        return "opening"
    return "middlegame"
```

- [ ] **Step 4: Run — expect PASS.** `pytest tests/test_phase.py -v`
- [ ] **Step 5: Commit.** `git add src/gm/analysis/phase.py tests && git commit -m "feat: phase tagging"`

### Task 6: Clock parsing + bucket

**Files:** Create `src/gm/analysis/clock.py`, `tests/test_clock.py`

**Interfaces:** Produces `clock.base_seconds(tc:str)->int`, `clock.bucket(clock_ms:int|None, tc:str)->str`

- [ ] **Step 1: Write the failing test**

```python
from gm.analysis import clock

def test_base_seconds_variants():
    assert clock.base_seconds("60") == 60
    assert clock.base_seconds("60+0") == 60
    assert clock.base_seconds("180+2") == 180

def test_bucket_low_and_had_time():
    assert clock.bucket(3000, "60") == "low_clock"     # 3s left on a 60s game
    assert clock.bucket(45000, "60") == "had_time"     # 45s left
    assert clock.bucket(None, "60") == "had_time"      # unknown -> assume had time
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_clock.py -v`
- [ ] **Step 3: Implement `src/gm/analysis/clock.py`**

```python
def base_seconds(tc: str) -> int:
    if not tc:
        return 0
    return int(str(tc).split("+")[0])

def bucket(clock_ms: int | None, tc: str) -> str:
    if clock_ms is None:
        return "had_time"
    thresh = max(5.0, 0.10 * base_seconds(tc))
    return "low_clock" if clock_ms / 1000.0 < thresh else "had_time"
```

- [ ] **Step 4: Run — expect PASS.** `pytest tests/test_clock.py -v`
- [ ] **Step 5: Commit.** `git add src/gm/analysis/clock.py tests && git commit -m "feat: clock bucket"`

### Task 7: Stockfish engine wrapper (integration)

**Files:** Create `src/gm/analysis/engine.py`, `tests/test_engine_integration.py`

**Interfaces:** Produces `engine.Analyzer` context manager with `analyse(board) -> tuple[int, str]` returning `(eval_cp_mover_pov, best_move_uci)`

- [ ] **Step 1: Write the failing test** (skips cleanly without a binary)

```python
import chess, pytest
from gm import config
from gm.analysis.engine import Analyzer

pytestmark = pytest.mark.skipif(config.stockfish_path() is None,
                                reason="stockfish not installed")

def test_finds_winning_capture_sign():
    # White to move, free queen capture on d8 is best; eval strongly positive.
    b = chess.Board("3qk3/8/8/8/8/8/8/3QK3 w - - 0 1")
    with Analyzer(depth=10) as a:
        cp, best = a.analyse(b)
    assert cp > 300
    assert best.startswith("d1d8") or "d8" in best

def test_forced_only_move_negative_control():
    # A stable roughly-equal position: best move loss should be ~0 downstream.
    b = chess.Board()
    with Analyzer(depth=10) as a:
        cp, best = a.analyse(b)
    assert -100 < cp < 100  # start position is near equal
```

- [ ] **Step 2: Run — expect FAIL or SKIP.** `pytest tests/test_engine_integration.py -v`
- [ ] **Step 3: Implement `src/gm/analysis/engine.py`**

```python
import chess
import chess.engine
from gm import config
from gm.analysis.winprob import MATE_CP

class Analyzer:
    def __init__(self, depth: int = 12, path: str | None = None):
        self.depth = depth
        self.path = path or config.stockfish_path()
        if not self.path:
            raise RuntimeError("Stockfish not found; set STOCKFISH_PATH")
        self._engine = None

    def __enter__(self):
        self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        return self

    def __exit__(self, *exc):
        if self._engine:
            self._engine.quit()

    def analyse(self, board: chess.Board) -> tuple[int, str]:
        info = self._engine.analyse(board, chess.engine.Limit(depth=self.depth))
        score = info["score"].pov(board.turn)
        cp = score.score(mate_score=MATE_CP)
        best = info["pv"][0].uci() if info.get("pv") else ""
        return cp, best
```

- [ ] **Step 4: Run — expect PASS (or SKIP).** `pytest tests/test_engine_integration.py -v`
- [ ] **Step 5: Commit.** `git add src/gm/analysis/engine.py tests && git commit -m "feat: stockfish analyzer wrapper"`

### Task 8: Static exchange eval + weakness classifier

**Files:** Create `src/gm/analysis/see.py`, `src/gm/analysis/classify.py`, `tests/test_see.py`, `tests/test_classify.py`

**Interfaces:**
- Produces: `see.see_capture(board: chess.Board, move: chess.Move) -> int` (pawns; +ve = winning capture for the side to move)
- Produces: `see.hanging_after(board_after: chess.Board) -> bool` (opponent-to-move has a winning capture)
- Produces: `classify.classify(board_before, played_uci, best_uci, eval_best_cp, eval_played_cp, severity, phase) -> str | None` returning one of `dropped_material|missed_tactic|allowed_tactic|endgame_conversion|None`

- [ ] **Step 1: Write the failing SEE test** — `tests/test_see.py`

```python
import chess
from gm.analysis import see

def test_free_capture_is_positive():
    # White rook takes undefended black pawn on a7.
    b = chess.Board("8/p7/8/8/8/8/8/R3K2k w - - 0 1")
    mv = chess.Move.from_uci("a1a7")
    assert see.see_capture(b, mv) > 0

def test_bad_capture_is_negative():
    # White queen takes a defended pawn; recapture wins the queen.
    b = chess.Board("4k3/8/8/3p4/8/3Q4/8/4K3 w - - 0 1")
    # add a defender of d5
    b = chess.Board("4k3/2p5/8/3p4/8/3Q4/8/4K3 w - - 0 1")
    mv = chess.Move.from_uci("d3d5")
    assert see.see_capture(b, mv) < 0

def test_hanging_after_detects_free_piece():
    # Black to move can grab an undefended white knight on e4.
    b = chess.Board("4k3/8/8/8/4N3/8/8/4K2q b - - 0 1")
    assert see.hanging_after(b) is True
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_see.py -v`
- [ ] **Step 3: Implement `src/gm/analysis/see.py`**

```python
import chess

VAL = {chess.PAWN:1, chess.KNIGHT:3, chess.BISHOP:3,
       chess.ROOK:5, chess.QUEEN:9, chess.KING:100}

def _least_attacker(board, sq, color):
    attackers = board.attackers(color, sq)
    if not attackers:
        return None
    return min(attackers, key=lambda s: VAL[board.piece_type_at(s)])

def see_capture(board: chess.Board, move: chess.Move) -> int:
    """Static exchange evaluation of a capture, in pawns, from mover POV."""
    target = board.piece_type_at(move.to_square)
    if target is None:
        return 0
    gain = [VAL[target]]
    b = board.copy(stack=False)
    b.push(move)
    sq = move.to_square
    occupied_val = VAL[board.piece_type_at(move.from_square)]
    color = not board.turn  # side to recapture
    while True:
        frm = _least_attacker(b, sq, color)
        if frm is None:
            break
        gain.append(occupied_val - gain[-1])
        occupied_val = VAL[b.piece_type_at(frm)]
        b.remove_piece_at(sq)
        b.set_piece_at(sq, b.piece_at(frm))
        b.remove_piece_at(frm)
        color = not color
    for i in range(len(gain) - 2, -1, -1):
        gain[i] = -max(-gain[i], gain[i + 1])
    return gain[0]

def hanging_after(board_after: chess.Board) -> bool:
    """True if the side to move on board_after has a strictly winning capture."""
    for mv in board_after.legal_moves:
        if board_after.is_capture(mv) and see_capture(board_after, mv) > 0:
            return True
    return False
```

- [ ] **Step 4: Write the failing classifier test** — `tests/test_classify.py`

```python
import chess
from gm.analysis import classify
from gm.analysis import winprob as w

def _sev(best, played):
    return w.severity(w.loss(best, played))

def test_no_error_no_category():
    # played == best, no severity -> None
    b = chess.Board()
    assert classify.classify(b, "e2e4", "e2e4", 20, 20, _sev(20, 20), "opening") is None

def test_dropped_material_when_move_hangs_piece():
    # White plays Ne4?? into a square where black queen grabs it free next move.
    b = chess.Board("4k3/8/8/8/8/8/8/3NK2q w - - 0 1")
    # playing Nd1-e3 leaves knight capturable by ...Qxe3? (construct a hang)
    b = chess.Board("4k3/8/8/8/8/4q3/8/3NK3 w - - 0 1")
    played = "d1e3"   # Ne3?? hangs to Qxe3
    sev = "blunder"
    cat = classify.classify(b, played, "e1f1", eval_best_cp=-50,
                            eval_played_cp=-900, severity=sev, phase="middlegame")
    assert cat == "dropped_material"

def test_endgame_conversion_when_winning_endgame_slips():
    b = chess.Board("8/8/8/4k3/8/8/4P3/4K3 w - - 0 60")  # winning K+P endgame
    cat = classify.classify(b, "e2e4", "e1d1", eval_best_cp=300,
                            eval_played_cp=0, severity="blunder", phase="endgame")
    assert cat == "endgame_conversion"

def test_missed_tactic_when_best_was_winning_capture():
    # Best move is a big winning capture (eval_best high, capture), played quiet move.
    b = chess.Board("3qk3/8/8/8/8/8/8/3QK3 w - - 0 1")
    cat = classify.classify(b, "e1f1", "d1d8", eval_best_cp=900,
                            eval_played_cp=0, severity="blunder", phase="middlegame")
    assert cat == "missed_tactic"

def test_allowed_tactic_is_fallback_for_tactical_drop():
    b = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    cat = classify.classify(b, "e2e4", "d2d4", eval_best_cp=30,
                            eval_played_cp=-250, severity="mistake", phase="middlegame")
    assert cat == "allowed_tactic"
```

- [ ] **Step 5: Run — expect FAIL.** `pytest tests/test_classify.py -v`
- [ ] **Step 6: Implement `src/gm/analysis/classify.py`**

```python
import chess
from gm.analysis import see

def classify(board_before: chess.Board, played_uci: str, best_uci: str,
             eval_best_cp: int, eval_played_cp: int,
             severity: str | None, phase: str) -> str | None:
    if severity is None:
        return None

    # 1) Winning endgame that slipped.
    if phase == "endgame" and eval_best_cp >= 200 and (eval_best_cp - eval_played_cp) >= 150:
        return "endgame_conversion"

    # 2) Missed your own tactic: best move was a winning capture/mate you skipped.
    if best_uci:
        best = chess.Move.from_uci(best_uci)
        best_is_capture = board_before.is_capture(best)
        if (eval_best_cp >= 300 and eval_best_cp - eval_played_cp >= 150
                and (best_is_capture or eval_best_cp >= 900)):
            played = chess.Move.from_uci(played_uci)
            if not board_before.is_capture(played):
                return "missed_tactic"

    # 3) Dropped material: your move left a piece capturable for free.
    after = board_before.copy(stack=False)
    after.push(chess.Move.from_uci(played_uci))
    if see.hanging_after(after):
        return "dropped_material"

    # 4) Fallback: your move worsened the position tactically.
    return "allowed_tactic"
```

- [ ] **Step 7: Run — expect PASS.** `pytest tests/test_see.py tests/test_classify.py -v`
- [ ] **Step 8: Commit.** `git add src/gm/analysis/see.py src/gm/analysis/classify.py tests && git commit -m "feat: SEE + weakness classifier"`

### Task 9: Game analysis pipeline

**Files:** Create `src/gm/analysis/pipeline.py`, `tests/test_pipeline.py`

**Interfaces:** Produces `pipeline.analyze_game(pgn:str, color:str, analyzer, depth:int) -> list[dict]` — each dict matches `moves` columns (minus `game_uuid`). Uses a **FakeAnalyzer** in tests.

- [ ] **Step 1: Write the failing test** (mocked analyzer → deterministic, no engine)

```python
import chess, chess.pgn, io
from gm.analysis import pipeline

class FakeAnalyzer:
    """Returns a fixed eval per FEN so the pipeline is deterministic."""
    def __init__(self, table): self.table = table
    def analyse(self, board):
        return self.table.get(board.fen(), (0, list(board.legal_moves)[0].uci()))

def test_pipeline_marks_my_moves_and_computes_delta():
    pgn = '[TimeControl "60"]\n\n1. e4 {[%clk 0:01:00]} e5 {[%clk 0:00:59]} 2. Nf3 *\n'
    rows = pipeline.analyze_game(pgn, color="white", analyzer=FakeAnalyzer({}), depth=1)
    assert rows[0]["is_mine"] == 1        # 1.e4 is White = mine
    assert rows[1]["is_mine"] == 0        # 1...e5 is Black
    assert all(r["winprob_delta"] >= 0 for r in rows)
    assert all(r["phase"] == "opening" for r in rows)
    assert rows[0]["clock_bucket"] == "had_time"
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_pipeline.py -v`
- [ ] **Step 3: Implement `src/gm/analysis/pipeline.py`**

```python
import io
import chess
import chess.pgn
from gm.analysis import winprob, phase as phase_mod, clock as clock_mod, classify

def analyze_game(pgn: str, color: str, analyzer, depth: int) -> list[dict]:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        return []
    tc = game.headers.get("TimeControl", "")
    my_turn = chess.WHITE if color == "white" else chess.BLACK

    # Pass 1: walk positions, collect (board_before, played, clock, eval_best, best_uci).
    steps = []
    board = game.board()
    node = game
    ply = 0
    while node.variations:
        nxt = node.variations[0]
        played = nxt.move
        ply += 1
        eval_best, best_uci = analyzer.analyse(board)
        clk = nxt.clock()
        steps.append({
            "ply": ply, "san": board.san(played), "fen_before": board.fen(),
            "played_uci": played.uci(), "eval_best_cp": eval_best, "best_uci": best_uci,
            "clock_ms": int(clk * 1000) if clk is not None else None,
            "is_mine": 1 if board.turn == my_turn else 0,
            "phase": phase_mod.game_phase(board, ply),
        })
        board.push(played)
        node = nxt

    # eval_played for ply i = -eval_best of the next position (mover flips).
    rows = []
    for i, s in enumerate(steps):
        nxt_best = steps[i + 1]["eval_best_cp"] if i + 1 < len(steps) else -s["eval_best_cp"]
        eval_played = -nxt_best
        delta = winprob.loss(s["eval_best_cp"], eval_played)
        sev = winprob.severity(delta) if s["is_mine"] else None
        cat = None
        if s["is_mine"] and sev:
            b = chess.Board(s["fen_before"])
            cat = classify.classify(b, s["played_uci"], s["best_uci"],
                                    s["eval_best_cp"], eval_played, sev, s["phase"])
        rows.append({
            "ply": s["ply"], "san": s["san"], "fen_before": s["fen_before"],
            "eval_best_cp": s["eval_best_cp"], "best_move": s["best_uci"],
            "eval_played_cp": eval_played, "winprob_delta": delta,
            "clock_ms": s["clock_ms"], "phase": s["phase"],
            "clock_bucket": clock_mod.bucket(s["clock_ms"], tc),
            "error_type": cat, "severity": sev, "is_mine": s["is_mine"],
        })
    return rows
```

- [ ] **Step 4: Run — expect PASS.** `pytest tests/test_pipeline.py -v`
- [ ] **Step 5: Commit.** `git add src/gm/analysis/pipeline.py tests && git commit -m "feat: game analysis pipeline"`

### Task 10: Incremental sync orchestration

**Files:** Create `src/gm/sync.py`, `tests/test_sync.py`

**Interfaces:** Produces `sync.sync(conn, username, time_class, analyzer, depth=12, max_games=None, full=False, months=None) -> dict` returning `{"fetched":int,"analyzed":int,"skipped":int}`. `months` is an injectable `list[list[rawgame]]` for tests (bypasses HTTP).

- [ ] **Step 1: Write the failing test** (idempotency + filter, no HTTP, no engine)

```python
import json
from pathlib import Path
from gm import sync

FIX = Path(__file__).parent / "fixtures" / "month_sample.json"

class FakeAnalyzer:
    def analyse(self, board):
        return (0, list(board.legal_moves)[0].uci())

def _months():
    return [json.loads(FIX.read_text())["games"]]

def test_first_sync_inserts_then_reruns_skip(conn):
    r1 = sync.sync(conn, "eric", "bullet", FakeAnalyzer(), months=_months())
    assert r1["analyzed"] == 2
    n = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    assert n == 2
    r2 = sync.sync(conn, "eric", "bullet", FakeAnalyzer(), months=_months())
    assert r2["analyzed"] == 0 and r2["skipped"] == 2   # idempotent

def test_time_class_filter(conn):
    months = _months()
    months[0][0]["time_class"] = "rapid"   # exclude one
    r = sync.sync(conn, "eric", "bullet", FakeAnalyzer(), months=months)
    assert r["analyzed"] == 1
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_sync.py -v`
- [ ] **Step 3: Implement `src/gm/sync.py`**

```python
import time
from gm import chesscom
from gm.analysis import pipeline

def _existing(conn, uuid) -> bool:
    return conn.execute("SELECT 1 FROM games WHERE uuid=?", (uuid,)).fetchone() is not None

def _insert(conn, g, rows):
    conn.execute("""INSERT INTO games
        (uuid,url,end_time,time_class,time_control,color,result,my_rating,opp_rating,
         eco,opening_name,accuracy_self,pgn,analyzed_at)
        VALUES (:uuid,:url,:end_time,:time_class,:time_control,:color,:result,:my_rating,
         :opp_rating,:eco,:opening_name,:accuracy_self,:pgn,:analyzed_at)""",
        {**g, "analyzed_at": int(time.time())})
    conn.executemany("""INSERT INTO moves
        (game_uuid,ply,san,fen_before,eval_best_cp,best_move,eval_played_cp,winprob_delta,
         clock_ms,phase,clock_bucket,error_type,severity,is_mine)
        VALUES (:game_uuid,:ply,:san,:fen_before,:eval_best_cp,:best_move,:eval_played_cp,
         :winprob_delta,:clock_ms,:phase,:clock_bucket,:error_type,:severity,:is_mine)""",
        [{**r, "game_uuid": g["uuid"]} for r in rows])

def _iter_months(username, time_class, full, conn, months):
    if months is not None:
        for m in months:
            yield m
        return
    for url in chesscom.get_archives(username):
        yield chesscom.get_month(url)

def sync(conn, username, time_class, analyzer, depth=12,
         max_games=None, full=False, months=None) -> dict:
    last = conn.execute("SELECT last_end_time FROM sync_state WHERE username=? AND time_class=?",
                        (username, time_class)).fetchone()
    last_end = 0 if (last is None or full) else (last[0] or 0)
    fetched = analyzed = skipped = 0
    max_end = last_end
    for raw_games in _iter_months(username, time_class, full, conn, months):
        for raw in raw_games:
            if raw.get("time_class") != time_class:
                continue
            if not full and raw.get("end_time", 0) <= last_end:
                continue
            fetched += 1
            if _existing(conn, raw["uuid"]):
                skipped += 1
                continue
            g = chesscom.normalize(raw, username)
            rows = pipeline.analyze_game(g["pgn"], g["color"], analyzer, depth)
            _insert(conn, g, rows)
            conn.commit()                      # per-game commit = kill-safe
            analyzed += 1
            max_end = max(max_end, raw.get("end_time", 0))
            if max_games and analyzed >= max_games:
                break
        if max_games and analyzed >= max_games:
            break
    conn.execute("""INSERT INTO sync_state(username,time_class,last_end_time)
        VALUES(?,?,?) ON CONFLICT(username,time_class)
        DO UPDATE SET last_end_time=excluded.last_end_time""",
        (username, time_class, max_end))
    conn.commit()
    return {"fetched": fetched, "analyzed": analyzed, "skipped": skipped}
```

- [ ] **Step 4: Run — expect PASS.** `pytest tests/test_sync.py -v`
- [ ] **Step 5: Commit.** `git add src/gm/sync.py tests && git commit -m "feat: incremental idempotent sync"`

---

## L3 — Query CLI

### Task 11: Weakness aggregation

**Files:** Create `src/gm/stats/__init__.py`, `src/gm/stats/weaknesses.py`, `tests/test_weaknesses.py`. Modify `tests/conftest.py` (add `seeded` fixture).

**Interfaces:** Produces `weaknesses.rank(conn, had_time_only=False) -> list[dict]` where each dict is `{"category":str,"count":int,"winprob_lost":float,"example":{"game_uuid","ply","san"}|None}`.

- [ ] **Step 1: Add `seeded` fixture to `tests/conftest.py`**

```python
@pytest.fixture
def seeded(conn):
    conn.execute("""INSERT INTO games(uuid,color,result,time_class,eco,opening_name,
        accuracy_self,end_time) VALUES('gA','white','loss','bullet','C50','Italian Game',70.0,10)""")
    conn.execute("""INSERT INTO games(uuid,color,result,time_class,eco,opening_name,
        accuracy_self,end_time) VALUES('gB','black','win','bullet','B20','Sicilian Defense',88.0,20)""")
    def mv(g,ply,mine,sev,cat,delta,bucket,phase,san="Xx"):
        conn.execute("""INSERT INTO moves(game_uuid,ply,san,fen_before,eval_best_cp,best_move,
            eval_played_cp,winprob_delta,clock_ms,phase,clock_bucket,error_type,severity,is_mine)
            VALUES(?,?,?,'fen',0,'a1a1',0,?,1000,?,?,?,?,?)""",
            (g,ply,san,delta,phase,bucket,cat,sev,mine))
    mv("gA",5,1,"blunder","dropped_material",0.4,"had_time","middlegame")
    mv("gA",7,1,"mistake","dropped_material",0.15,"low_clock","middlegame")
    mv("gA",9,1,"mistake","endgame_conversion",0.18,"had_time","endgame")
    mv("gB",4,1,"blunder","missed_tactic",0.30,"had_time","opening")
    mv("gB",6,0,"blunder","dropped_material",0.5,"had_time","middlegame")  # opponent move, ignored
    conn.commit()
    return conn
```

- [ ] **Step 2: Write the failing test** — `tests/test_weaknesses.py`

```python
from gm.stats import weaknesses

def test_ranks_by_winprob_lost_desc(seeded):
    ranked = weaknesses.rank(seeded)
    cats = [r["category"] for r in ranked]
    assert cats[0] == "dropped_material"        # 0.4+0.15 = 0.55 total
    assert "missed_tactic" in cats
    assert all("example" in r for r in ranked)

def test_only_counts_my_moves(seeded):
    ranked = weaknesses.rank(seeded)
    dropped = next(r for r in ranked if r["category"] == "dropped_material")
    assert dropped["count"] == 2                # opponent's dropped piece excluded

def test_had_time_only_filters_low_clock(seeded):
    ranked = weaknesses.rank(seeded, had_time_only=True)
    dropped = next(r for r in ranked if r["category"] == "dropped_material")
    assert dropped["count"] == 1               # the low_clock mistake removed
```

- [ ] **Step 3: Run — expect FAIL.** `pytest tests/test_weaknesses.py -v`
- [ ] **Step 4: Implement `src/gm/stats/weaknesses.py`**

```python
def rank(conn, had_time_only: bool = False) -> list[dict]:
    clause = "AND clock_bucket='had_time'" if had_time_only else ""
    q = f"""
      SELECT COALESCE(error_type,'other') AS category,
             COUNT(*) AS count, SUM(winprob_delta) AS lost
      FROM moves
      WHERE is_mine=1 AND severity IS NOT NULL {clause}
      GROUP BY category ORDER BY lost DESC"""
    out = []
    for row in conn.execute(q):
        ex = conn.execute(f"""
          SELECT game_uuid, ply, san FROM moves
          WHERE is_mine=1 AND severity IS NOT NULL {clause}
            AND COALESCE(error_type,'other')=?
          ORDER BY winprob_delta DESC LIMIT 1""", (row["category"],)).fetchone()
        out.append({
            "category": row["category"], "count": row["count"],
            "winprob_lost": round(row["lost"], 3),
            "example": dict(ex) if ex else None,
        })
    return out
```

- [ ] **Step 5: Run — expect PASS.** `pytest tests/test_weaknesses.py -v`
- [ ] **Step 6: Commit.** `git add src/gm/stats tests && git commit -m "feat: weakness aggregation"`

### Task 12: Repertoire aggregation

**Files:** Create `src/gm/stats/repertoire.py`, `tests/test_repertoire.py`

**Interfaces:** Produces `repertoire.by_color(conn, color) -> list[dict]` — `{"opening":str,"eco":str,"games":int,"score":float,"wdl":[w,d,l],"break_ply":int|None}` sorted by `games` desc.

- [ ] **Step 1: Write the failing test**

```python
from gm.stats import repertoire

def test_groups_by_opening_and_scores(seeded):
    white = repertoire.by_color(seeded, "white")
    ital = next(r for r in white if r["opening"] == "Italian Game")
    assert ital["games"] == 1
    assert ital["wdl"] == [0, 0, 1]        # one loss
    assert ital["score"] == 0.0
    assert ital["break_ply"] == 5          # earliest opening/my error ply

def test_color_split(seeded):
    black = repertoire.by_color(seeded, "black")
    assert any(r["opening"] == "Sicilian Defense" for r in black)
    assert all(r["opening"] != "Italian Game" for r in black)
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_repertoire.py -v`
- [ ] **Step 3: Implement `src/gm/stats/repertoire.py`**

```python
def by_color(conn, color: str) -> list[dict]:
    games = conn.execute(
        "SELECT uuid, eco, opening_name, result FROM games WHERE color=?", (color,)).fetchall()
    buckets: dict[str, dict] = {}
    for g in games:
        key = g["opening_name"] or g["eco"] or "Unknown"
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
```

- [ ] **Step 4: Run — expect PASS.** `pytest tests/test_repertoire.py -v`
- [ ] **Step 5: Commit.** `git add src/gm/stats/repertoire.py tests && git commit -m "feat: repertoire aggregation"`

### Task 13: Overview + queries

**Files:** Create `src/gm/stats/overview.py`, `src/gm/stats/queries.py`, `tests/test_queries.py`

**Interfaces:**
- Produces: `overview.summary(conn) -> dict` (`games`, `by_time_class`, `rating_latest`, `phase_loss` map, `clock_split`)
- Produces: `queries.search_games(conn, result=None, opening=None, color=None, limit=50) -> list[dict]`
- Produces: `queries.find_positions(conn, error_type=None, phase=None, min_delta=0.0, had_time=False, limit=50) -> list[dict]`
- Produces: `queries.one_game(conn, uuid) -> dict` (game row + its `moves` with `severity` set, ordered by ply)

- [ ] **Step 1: Write the failing test** — `tests/test_queries.py`

```python
from gm.stats import overview, queries

def test_overview_counts(seeded):
    s = overview.summary(seeded)
    assert s["games"] == 2
    assert s["by_time_class"]["bullet"] == 2

def test_search_games_by_result(seeded):
    losses = queries.search_games(seeded, result="loss")
    assert [g["uuid"] for g in losses] == ["gA"]

def test_find_positions_by_category(seeded):
    hits = queries.find_positions(seeded, error_type="missed_tactic")
    assert len(hits) == 1 and hits[0]["game_uuid"] == "gB"

def test_find_positions_had_time_filter(seeded):
    hits = queries.find_positions(seeded, error_type="dropped_material", had_time=True)
    assert len(hits) == 1                      # excludes the low_clock one

def test_one_game_returns_moves(seeded):
    g = queries.one_game(seeded, "gA")
    assert g["uuid"] == "gA"
    assert len(g["moves"]) >= 1
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_queries.py -v`
- [ ] **Step 3: Implement `src/gm/stats/overview.py`**

```python
def summary(conn) -> dict:
    games = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    tc = {r["time_class"]: r["n"] for r in conn.execute(
        "SELECT time_class, COUNT(*) n FROM games GROUP BY time_class")}
    latest = conn.execute(
        "SELECT my_rating FROM games ORDER BY end_time DESC LIMIT 1").fetchone()
    phase_loss = {r["phase"]: round(r["avg"], 3) for r in conn.execute(
        """SELECT phase, AVG(winprob_delta) avg FROM moves
           WHERE is_mine=1 GROUP BY phase""")}
    clock = {r["clock_bucket"]: r["n"] for r in conn.execute(
        """SELECT clock_bucket, COUNT(*) n FROM moves
           WHERE is_mine=1 AND severity IS NOT NULL GROUP BY clock_bucket""")}
    return {"games": games, "by_time_class": tc,
            "rating_latest": latest[0] if latest else None,
            "phase_loss": phase_loss, "clock_split": clock}
```

- [ ] **Step 4: Implement `src/gm/stats/queries.py`**

```python
def search_games(conn, result=None, opening=None, color=None, limit=50) -> list[dict]:
    where, args = [], []
    if result: where.append("result=?"); args.append(result)
    if color: where.append("color=?"); args.append(color)
    if opening: where.append("opening_name LIKE ?"); args.append(f"%{opening}%")
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(
        f"SELECT * FROM games {clause} ORDER BY end_time DESC LIMIT ?", (*args, limit))
    return [dict(r) for r in rows]

def find_positions(conn, error_type=None, phase=None, min_delta=0.0,
                   had_time=False, limit=50) -> list[dict]:
    where = ["is_mine=1", "severity IS NOT NULL", "winprob_delta>=?"]
    args = [min_delta]
    if error_type: where.append("error_type=?"); args.append(error_type)
    if phase: where.append("phase=?"); args.append(phase)
    if had_time: where.append("clock_bucket='had_time'")
    rows = conn.execute(
        f"""SELECT game_uuid,ply,san,fen_before,error_type,severity,winprob_delta,phase
            FROM moves WHERE {' AND '.join(where)}
            ORDER BY winprob_delta DESC LIMIT ?""", (*args, limit))
    return [dict(r) for r in rows]

def one_game(conn, uuid) -> dict:
    g = conn.execute("SELECT * FROM games WHERE uuid=?", (uuid,)).fetchone()
    if g is None:
        return {}
    moves = conn.execute(
        "SELECT * FROM moves WHERE game_uuid=? ORDER BY ply", (uuid,)).fetchall()
    d = dict(g); d["moves"] = [dict(m) for m in moves]
    return d
```

- [ ] **Step 5: Run — expect PASS.** `pytest tests/test_queries.py -v`
- [ ] **Step 6: Commit.** `git add src/gm/stats tests && git commit -m "feat: overview + query tools"`

### Task 14: Markdown rendering

**Files:** Create `src/gm/report.py`, `tests/test_report.py`

**Interfaces:** Produces `report.weaknesses_md(ranked, had_time_ranked) -> str`, `report.repertoire_md(white, black) -> str`

- [ ] **Step 1: Write the failing test**

```python
from gm import report

def test_weaknesses_md_has_headers_and_rows():
    ranked = [{"category":"dropped_material","count":2,"winprob_lost":0.55,
               "example":{"game_uuid":"gA","ply":5,"san":"Ne3"}}]
    md = report.weaknesses_md(ranked, ranked)
    assert "# Weakness Report" in md
    assert "dropped_material" in md and "gA" in md

def test_repertoire_md_splits_colors():
    w = [{"opening":"Italian Game","eco":"C50","games":1,"score":0.0,
          "wdl":[0,0,1],"break_ply":5}]
    md = report.repertoire_md(w, [])
    assert "As White" in md and "Italian Game" in md
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_report.py -v`
- [ ] **Step 3: Implement `src/gm/report.py`**

```python
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
```

- [ ] **Step 4: Run — expect PASS.** `pytest tests/test_report.py -v`
- [ ] **Step 5: Commit.** `git add src/gm/report.py tests && git commit -m "feat: markdown reports"`

### Task 15: CLI wiring

**Files:** Modify `src/gm/cli.py`; Create `tests/test_cli.py`

**Interfaces:** Commands `sync`, `stats`, `weaknesses`, `repertoire`, `game`, `search-games`, `find-positions`. Query commands accept `--json/--md` and `--db PATH`. Uses `typer.testing.CliRunner`.

- [ ] **Step 1: Write the failing test** (drives CLI against a seeded db file)

```python
import json
from typer.testing import CliRunner
from gm.cli import app
from gm import db as _db

runner = CliRunner()

def _seed_file(tmp_path):
    p = tmp_path / "cli.sqlite"
    c = _db.connect(p); _db.init_db(c)
    c.execute("""INSERT INTO games(uuid,color,result,time_class,opening_name,end_time,my_rating)
                 VALUES('gA','white','loss','bullet','Italian Game',10,1450)""")
    c.execute("""INSERT INTO moves(game_uuid,ply,san,fen_before,eval_best_cp,best_move,
        eval_played_cp,winprob_delta,clock_ms,phase,clock_bucket,error_type,severity,is_mine)
        VALUES('gA',5,'Ne3','fen',0,'a1a1',0,0.4,1000,'middlegame','had_time',
               'dropped_material','blunder',1)""")
    c.commit()
    return p

def test_weaknesses_json(tmp_path):
    p = _seed_file(tmp_path)
    res = runner.invoke(app, ["weaknesses", "--db", str(p), "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data[0]["category"] == "dropped_material"

def test_stats_json(tmp_path):
    p = _seed_file(tmp_path)
    res = runner.invoke(app, ["stats", "--db", str(p), "--json"])
    assert res.exit_code == 0
    assert json.loads(res.stdout)["games"] == 1

def test_repertoire_md(tmp_path):
    p = _seed_file(tmp_path)
    res = runner.invoke(app, ["repertoire", "--db", str(p), "--md"])
    assert res.exit_code == 0 and "Italian Game" in res.stdout
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_cli.py -v`
- [ ] **Step 3: Implement `src/gm/cli.py`** (replace skeleton)

```python
import json as _json
import typer
from gm import config, db as _db, report
from gm.stats import weaknesses, repertoire, overview, queries

app = typer.Typer(help="gm — local chess knowledge base + coach", no_args_is_help=True)

def _conn(db):
    c = _db.connect(db or config.db_path()); _db.init_db(c); return c

def _emit(obj, as_json, md=None):
    typer.echo(md if (md is not None and not as_json) else _json.dumps(obj, indent=2))

@app.command()
def sync(username: str, time_class: str = "bullet", max_games: int = typer.Option(None),
         full: bool = False, depth: int = 12, db: str = typer.Option(None)):
    """Fetch + analyze games from Chess.com into the local KB."""
    from gm.analysis.engine import Analyzer
    from gm import sync as sync_mod
    c = _conn(db)
    with Analyzer(depth=depth) as a:
        res = sync_mod.sync(c, username, time_class, a, depth=depth,
                            max_games=max_games, full=full)
    typer.echo(_json.dumps(res, indent=2))

@app.command()
def stats(db: str = typer.Option(None), json: bool = typer.Option(False, "--json")):
    _emit(overview.summary(_conn(db)), json, md=None if json else None)

@app.command()
def weaknesses_cmd(db: str = typer.Option(None), json: bool = typer.Option(False, "--json"),
                   md: bool = typer.Option(False, "--md"), had_time: bool = False):
    c = _conn(db)
    ranked = weaknesses.rank(c, had_time_only=had_time)
    if md:
        typer.echo(report.weaknesses_md(ranked, weaknesses.rank(c, had_time_only=True)))
    else:
        typer.echo(_json.dumps(ranked, indent=2))

@app.command()
def repertoire_cmd(db: str = typer.Option(None), json: bool = typer.Option(False, "--json"),
                   md: bool = typer.Option(False, "--md")):
    c = _conn(db)
    w, b = repertoire.by_color(c, "white"), repertoire.by_color(c, "black")
    if md:
        typer.echo(report.repertoire_md(w, b))
    else:
        typer.echo(_json.dumps({"white": w, "black": b}, indent=2))

@app.command()
def game(uuid: str, db: str = typer.Option(None)):
    typer.echo(_json.dumps(queries.one_game(_conn(db), uuid), indent=2))

@app.command(name="search-games")
def search_games(result: str = typer.Option(None), opening: str = typer.Option(None),
                 color: str = typer.Option(None), db: str = typer.Option(None)):
    typer.echo(_json.dumps(queries.search_games(_conn(db), result, opening, color), indent=2))

@app.command(name="find-positions")
def find_positions(error_type: str = typer.Option(None), phase: str = typer.Option(None),
                   min_delta: float = 0.0, had_time: bool = False, db: str = typer.Option(None)):
    typer.echo(_json.dumps(queries.find_positions(
        _conn(db), error_type, phase, min_delta, had_time), indent=2))

# register aliases so command names are `weaknesses` / `repertoire`
app.command(name="weaknesses")(weaknesses_cmd)
app.command(name="repertoire")(repertoire_cmd)

if __name__ == "__main__":
    app()
```

> Note: `stats` returns JSON always (no MD form). `--json` on it is a no-op accepted for uniformity.

- [ ] **Step 4: Run — expect PASS.** `pytest tests/test_cli.py -v`
- [ ] **Step 5: Full suite green.** Run: `pytest -v` (engine test may SKIP). Expected: all pass/skip.
- [ ] **Step 6: Commit.** `git add src/gm/cli.py tests && git commit -m "feat: query CLI"`

---

## L4 — Coach skill

### Task 16: Claude Code coach skill

**Files:** Create `skills/gm-coach/SKILL.md`, `tests/test_skill.py`

**Interfaces:** A skill doc that routes NL questions → CLI commands and forbids inventing facts.

- [ ] **Step 1: Write the failing test** (validates the skill contract statically)

```python
from pathlib import Path

SKILL = Path("skills/gm-coach/SKILL.md")

def test_skill_exists_and_declares_tools():
    text = SKILL.read_text()
    for cmd in ["gm weaknesses", "gm repertoire", "gm stats",
                "gm search-games", "gm find-positions", "gm game"]:
        assert cmd in text
    assert "never invent" in text.lower() or "do not invent" in text.lower()
    assert "--json" in text
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_skill.py -v`
- [ ] **Step 3: Write `skills/gm-coach/SKILL.md`**

```markdown
---
name: gm-coach
description: Personal chess coach over Eric's local Chess.com knowledge base. Use when he asks about his chess — weaknesses, openings, a specific game, or "how do I improve". Answers are grounded in the `gm` CLI, never invented.
---

# gm Coach

You coach Eric on his own games. The `gm` CLI reads a local SQLite KB of his
analyzed Chess.com games. You NARRATE its output — you never compute chess
facts yourself and you NEVER invent facts about his games.

## Hard rules
- Every claim about HIS play must come from a `gm ... --json` call in this session.
- If the KB is empty, tell him to run `gm sync <username>` first.
- General opening theory for STUDY recommendations is allowed (that is knowledge,
  not a claim about his games). Keep it clearly separated from his stats.

## Tool routing
| He asks… | Run |
|---|---|
| "top weaknesses", "what do I do wrong" | `gm weaknesses --json` (add `--had-time` for real knowledge gaps) |
| "my openings", "repertoire", "what to study" | `gm repertoire --json` |
| "overview", "how am I doing" | `gm stats --json` |
| "show me games where…" | `gm search-games --result/--opening/--color` |
| "positions where I…" | `gm find-positions --error-type/--phase/--had-time` |
| "review game X" | `gm game <uuid>` |

## Method
1. Pick the tool; run it with `--json`.
2. Read the JSON; quote real numbers (counts, win% lost, scores).
3. For bullet, prefer the had-time subset when diagnosing knowledge vs speed.
4. Give at most 3 prioritized, concrete actions. Name a fitting opening only to
   fill a genuine repertoire gap the data shows.
```

- [ ] **Step 4: Run — expect PASS.** `pytest tests/test_skill.py -v`
- [ ] **Step 5: Commit.** `git add skills tests && git commit -m "feat: gm-coach Claude Code skill"`

---

## L5 — Live acceptance

### Task 17: Accuracy rank-correlation + negative control

**Files:** Create `src/gm/accept.py`, `tests/test_accept.py`

**Interfaces:** Produces `accept.spearman(xs, ys) -> float`, `accept.correlate(conn) -> dict` returning `{"n":int,"rho":float,"shuffled_rho":float,"pass":bool}`. `pass` iff `n>=20 and rho < -0.6 and abs(shuffled_rho) < 0.3`.

- [ ] **Step 1: Write the failing test** (synthetic KB where our loss anti-correlates with accuracy)

```python
import random
from gm import accept

def test_spearman_perfect_negative():
    xs = [1,2,3,4,5]; ys = [5,4,3,2,1]
    assert abs(accept.spearman(xs, ys) + 1.0) < 1e-9

def test_correlate_passes_when_loss_tracks_accuracy(conn):
    # accuracy high -> our avg loss low, and vice-versa, for 25 games
    for i in range(25):
        acc = 50 + i * 2                     # 50..98
        conn.execute("INSERT INTO games(uuid,color,accuracy_self,result,time_class) "
                     "VALUES(?,?,?,?,?)", (f"g{i}", "white", float(acc), "loss", "bullet"))
        loss = (100 - acc) / 100.0           # inverse of accuracy
        conn.execute("""INSERT INTO moves(game_uuid,ply,san,fen_before,eval_best_cp,
            best_move,eval_played_cp,winprob_delta,clock_ms,phase,clock_bucket,
            error_type,severity,is_mine) VALUES(?,?, 'x','f',0,'a1a1',0,?,1000,
            'middlegame','had_time',NULL,NULL,1)""", (f"g{i}", 1, loss))
    conn.commit()
    res = accept.correlate(conn)
    assert res["n"] == 25
    assert res["rho"] < -0.6
    assert abs(res["shuffled_rho"]) < 0.3    # negative control
    assert res["pass"] is True
```

- [ ] **Step 2: Run — expect FAIL.** `pytest tests/test_accept.py -v`
- [ ] **Step 3: Implement `src/gm/accept.py`**

```python
import random

def _rank(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks

def _pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0

def spearman(xs, ys) -> float:
    return _pearson(_rank(xs), _rank(ys))

def correlate(conn) -> dict:
    rows = conn.execute("""
        SELECT g.accuracy_self AS acc, AVG(m.winprob_delta) AS loss
        FROM games g JOIN moves m ON m.game_uuid=g.uuid AND m.is_mine=1
        WHERE g.accuracy_self IS NOT NULL
        GROUP BY g.uuid HAVING COUNT(m.ply) > 0""").fetchall()
    acc = [r["acc"] for r in rows]
    loss = [r["loss"] for r in rows]
    n = len(acc)
    if n < 2:
        return {"n": n, "rho": 0.0, "shuffled_rho": 0.0, "pass": False}
    rho = spearman(loss, acc)
    rng = random.Random(1234)                 # deterministic negative control
    shuffled = acc[:]
    rng.shuffle(shuffled)
    srho = spearman(loss, shuffled)
    return {"n": n, "rho": round(rho, 3), "shuffled_rho": round(srho, 3),
            "pass": bool(n >= 20 and rho < -0.6 and abs(srho) < 0.3)}
```

- [ ] **Step 4: Add CLI command** in `src/gm/cli.py`

```python
@app.command()
def accept(db: str = typer.Option(None)):
    """L5 gate: our analysis vs Chess.com accuracies (+ shuffle control)."""
    from gm import accept as acc
    typer.echo(_json.dumps(acc.correlate(_conn(db)), indent=2))
```

- [ ] **Step 5: Run — expect PASS.** `pytest tests/test_accept.py -v && pytest -v`
- [ ] **Step 6: Commit.** `git add src/gm/accept.py src/gm/cli.py tests && git commit -m "feat: L5 accuracy correlation gate"`

### Task 18: Live acceptance runbook (manual gate — the exit)

**Files:** Create `docs/ACCEPTANCE.md`

This task is executed by a human (Eric) with a real Stockfish install and his real username. It is the project exit gate. Record outputs in `docs/ACCEPTANCE.md`.

- [ ] **Step 1: Prereqs**

```bash
brew install stockfish
pip install -e ".[dev]"
gm --help
```

- [ ] **Step 2: Live sync (real account, bounded first run)**

```bash
gm sync <your_username> --time-class bullet --max-games 60
```
Expected: JSON `{"fetched":N,"analyzed":M,...}` with `analyzed > 0`.

- [ ] **Step 3: Idempotency gate** — re-run the exact command.
Expected: `analyzed == 0`, `skipped > 0`.

- [ ] **Step 4: Out-of-band oracle gate (Chess.com accuracies)**

```bash
gm accept
```
Expected: `n >= 20`, `rho < -0.6`, `abs(shuffled_rho) < 0.3`, `"pass": true`.
If `n < 20`, raise `--max-games` (bullet games without Chess.com review lack `accuracy_self` and are skipped by the oracle).

- [ ] **Step 5: Negative control gate** — confirm the shuffled ρ printed in Step 4 is near zero. A near-zero real ρ with a near-zero shuffled ρ = the analysis carries no signal → **FAIL, do not exit.**

- [ ] **Step 6: Per-move spot check (manual out-of-band)** — pick 2 games with low `accuracy_self`:

```bash
gm search-games --result loss
gm game <uuid>
```
Open the same game's Review on chess.com. Confirm the moves `gm` marks `blunder` line up with Chess.com's blunder markers on at least the worst 1–2 moves per game.

- [ ] **Step 7: Classifier false-positive control** — pick a game with high `accuracy_self` (>90):

```bash
gm game <high_accuracy_uuid>
```
Expected: few/no `blunder` rows — the classifier does not cry wolf on a clean game.

- [ ] **Step 8: Bad-input control**

```bash
gm sync this_user_does_not_exist_zzz --time-class bullet
```
Expected: a clean error (HTTP 404 surfaced), no rows written, KB uncorrupted (`gm stats` unchanged).

- [ ] **Step 9: Coach dogfood** — in Claude Code, with the `gm-coach` skill active, ask:
  - "What are my top 3 weaknesses?" → must call `gm weaknesses --json` and quote its numbers.
  - "How's my repertoire as Black?" → must call `gm repertoire --json`.
Confirm every stated fact traces to a CLI call; no invented games or numbers.

- [ ] **Step 10: Record + exit**

```bash
git add docs/ACCEPTANCE.md && git commit -m "docs: live acceptance results — gm v1"
```
**Exit criteria met** when Steps 2–9 all pass, including the two negative controls (5, 7) and the bad-input control (8).

---

## Self-Review

**Spec coverage** (PRD → task):
- Goal 1 (local synced corpus) → Tasks 2,3,10. Goal 2 (weaknesses ranked) → 8,9,11. Goal 3 (repertoire) → 12. Goal 4 (Claude answers grounded) → 16. Goal 5 (had-time split) → 6,9,11,13.
- Functional S1–S5 → Task 10 (+3). A1–A5 → 4,5,6,7,9. Taxonomy → 8. O1–O4 → 12. Query tools → 11,12,13,15. Coach C1–C4 → 16.
- Exit criteria → Tasks 15 (suite green), 17 (correlation), 18 (live). Negative controls → 8 (false-positive test), 17 (shuffle), 18 (steps 5,7,8).

**Placeholder scan:** none — every step has real code/commands.

**Type consistency:** `moves` columns identical across db.py / pipeline / sync insert / stats queries (`eval_best_cp`, `eval_played_cp`, `winprob_delta`, `error_type`, `clock_bucket`, `is_mine`). `Analyzer.analyse(board) -> (cp, uci)` consumed by pipeline. `winprob.loss/severity` used by pipeline + tests. `weaknesses.rank`, `repertoire.by_color`, `queries.*`, `overview.summary`, `accept.correlate` signatures match their CLI callers.

**Known deferrals (not gaps):** semantic search, MCP server, spaced-repetition trainer, style radar, Lichess/OTB, web UI, standalone `--llm` — all listed Out-of-scope in the PRD.
