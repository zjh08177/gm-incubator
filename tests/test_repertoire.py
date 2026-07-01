from gm import db as _db
from gm.stats import repertoire


def test_family_rollup_merges_variations(tmp_path):
    conn = _db.connect(tmp_path / "t.sqlite")
    _db.init_db(conn)
    for uuid, name, res in [("a", "Sicilian Defense Smith-Morra Gambit Accepted", "win"),
                            ("b", "Sicilian Defense Open", "loss")]:
        conn.execute("INSERT INTO games(uuid,color,result,eco,opening_name) VALUES(?,?,?,?,?)",
                     (uuid, "white", res, "B21", name))
    conn.commit()
    assert len(repertoire.by_color(conn, "white", "opening")) == 2   # distinct variations
    fam = repertoire.by_color(conn, "white", "family")
    assert len(fam) == 1 and fam[0]["opening"] == "Sicilian Defense" and fam[0]["games"] == 2


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
