import typer

app = typer.Typer(help="gm — local chess knowledge base + coach", no_args_is_help=True)


@app.command()
def version():
    """Print version."""
    typer.echo("gm 0.1.0")


if __name__ == "__main__":
    app()
