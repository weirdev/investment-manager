import polars as pl


def aggregate_positions(df: pl.DataFrame) -> pl.DataFrame:
    """Group by ticker; show total value and per-account breakdown."""
    if df.is_empty():
        return df

    total_by_ticker = (
        df.group_by("ticker")
        .agg(pl.col("value").sum().alias("total_value"))
        .sort("total_value", descending=True)
    )

    breakdown = (
        df.select(["ticker", "institution_name", "account_name", "account_type", "value"])
        .sort(["ticker", "institution_name", "account_name"])
    )

    return total_by_ticker.join(breakdown, on="ticker", how="left").sort(
        "total_value", descending=True
    )


def concentration_breakdown(df: pl.DataFrame) -> pl.DataFrame:
    """Group by asset_class, market_segment, region, account_type; show value and % of total."""
    if df.is_empty():
        return df

    total = df.select(pl.col("value").sum()).item()

    return (
        df.group_by(["asset_class", "market_segment", "region", "account_type"])
        .agg(pl.col("value").sum())
        .with_columns(
            (pl.col("value") / total * 100).round(2).alias("pct_of_portfolio")
        )
        .sort(["asset_class", "value"], descending=[False, True])
    )


def owner_breakdown(df: pl.DataFrame) -> pl.DataFrame:
    """Group by owner; show total value and % of portfolio, sorted descending."""
    if df.is_empty():
        return df

    total = df.select(pl.col("value").sum()).item()

    return (
        df.group_by("owner")
        .agg(pl.col("value").sum().alias("total_value"))
        .with_columns(
            (pl.col("total_value") / total * 100).round(2).alias("pct_of_portfolio")
        )
        .sort("total_value", descending=True)
    )


def allocation_breakdown(df: pl.DataFrame) -> pl.DataFrame:
    """Group by account_type and institution_name; show value and % of total."""
    if df.is_empty():
        return df

    total = df.select(pl.col("value").sum()).item()

    result = (
        df.group_by(["account_type", "institution_name"])
        .agg(pl.col("value").sum().alias("total_value"))
        .with_columns(
            (pl.col("total_value") / total * 100).round(2).alias("pct_of_portfolio")
        )
        .sort("total_value", descending=True)
    )
    return result
