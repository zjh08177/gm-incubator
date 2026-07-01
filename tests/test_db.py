from gm import db


def test_init_creates_tables(tmp_path):
    conn = db.connect(tmp_path / "t.sqlite")
    db.init_db(conn)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"games", "moves", "sync_state"} <= names


def test_init_is_idempotent(tmp_path):
    conn = db.connect(tmp_path / "t.sqlite")
    db.init_db(conn)
    db.init_db(conn)  # must not raise
    cols = {r[1] for r in conn.execute("PRAGMA table_info(moves)")}
    assert {"game_uuid", "ply", "winprob_delta", "error_type",
            "is_mine", "clock_bucket", "phase"} <= cols
