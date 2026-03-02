import polars as pl


def aggregate_positions(df: pl.DataFrame, by_retirement: bool = False) -> pl.DataFrame:
    """Group by ticker; show total value and per-account breakdown."""
    if df.is_empty():
        return df

    total_by_ticker = (
        df.group_by("ticker")
        .agg(pl.col("value").sum().alias("total_value"))
        .sort("total_value", descending=True)
    )

    acct_col = "is_retirement" if by_retirement else "account_type"
    breakdown = (
        df.select(["ticker", "institution_name", "account_name", acct_col, "value"])
        .sort(["ticker", "institution_name", "account_name"])
    )

    return total_by_ticker.join(breakdown, on="ticker", how="left").sort(
        "total_value", descending=True
    )


def concentration_breakdown(
    df: pl.DataFrame, group_by_account_type: bool = True, by_retirement: bool = False
) -> pl.DataFrame:
    """Group by asset_class, market_segment, region, account_type; show value and % of total."""
    if df.is_empty():
        return df

    total = df.select(pl.col("value").sum()).item()

    group_cols = ["asset_class", "market_segment", "region"]
    if by_retirement:
        group_cols.append("is_retirement")
    elif group_by_account_type:
        group_cols.append("account_type")

    return (
        df.group_by(group_cols)
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


def precious_metals_by_account(df: pl.DataFrame, by_retirement: bool = False) -> pl.DataFrame:
    """Filter to precious metals positions; group by account and ticker."""
    metals = df.filter(pl.col("asset_class") == "precious_metals")
    if metals.is_empty():
        return metals

    total = df.select(pl.col("value").sum()).item()

    acct_col = "is_retirement" if by_retirement else "account_type"
    return (
        metals.group_by(["institution_name", "account_name", acct_col, "ticker"])
        .agg(pl.col("value").sum())
        .with_columns(
            (pl.col("value") / total * 100).round(2).alias("pct_of_portfolio")
        )
        .sort(["institution_name", "account_name", "value"], descending=[False, False, True])
    )


def allocation_breakdown(df: pl.DataFrame, by_retirement: bool = False) -> pl.DataFrame:
    """Group by account_type and institution_name; show value and % of total."""
    if df.is_empty():
        return df

    total = df.select(pl.col("value").sum()).item()

    acct_col = "is_retirement" if by_retirement else "account_type"
    result = (
        df.group_by([acct_col, "institution_name"])
        .agg(pl.col("value").sum().alias("total_value"))
        .with_columns(
            (pl.col("total_value") / total * 100).round(2).alias("pct_of_portfolio")
        )
        .sort("total_value", descending=True)
    )
    return result
