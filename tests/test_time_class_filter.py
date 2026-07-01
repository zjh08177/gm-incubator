"""The --time-class filter must scope every stat to one class (separate-per-class
profiles); with no class it stays whole-corpus (back-compat)."""
from gm import profile
from gm.stats import overview, queries, repertoire, weaknesses


def _mk(conn):
    conn.execute("""INSERT INTO games(uuid,color,result,time_class,opening_name,
        accuracy_self,end_time,my_rating)
        VALUES('b1','white','loss','bullet','Italian Game',70.0,10,1900)""")
    conn.execute("""INSERT INTO games(uuid,color,result,time_class,opening_name,
        accuracy_self,end_time,my_rating)
        VALUES('z1','black','win','blitz','French Defense',85.0,20,1600)""")

    def mv(g, ply, cat, delta, phase="middlegame", bucket="had_time"):
        conn.execute("""INSERT INTO moves(game_uuid,ply,san,fen_before,eval_best_cp,
            best_move,eval_played_cp,winprob_delta,clock_ms,phase,clock_bucket,
            error_type,severity,is_mine)
            VALUES(?,?,'Xx','fen',0,'a1a1',0,?,1000,?,?,?,'blunder',1)""",
                     (g, ply, delta, phase, bucket, cat))

    mv("b1", 5, "dropped_material", 0.4)
    mv("z1", 5, "missed_tactic", 0.3)
    conn.commit()
    return conn


def test_weaknesses_scoped_by_time_class(conn):
    _mk(conn)
    assert {r["category"] for r in weaknesses.rank(conn)} == {"dropped_material", "missed_tactic"}
    assert {r["category"] for r in weaknesses.rank(conn, time_class="bullet")} == {"dropped_material"}
    assert {r["category"] for r in weaknesses.rank(conn, time_class="blitz")} == {"missed_tactic"}
    assert weaknesses.rank(conn, time_class="rapid") == []


def test_had_time_and_time_class_compose(conn):
    _mk(conn)
    # low_clock bullet move must drop out under had_time even within the class
    conn.execute("""INSERT INTO moves(game_uuid,ply,san,fen_before,eval_best_cp,best_move,
        eval_played_cp,winprob_delta,clock_ms,phase,clock_bucket,error_type,severity,is_mine)
        VALUES('b1',7,'Xx','fen',0,'a1a1',0,0.2,50,'middlegame','low_clock',
               'dropped_material','mistake',1)""")
    conn.commit()
    got = weaknesses.rank(conn, had_time_only=True, time_class="bullet")
    dm = next(r for r in got if r["category"] == "dropped_material")
    assert dm["count"] == 1                       # low_clock one excluded


def test_repertoire_scoped_by_time_class(conn):
    _mk(conn)
    assert any(r["opening"] == "Italian Game" for r in repertoire.by_color(conn, "white"))
    assert repertoire.by_color(conn, "white", time_class="blitz") == []   # white game is bullet
    assert [r["opening"] for r in repertoire.by_color(conn, "black", time_class="blitz")] == ["French Defense"]


def test_find_positions_scoped(conn):
    _mk(conn)
    assert len(queries.find_positions(conn)) == 2
    assert len(queries.find_positions(conn, time_class="bullet")) == 1
    assert queries.find_positions(conn, time_class="rapid") == []


def test_overview_scoped_uses_per_class_rating(conn):
    _mk(conn)
    assert overview.summary(conn)["games"] == 2
    assert overview.summary(conn, time_class="bullet")["rating_latest"] == 1900
    assert overview.summary(conn, time_class="blitz")["rating_latest"] == 1600


def test_profile_scoped_header_and_counts(conn):
    _mk(conn)
    md_bullet = profile.build(conn, time_class="bullet")
    assert "Chess Profile (bullet)" in md_bullet
    assert "**1 games**" in md_bullet
    assert "**2 games**" in profile.build(conn)      # unscoped = whole corpus
