from pathlib import Path

import polars as pl

from .paths import DEFAULT_METADATA_PATH as _DEFAULT_METADATA_PATH

_MAPPING_SCHEMA = {
    "account_type": pl.Utf8,
    "raw_ticker": pl.Utf8,
    "canonical_ticker": pl.Utf8,
}

_METADATA_SCHEMA = {
    "canonical_ticker": pl.Utf8,
    "asset_class": pl.Utf8,
    "security_type": pl.Utf8,
    "market_segment": pl.Utf8,
    "region": pl.Utf8,
}


def load_asset_mapping(paths: list[Path] = []) -> pl.DataFrame:
    frames = [pl.read_csv(p, schema_overrides=_MAPPING_SCHEMA) for p in paths if p.exists()]
    if not frames:
        return pl.DataFrame(schema=_MAPPING_SCHEMA)
    return pl.concat(frames).unique(subset=["account_type", "raw_ticker"], keep="first")


def load_asset_metadata(path: Path = _DEFAULT_METADATA_PATH) -> pl.DataFrame:
    if not path.exists():
        return pl.DataFrame(schema=_METADATA_SCHEMA)
    return pl.read_csv(path, schema_overrides=_METADATA_SCHEMA)


def enrich(
    df: pl.DataFrame,
    asset_mapping: pl.DataFrame,
    asset_metadata: pl.DataFrame,
) -> pl.DataFrame:
    """Join asset mapping and metadata onto positions DataFrame."""
    # Step 1: resolve canonical_ticker via (account_type, raw_ticker) mapping
    enriched = df.join(
        asset_mapping.select(["account_type", "raw_ticker", "canonical_ticker"]),
        left_on=["account_type", "ticker"],
        right_on=["account_type", "raw_ticker"],
        how="left",
    ).with_columns(
        pl.when(pl.col("canonical_ticker").is_null())
        .then(pl.col("ticker").str.strip_chars_end("*"))
        .otherwise(pl.col("canonical_ticker"))
        .alias("canonical_ticker")
    )

    # Step 2: join metadata by canonical_ticker
    enriched = enriched.join(
        asset_metadata.select(
            ["canonical_ticker", "asset_class", "security_type", "market_segment", "region"]
        ),
        on="canonical_ticker",
        how="left",
    ).with_columns(
        pl.col("asset_class").fill_null("unknown"),
        pl.col("security_type").fill_null("unknown"),
        pl.col("market_segment").fill_null("unknown"),
        pl.col("region").fill_null("unknown"),
    )

    return enriched
