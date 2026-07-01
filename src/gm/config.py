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
