import pytest

from gm import db as _db


@pytest.fixture
def conn(tmp_path):
    c = _db.connect(tmp_path / "test.sqlite")
    _db.init_db(c)
    return c


@pytest.fixture
def seeded(conn):
    conn.execute("""INSERT INTO games(uuid,color,result,time_class,eco,opening_name,
        accuracy_self,end_time) VALUES('gA','white','loss','bullet','C50','Italian Game',70.0,10)""")
    conn.execute("""INSERT INTO games(uuid,color,result,time_class,eco,opening_name,
        accuracy_self,end_time) VALUES('gB','black','win','bullet','B20','Sicilian Defense',88.0,20)""")

    def mv(g, ply, mine, sev, cat, delta, bucket, phase, san="Xx"):
        conn.execute("""INSERT INTO moves(game_uuid,ply,san,fen_before,eval_best_cp,best_move,
            eval_played_cp,winprob_delta,clock_ms,phase,clock_bucket,error_type,severity,is_mine)
            VALUES(?,?,?,'fen',0,'a1a1',0,?,1000,?,?,?,?,?)""",
                     (g, ply, san, delta, phase, bucket, cat, sev, mine))

    mv("gA", 5, 1, "blunder", "dropped_material", 0.4, "had_time", "opening")
    mv("gA", 7, 1, "mistake", "dropped_material", 0.15, "low_clock", "middlegame")
    mv("gA", 9, 1, "mistake", "endgame_conversion", 0.18, "had_time", "endgame")
    mv("gB", 4, 1, "blunder", "missed_tactic", 0.30, "had_time", "opening")
    mv("gB", 6, 0, "blunder", "dropped_material", 0.5, "had_time", "middlegame")
    conn.commit()
    return conn
