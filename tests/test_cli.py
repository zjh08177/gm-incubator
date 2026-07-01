import json

from typer.testing import CliRunner

from gm import db as _db
from gm.cli import app

runner = CliRunner()


def _seed_file(tmp_path):
    p = tmp_path / "cli.sqlite"
    c = _db.connect(p)
    _db.init_db(c)
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


def test_time_class_option_scopes_stats(tmp_path):
    p = _seed_file(tmp_path)                       # one bullet game
    c = _db.connect(p)
    c.execute("""INSERT INTO games(uuid,color,result,time_class,opening_name,end_time,my_rating)
                 VALUES('z1','black','win','blitz','French Defense',20,1600)""")
    c.commit()
    allc = json.loads(runner.invoke(app, ["stats", "--db", str(p), "--json"]).stdout)
    assert allc["games"] == 2
    scoped = json.loads(runner.invoke(
        app, ["stats", "--db", str(p), "--json", "--time-class", "bullet"]).stdout)
    assert scoped["games"] == 1 and list(scoped["by_time_class"]) == ["bullet"]


def test_sync_missing_stockfish_is_clean_error(tmp_path, monkeypatch):
    from gm import config
    monkeypatch.setattr(config, "stockfish_path", lambda: None)
    monkeypatch.delenv("STOCKFISH_PATH", raising=False)
    res = runner.invoke(app, ["sync", "someuser", "--db", str(tmp_path / "s.sqlite")])
    assert res.exit_code == 1
    assert "tockfish" in res.output          # clean message, not a traceback
