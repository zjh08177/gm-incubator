from gm import db as _db, sync


def test_backfill_openings_from_ecourl(tmp_path):
    conn = _db.connect(tmp_path / "t.sqlite")
    _db.init_db(conn)
    conn.execute("INSERT INTO games(uuid,color,result,pgn) VALUES(?,?,?,?)",
                 ("g1", "white", "win",
                  '[ECOUrl "https://www.chess.com/openings/Scotch-Game-4.Nxd4"]\n\n1. e4 *'))
    conn.execute("INSERT INTO games(uuid,color,result,pgn) VALUES(?,?,?,?)",
                 ("g2", "black", "loss", '[ECO "C00"]\n\n1. e4 *'))   # no ECOUrl -> untouched
    conn.commit()
    res = sync.backfill_openings(conn)
    assert res == {"updated": 1, "total": 2}
    assert conn.execute("SELECT opening_name FROM games WHERE uuid='g1'").fetchone()[0] == "Scotch Game"
    assert conn.execute("SELECT opening_name FROM games WHERE uuid='g2'").fetchone()[0] is None
