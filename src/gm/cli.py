import json as _json

import typer

from gm import config, db as _db, report
from gm.stats import overview, queries, repertoire, weaknesses

app = typer.Typer(help="gm — local chess knowledge base + coach", no_args_is_help=True)


def _conn(db):
    c = _db.connect(db or config.db_path())
    _db.init_db(c)
    return c


@app.command()
def version():
    """Print version."""
    typer.echo("gm 0.1.0")


@app.command()
def sync(username: str, time_class: str = "bullet", max_games: int = typer.Option(None),
         full: bool = False, depth: int = 12, workers: int = 1,
         since: str = typer.Option(None, help="floor the window, YYYY-MM (parallel only)"),
         db: str = typer.Option(None)):
    """Fetch + analyze games from Chess.com into the local KB.

    workers>1 fans engine analysis across threads (each its own Stockfish);
    re-runs skip whole already-synced months via the stored watermark."""
    import httpx
    from gm import sync as sync_mod
    from gm.analysis.engine import Analyzer
    since_ym = tuple(int(x) for x in since.split("-")) if since else None
    c = _conn(db)
    try:
        if workers > 1:
            res = sync_mod.sync_parallel(c, username, time_class, depth=depth,
                                         workers=workers, max_games=max_games,
                                         full=full, progress=200, since_ym=since_ym)
        else:
            with Analyzer(depth=depth) as a:
                res = sync_mod.sync(c, username, time_class, a,
                                    max_games=max_games, full=full)
    except RuntimeError as e:                       # stockfish missing
        typer.secho(str(e), fg="red")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        msg = (f"Chess.com user '{username}' not found."
               if code == 404 else f"Chess.com API error {code}.")
        typer.secho(msg, fg="red")
        raise typer.Exit(1)
    typer.echo(_json.dumps(res, indent=2))


@app.command(name="backfill-openings")
def backfill_openings_cmd(db: str = typer.Option(None)):
    """Populate human opening names from stored PGNs (no re-fetch, no re-analyze)."""
    from gm import sync as sync_mod
    res = sync_mod.backfill_openings(_conn(db))
    typer.echo(f"opening names: {res['updated']}/{res['total']} updated")


@app.command()
def stats(db: str = typer.Option(None), json: bool = typer.Option(False, "--json")):
    """Corpus overview."""
    typer.echo(_json.dumps(overview.summary(_conn(db)), indent=2))


@app.command(name="weaknesses")
def weaknesses_cmd(db: str = typer.Option(None), json: bool = typer.Option(False, "--json"),
                   md: bool = typer.Option(False, "--md"),
                   had_time: bool = typer.Option(False, "--had-time")):
    """Ranked recurring weaknesses."""
    c = _conn(db)
    ranked = weaknesses.rank(c, had_time_only=had_time)
    if md:
        typer.echo(report.weaknesses_md(ranked, weaknesses.rank(c, had_time_only=True)))
    else:
        typer.echo(_json.dumps(ranked, indent=2))


@app.command(name="repertoire")
def repertoire_cmd(db: str = typer.Option(None), json: bool = typer.Option(False, "--json"),
                   md: bool = typer.Option(False, "--md"),
                   group: str = typer.Option("opening", help="opening | family")):
    """Opening repertoire by color."""
    c = _conn(db)
    w, b = repertoire.by_color(c, "white", group), repertoire.by_color(c, "black", group)
    if md:
        typer.echo(report.repertoire_md(w, b))
    else:
        typer.echo(_json.dumps({"white": w, "black": b}, indent=2))


@app.command()
def game(uuid: str, db: str = typer.Option(None)):
    """Per-move review of one game."""
    typer.echo(_json.dumps(queries.one_game(_conn(db), uuid), indent=2))


@app.command(name="search-games")
def search_games(result: str = typer.Option(None), opening: str = typer.Option(None),
                 color: str = typer.Option(None), db: str = typer.Option(None)):
    """Filtered game list."""
    typer.echo(_json.dumps(queries.search_games(_conn(db), result, opening, color), indent=2))


@app.command(name="find-positions")
def find_positions(error_type: str = typer.Option(None), phase: str = typer.Option(None),
                   min_delta: float = 0.0, had_time: bool = typer.Option(False, "--had-time"),
                   db: str = typer.Option(None)):
    """Positions matching error/phase/clock filters."""
    typer.echo(_json.dumps(queries.find_positions(
        _conn(db), error_type, phase, min_delta, had_time), indent=2))


@app.command()
def accept(db: str = typer.Option(None)):
    """L5 gate: our analysis vs Chess.com accuracies (+ shuffle control)."""
    from gm import accept as acc
    typer.echo(_json.dumps(acc.correlate(_conn(db)), indent=2))


@app.command()
def profile(db: str = typer.Option(None), out: str = typer.Option(None)):
    """Full player profile (markdown): rating, repertoire, weaknesses, blunders."""
    from gm import profile as prof
    md = prof.build(_conn(db))
    if out:
        from pathlib import Path
        Path(out).write_text(md)
        typer.echo(f"wrote {out}")
    else:
        typer.echo(md)


if __name__ == "__main__":
    app()
