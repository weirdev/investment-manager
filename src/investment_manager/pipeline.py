import warnings
from pathlib import Path

import polars as pl

from .enrichment import enrich, load_asset_mapping, load_asset_metadata
from .models import Position
from .parsers.base import InstitutionParser
from .parsers.fidelity import FidelityParser
from .parsers.schwab import SchwabParser
from .registry import AccountRegistry

_DEFAULT_DATA_DIR = Path(__file__).parents[2] / "personal_data" / "raw_account_details"

# All known parsers — add new ones here
_PARSERS: list[type[InstitutionParser]] = [FidelityParser, SchwabParser]


def _get_parser(file_path: Path, registry: AccountRegistry) -> InstitutionParser | None:
    for parser_cls in _PARSERS:
        if parser_cls.can_parse(file_path):
            return parser_cls(registry=registry)  # type: ignore[call-arg]
    return None


def run(
    data_dir: Path = _DEFAULT_DATA_DIR,
    registry: AccountRegistry | None = None,
) -> pl.DataFrame:
    """Discover CSVs, parse each, validate, and return a merged DataFrame."""
    if registry is None:
        registry = AccountRegistry()

    csv_files = list(data_dir.rglob("*.csv"))
    if not csv_files:
        warnings.warn(f"No CSV files found in {data_dir}", stacklevel=2)

    all_positions: list[Position] = []
    for csv_file in csv_files:
        parser = _get_parser(csv_file, registry)
        if parser is None:
            warnings.warn(
                f"No parser found for {csv_file.name}; skipping.", stacklevel=2
            )
            continue
        positions = parser.parse(csv_file)
        all_positions.extend(positions)

    if not all_positions:
        return pl.DataFrame(
            schema={
                "institution_name": pl.Utf8,
                "account_name": pl.Utf8,
                "account_type": pl.Utf8,
                "ticker": pl.Utf8,
                "value": pl.Float64,
            }
        )

    df = pl.DataFrame(
        [
            {
                "institution_name": p.institution_name,
                "account_name": p.account_name,
                "account_type": p.account_type,
                "ticker": p.ticker,
                "value": p.value,
            }
            for p in all_positions
        ]
    )
    return enrich(df, load_asset_mapping(), load_asset_metadata())
