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
