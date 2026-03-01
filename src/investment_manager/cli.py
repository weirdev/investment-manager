import logging
import sys
from pathlib import Path
from typing import Annotated, Optional

import polars as pl
import typer

from . import analysis, pipeline
from . import decomposition as decomp


def _total_line(df: pl.DataFrame) -> str:
    total = df.select(pl.col("value").sum()).item()
    return f"Total: ${total:,.2f}"


def _safe_echo(text: str) -> None:
    """Echo text, replacing un-encodable characters to avoid crashes on Windows."""
    encoded = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8", errors="replace"
    )
    typer.echo(encoded)

app = typer.Typer(help="Investment Manager — aggregate and analyze your positions.")


@app.callback()
def _app_callback(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging."),
    ] = False,
) -> None:
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_DataDirOption = Annotated[
    Optional[Path],
    typer.Option(
        "--data-dir",
        help="Directory containing institution CSV exports.",
        show_default=True,
    ),
]


def _resolve_data_dir(data_dir: Optional[Path]) -> Path:
    from .paths import DEFAULT_DATA_DIR
    return data_dir if data_dir is not None else DEFAULT_DATA_DIR


@app.command()
def positions(data_dir: _DataDirOption = None) -> None:
    """Print the aggregate position view grouped by ticker."""
    resolved = _resolve_data_dir(data_dir)
    df = pipeline.run(data_dir=resolved)
    if df.is_empty():
        typer.echo("No positions found.")
        raise typer.Exit(1)

    agg = analysis.aggregate_positions(df)
    with pl_options():
        _safe_echo(str(agg))
    _safe_echo(_total_line(df))


@app.command()
def concentration(data_dir: _DataDirOption = None) -> None:
    """Print portfolio concentration by asset class, market segment, region, and account type."""
    resolved = _resolve_data_dir(data_dir)
    df = pipeline.run(data_dir=resolved)
    if df.is_empty():
        typer.echo("No positions found.")
        raise typer.Exit(1)

    breakdown = analysis.concentration_breakdown(df)
    with pl_options():
        _safe_echo(str(breakdown))
    _safe_echo(_total_line(df))


@app.command()
def decomposition(
    data_dir: _DataDirOption = None,
    no_account_type: Annotated[
        bool,
        typer.Option("--no-account-type", help="Collapse across account types."),
    ] = False,
) -> None:
    """Print look-through concentration with composite funds split into components."""
    resolved = _resolve_data_dir(data_dir)
    df = pipeline.run(data_dir=resolved)
    if df.is_empty():
        typer.echo("No positions found.")
        raise typer.Exit(1)

    compositions = decomp.load_fund_compositions()
    decomposed = decomp.decompose(df, compositions)
    breakdown = analysis.concentration_breakdown(decomposed, group_by_account_type=not no_account_type)
    with pl_options():
        _safe_echo(str(breakdown))
    _safe_echo(_total_line(df))


@app.command()
def owners(data_dir: _DataDirOption = None) -> None:
    """Print the owner breakdown by portfolio share."""
    resolved = _resolve_data_dir(data_dir)
    df = pipeline.run(data_dir=resolved)
    if df.is_empty():
        typer.echo("No positions found.")
        raise typer.Exit(1)

    breakdown = analysis.owner_breakdown(df)
    with pl_options():
        _safe_echo(str(breakdown))
    _safe_echo(_total_line(df))


@app.command()
def precious_metals(data_dir: _DataDirOption = None) -> None:
    """Print precious metals holdings by account."""
    resolved = _resolve_data_dir(data_dir)
    df = pipeline.run(data_dir=resolved)
    if df.is_empty():
        typer.echo("No positions found.")
        raise typer.Exit(1)

    breakdown = analysis.precious_metals_by_account(df)
    if breakdown.is_empty():
        typer.echo("No precious metals positions found.")
        raise typer.Exit(1)

    with pl_options():
        _safe_echo(str(breakdown))
    metals_total = breakdown["value"].sum()
    _safe_echo(f"Precious metals total: ${metals_total:,.2f}")
    _safe_echo(_total_line(df))


@app.command()
def allocations(data_dir: _DataDirOption = None) -> None:
    """Print the allocation breakdown by account type and institution."""
    resolved = _resolve_data_dir(data_dir)
    df = pipeline.run(data_dir=resolved)
    if df.is_empty():
        typer.echo("No positions found.")
        raise typer.Exit(1)

    breakdown = analysis.allocation_breakdown(df)
    with pl_options():
        _safe_echo(str(breakdown))
    _safe_echo(_total_line(df))


@app.command()
def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    data_dir: _DataDirOption = None,
) -> None:
    """Start the web dashboard server."""
    import uvicorn

    from .server import create_app

    resolved = _resolve_data_dir(data_dir)
    typer.echo(f"Starting server at http://{host}:{port}")
    uvicorn.run(create_app(data_dir=resolved), host=host, port=port)


class pl_options:
    """Context manager to set polars display options for CLI output."""

    def __enter__(self):
        pl.Config.set_tbl_rows(100)
        pl.Config.set_tbl_width_chars(120)
        return self

    def __exit__(self, *_):
        pl.Config.restore_defaults()
