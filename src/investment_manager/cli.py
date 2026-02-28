import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from . import analysis, pipeline


def _safe_echo(text: str) -> None:
    """Echo text, replacing un-encodable characters to avoid crashes on Windows."""
    encoded = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8", errors="replace"
    )
    typer.echo(encoded)

app = typer.Typer(help="Investment Manager — aggregate and analyze your positions.")

_DataDirOption = Annotated[
    Optional[Path],
    typer.Option(
        "--data-dir",
        help="Directory containing institution CSV exports.",
        show_default=True,
    ),
]


def _resolve_data_dir(data_dir: Optional[Path]) -> Path:
    return data_dir if data_dir is not None else pipeline._DEFAULT_DATA_DIR


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


class pl_options:
    """Context manager to set polars display options for CLI output."""

    def __enter__(self):
        import polars as pl
        pl.Config.set_tbl_rows(100)
        pl.Config.set_tbl_width_chars(120)
        return self

    def __exit__(self, *_):
        import polars as pl
        pl.Config.restore_defaults()
