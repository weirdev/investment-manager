from pathlib import Path

import polars as pl

from .paths import DEFAULT_COMPOSITIONS_PATH as _DEFAULT_COMPOSITIONS_PATH

_COMPOSITIONS_SCHEMA = {
    "canonical_ticker": pl.Utf8,
    "asset_class": pl.Utf8,
    "market_segment": pl.Utf8,
    "region": pl.Utf8,
    "fraction": pl.Float64,
}


def load_fund_compositions(path: Path = _DEFAULT_COMPOSITIONS_PATH) -> pl.DataFrame:
    if not path.exists():
        return pl.DataFrame(schema=_COMPOSITIONS_SCHEMA)
    return pl.read_csv(path, schema_overrides=_COMPOSITIONS_SCHEMA)


def decompose(df: pl.DataFrame, compositions: pl.DataFrame) -> pl.DataFrame:
    """Expand composite positions into component rows weighted by fraction.

    Positions whose canonical_ticker has no composition entry are passed through
    unchanged. The total value across all output rows equals the total input value
    (assuming fractions sum to 1.0 per ticker).
    """
    if df.is_empty() or compositions.is_empty():
        return df

    composite_tickers = compositions["canonical_ticker"].unique().to_list()
    atomic = df.filter(~pl.col("canonical_ticker").is_in(composite_tickers))
    composite = df.filter(pl.col("canonical_ticker").is_in(composite_tickers))

    if composite.is_empty():
        return df

    expanded = (
        composite
        .join(compositions, on="canonical_ticker", how="left", suffix="_comp")
        .with_columns([
            (pl.col("value") * pl.col("fraction")).alias("value"),
            pl.col("asset_class_comp").alias("asset_class"),
            pl.col("market_segment_comp").alias("market_segment"),
            pl.col("region_comp").alias("region"),
        ])
        .drop(["asset_class_comp", "market_segment_comp", "region_comp", "fraction"])
    )

    return pl.concat([atomic, expanded])
