import logging
import re
import warnings
from pathlib import Path

import polars as pl

from .enrichment import enrich, load_asset_mapping, load_asset_metadata
from .models import Position
from .parsers.alight import AlightParser
from .parsers.base import InstitutionParser
from .parsers.fidelity import FidelityParser
from .parsers.interactive_brokers import InteractiveBrokersParser
from .parsers.schwab import SchwabParser
from .paths import DEFAULT_DATA_DIR as _DEFAULT_DATA_DIR
from .paths import DEFAULT_DATA_PATHS, DataPaths
from .registry import AccountRegistry

logger = logging.getLogger(__name__)

# All known parsers — add new ones here
_PARSERS: list[type[InstitutionParser]] = [FidelityParser, SchwabParser, InteractiveBrokersParser, AlightParser]

# Raw exports must be named "<YYYY-MM-DD>_<rest-of-filename>.csv" — the leading
# datestamp is the export date and is the sole signal the pipeline uses to decide
# which file is current when a directory holds more than one export.
_EXPORT_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[_-]")


class MissingExportDateError(ValueError):
    """A raw export CSV is missing its required leading YYYY-MM-DD datestamp."""


class AmbiguousExportDateError(ValueError):
    """Two or more exports in the same directory share the same leading datestamp."""


def _export_date(csv_file: Path) -> str:
    match = _EXPORT_DATE_PREFIX_RE.match(csv_file.name)
    if not match:
        raise MissingExportDateError(
            f"{csv_file} has no leading YYYY-MM-DD datestamp. Raw exports must be "
            f"named '<YYYY-MM-DD>_<original-filename>' (the date the export was "
            f"generated) so the pipeline can tell which export in a directory is "
            f"current. Rename the file and re-run."
        )
    return match.group(1)


def _latest_export_per_directory(csv_files: list[Path]) -> list[Path]:
    """Keep only the most-recently-dated CSV (by filename datestamp) in each directory.

    Institution export directories (``<owner>/<institution>/``) are expected to hold
    at most one *current* export at a time. If an older export is left behind after a
    fresh one is dropped in, it's superseded and ignored rather than merged in —
    merging would let stale values silently override fresh ones, or leave positions
    for since-sold tickers lingering forever. Freshness is determined purely from
    each filename's leading datestamp (not file mtime, which doesn't survive copies,
    git checkouts, or backups) — see ``_export_date``.
    """
    by_dir: dict[Path, list[Path]] = {}
    for csv_file in csv_files:
        by_dir.setdefault(csv_file.parent, []).append(csv_file)

    kept: list[Path] = []
    for directory, files in by_dir.items():
        dated = sorted(((_export_date(f), f) for f in files), key=lambda pair: pair[0], reverse=True)
        if len(dated) == 1:
            kept.append(dated[0][1])
            continue

        newest_date = dated[0][0]
        tied = [f for date, f in dated if date == newest_date]
        if len(tied) > 1:
            raise AmbiguousExportDateError(
                f"{directory} has {len(tied)} exports all dated {newest_date}: "
                f"{', '.join(f.name for f in tied)}. Rename or remove one so the "
                f"newest export is unambiguous."
            )

        newest_file = dated[0][1]
        superseded = [f for _, f in dated[1:]]
        kept.append(newest_file)
        warnings.warn(
            f"{directory} contains {len(files)} exports; using the newest "
            f"({newest_file.name}, dated {newest_date}) and ignoring superseded "
            f"file(s): {', '.join(f.name for f in superseded)}. Remove old exports "
            f"once a fresh one is in place to avoid this warning.",
            stacklevel=3,
        )
    return kept


def _get_parser(file_path: Path, registry: AccountRegistry) -> InstitutionParser | None:
    for parser_cls in _PARSERS:
        if parser_cls.can_parse(file_path):
            return parser_cls(registry=registry)  # type: ignore[call-arg]
    return None


def run(
    data_dir: Path = _DEFAULT_DATA_DIR,
    data_paths: DataPaths | None = None,
    registry: AccountRegistry | None = None,
    anonymize: bool = False,
) -> pl.DataFrame:
    """Discover CSVs, parse each, validate, and return a merged DataFrame."""
    if data_paths is None:
        data_paths = DataPaths.from_data_dir(data_dir) if data_dir != _DEFAULT_DATA_DIR else DEFAULT_DATA_PATHS

    if registry is None:
        registry = AccountRegistry(data_paths=data_paths)

    csv_files = list(data_paths.raw_account_details_dir.rglob("*.csv"))
    logger.info("Discovered %d CSV file(s) in %s", len(csv_files), data_paths.raw_account_details_dir)
    if not csv_files:
        warnings.warn(f"No CSV files found in {data_paths.raw_account_details_dir}", stacklevel=2)

    csv_files = _latest_export_per_directory(csv_files)

    all_positions: list[Position] = []
    for csv_file in csv_files:
        parser = _get_parser(csv_file, registry)
        if parser is None:
            warnings.warn(
                f"No parser found for {csv_file.name}; skipping.", stacklevel=2
            )
            continue
        logger.info("Parsing %s with %s", csv_file.name, type(parser).__name__)
        positions = parser.parse(csv_file)
        logger.info("Parsed %d position(s) from %s", len(positions), csv_file.name)
        all_positions.extend(positions)

    seen: set[tuple[str, str, str]] = set()
    deduped: list[Position] = []
    for pos in all_positions:
        key = (pos.institution_name, pos.account_number, pos.ticker)
        if key not in seen:
            seen.add(key)
            deduped.append(pos)
    logger.info("Deduplication: %d → %d position(s)", len(all_positions), len(deduped))
    all_positions = deduped

    if not all_positions:
        return pl.DataFrame(
            schema={
                "institution_name": pl.Utf8,
                "account_name": pl.Utf8,
                "account_number": pl.Utf8,
                "account_type": pl.Utf8,
                "owner": pl.Utf8,
                "is_retirement": pl.Boolean,
                "ticker": pl.Utf8,
                "value": pl.Float64,
                "canonical_ticker": pl.Utf8,
                "asset_class": pl.Utf8,
                "security_type": pl.Utf8,
                "market_segment": pl.Utf8,
                "region": pl.Utf8,
            }
        )

    df = pl.DataFrame(
        [
            {
                "institution_name": p.institution_name,
                "account_name": p.account_name,
                "account_number": p.account_number,
                "account_type": p.account_type,
                "owner": p.owner,
                "is_retirement": p.is_retirement,
                "ticker": p.ticker,
                "value": p.value,
            }
            for p in all_positions
        ]
    )
    mapping_paths = data_paths.discover_mapping_paths()
    df = enrich(df, load_asset_mapping(mapping_paths), load_asset_metadata(data_paths.metadata_path))
    if anonymize:
        total = df["value"].sum()
        if total > 0:
            df = df.with_columns(
                (pl.col("value") * (100_000.0 / total)).clip(lower_bound=0.01)
            )
    return df
