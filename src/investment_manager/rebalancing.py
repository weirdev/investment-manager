from pathlib import Path

import polars as pl

from .paths import DEFAULT_MARKET_WEIGHTS_PATH as _DEFAULT_MARKET_WEIGHTS_PATH

_MARKET_WEIGHTS_SCHEMA = {
    "region": pl.Utf8,
    "market_segment": pl.Utf8,
    "weight": pl.Float64,
}

# The three developed-market cap tiers. Emerging markets is treated as its own tier
# regardless of company size, so it is not in this list.
_DEV_TIERS = ["large_cap", "mid_cap", "small_cap"]

# Fixed display order for the flat cap-tier comparison.
_TIERS = ["large_cap", "mid_cap", "small_cap", "emerging"]

# Fixed display order for the region x cap-tier grid.
_CELLS = [
    ("us", "large_cap"),
    ("us", "mid_cap"),
    ("us", "small_cap"),
    ("ex_us", "large_cap"),
    ("ex_us", "mid_cap"),
    ("ex_us", "small_cap"),
    ("emerging", "emerging"),
]

_COMPARISON_SCHEMA = {
    "market_cap_tier": pl.Utf8,
    "portfolio_pct": pl.Float64,
    "market_pct": pl.Float64,
    "drift_pct": pl.Float64,
}
_REGION_COMPARISON_SCHEMA = {
    "region": pl.Utf8,
    "market_cap_tier": pl.Utf8,
    "portfolio_pct": pl.Float64,
    "market_pct": pl.Float64,
    "drift_pct": pl.Float64,
}


def load_market_weights(path: Path = _DEFAULT_MARKET_WEIGHTS_PATH) -> pl.DataFrame:
    """Load the committed global market-cap benchmark. Empty schema frame if missing."""
    if not path.exists():
        return pl.DataFrame(schema=_MARKET_WEIGHTS_SCHEMA)
    return pl.read_csv(path, schema_overrides=_MARKET_WEIGHTS_SCHEMA)


def equity_sleeve_total(df: pl.DataFrame) -> float:
    """Total value of the equities asset class (0.0 if none / empty)."""
    if df.is_empty():
        return 0.0
    equities = df.filter(pl.col("asset_class") == "equities")
    if equities.is_empty():
        return 0.0
    return float(equities.select(pl.col("value").sum()).item() or 0.0)


# ── shared helpers ──────────────────────────────────────────────────────────


def _norm(col: str) -> pl.Expr:
    return pl.col(col).fill_null("").str.to_lowercase().str.strip_chars()


def _equities_or_none(df: pl.DataFrame, market_weights: pl.DataFrame) -> pl.DataFrame | None:
    if df.is_empty() or market_weights.is_empty():
        return None
    equities = df.filter(pl.col("asset_class") == "equities")
    if equities.is_empty() or not equities.select(pl.col("value").sum()).item():
        return None
    return equities


def _finalize(
    portfolio: pl.DataFrame,
    market: pl.DataFrame,
    key_cols: list[str],
    order_frame: pl.DataFrame,
    extra_cols: list[str],
) -> pl.DataFrame:
    """Join benchmark %, compute drift from the rounded columns, apply fixed ordering."""
    return (
        portfolio.join(market, on=key_cols, how="left")
        .with_columns(
            (pl.col("portfolio_pct") - pl.col("market_pct")).round(2).alias("drift_pct")
        )
        .join(order_frame, on=key_cols, how="left")
        .sort([*extra_cols, "_order"], descending=[*([True] * len(extra_cols)), False])
        .drop("_order")
        .select(*extra_cols, *key_cols, "portfolio_pct", "market_pct", "drift_pct")
    )


def _compare(
    equities: pl.DataFrame,
    market: pl.DataFrame,
    base: pl.DataFrame,
    key_cols: list[str],
    order_frame: pl.DataFrame,
    totals_fn,
    by_retirement: bool,
    empty_schema: dict,
) -> pl.DataFrame:
    """Bucket the equity sleeve via ``totals_fn`` and compare it to ``market``.

    ``totals_fn(sleeve)`` returns a frame of ``key_cols + [value]``. With
    ``by_retirement`` the sleeve is split on ``is_retirement`` and each half is
    renormalized independently.
    """

    def sleeve_pct(sleeve: pl.DataFrame, sleeve_total: float) -> pl.DataFrame:
        return (
            base.join(totals_fn(sleeve), on=key_cols, how="left")
            .with_columns(pl.col("value").fill_null(0.0))
            .with_columns((pl.col("value") / sleeve_total * 100).round(2).alias("portfolio_pct"))
            .select(*key_cols, "portfolio_pct")
        )

    if by_retirement and "is_retirement" in equities.columns:
        sleeves: list[pl.DataFrame] = []
        for is_retirement in (True, False):
            sleeve = equities.filter(pl.col("is_retirement") == is_retirement)
            sleeve_total = (
                sleeve.select(pl.col("value").sum()).item() if not sleeve.is_empty() else 0.0
            )
            if not sleeve_total:
                continue
            sleeves.append(
                sleeve_pct(sleeve, sleeve_total).with_columns(
                    pl.lit(is_retirement).alias("is_retirement")
                )
            )
        if not sleeves:
            return pl.DataFrame(schema=empty_schema)
        return _finalize(pl.concat(sleeves), market, key_cols, order_frame, ["is_retirement"])

    total = equities.select(pl.col("value").sum()).item()
    return _finalize(sleeve_pct(equities, total), market, key_cols, order_frame, [])


# ── cap-tier comparison ─────────────────────────────────────────────────────


def _developed_ratios(market_weights: pl.DataFrame) -> pl.DataFrame | None:
    """Benchmark developed-market tier weights, normalized per region and combined.

    Returns ``[_region_class, market_cap_tier, ratio]`` where ``_region_class`` is
    ``us`` / ``ex_us`` / ``combined`` and ``ratio`` sums to 1.0 within each class.
    ``None`` if the benchmark carries no developed cap-tier detail.
    """
    dev = market_weights.filter(
        _norm("region").is_in(["us", "ex_us"]) & _norm("market_segment").is_in(_DEV_TIERS)
    ).select(
        _norm("region").alias("_region_class"),
        _norm("market_segment").alias("market_cap_tier"),
        pl.col("weight"),
    )
    if dev.is_empty():
        return None

    per_region = (
        dev.group_by(["_region_class", "market_cap_tier"])
        .agg(pl.col("weight").sum())
        .with_columns(
            (pl.col("weight") / pl.col("weight").sum().over("_region_class")).alias("ratio")
        )
        .select("_region_class", "market_cap_tier", "ratio")
    )
    combined = (
        dev.group_by("market_cap_tier")
        .agg(pl.col("weight").sum())
        .with_columns(
            pl.lit("combined").alias("_region_class"),
            (pl.col("weight") / pl.col("weight").sum()).alias("ratio"),
        )
        .select("_region_class", "market_cap_tier", "ratio")
    )
    return pl.concat([per_region, combined])


def _tier_totals(
    equities: pl.DataFrame, ratios: pl.DataFrame, region_classes: list[str]
) -> pl.DataFrame:
    """Bucket an equities frame into the four cap tiers, redistributing unresolved value."""
    classified = equities.with_columns(
        _norm("market_segment").alias("_seg"),
        _norm("region").alias("_reg"),
    ).with_columns(
        pl.when(pl.col("_reg") == "emerging")
        .then(pl.lit("emerging"))
        .when(pl.col("_seg").is_in(_DEV_TIERS))
        .then(pl.col("_seg"))
        .otherwise(pl.lit("__residual__"))
        .alias("_tier"),
        pl.when(pl.col("_reg") == "us")
        .then(pl.lit("us"))
        .when(pl.col("_reg") == "ex_us")
        .then(pl.lit("ex_us"))
        .otherwise(pl.lit("combined"))
        .alias("_region_class"),
    )

    resolved = classified.filter(pl.col("_tier") != "__residual__").select(
        pl.col("_tier").alias("market_cap_tier"), pl.col("value")
    )

    residual = (
        classified.filter(pl.col("_tier") == "__residual__")
        .group_by("_region_class")
        .agg(pl.col("value").sum().alias("_residual_value"))
        .with_columns(
            pl.when(pl.col("_region_class").is_in(region_classes))
            .then(pl.col("_region_class"))
            .otherwise(pl.lit("combined"))
            .alias("_region_class")
        )
        .group_by("_region_class")
        .agg(pl.col("_residual_value").sum())
    )
    redistributed = residual.join(ratios, on="_region_class", how="inner").select(
        pl.col("market_cap_tier"),
        (pl.col("_residual_value") * pl.col("ratio")).alias("value"),
    )

    return pl.concat([resolved, redistributed]).group_by("market_cap_tier").agg(
        pl.col("value").sum()
    )


def _benchmark_tier_pct(market_weights: pl.DataFrame, base: pl.DataFrame) -> pl.DataFrame:
    """Collapse the benchmark to the four display tiers and renormalize to 100%."""
    market_tiered = (
        market_weights.with_columns(
            pl.when(_norm("region") == "emerging")
            .then(pl.lit("emerging"))
            .when(_norm("market_segment").is_in(_DEV_TIERS))
            .then(_norm("market_segment"))
            .otherwise(pl.lit("__other__"))
            .alias("market_cap_tier")
        )
        .filter(pl.col("market_cap_tier") != "__other__")
        .group_by("market_cap_tier")
        .agg(pl.col("weight").sum())
    )
    market_total = market_tiered.select(pl.col("weight").sum()).item()
    return (
        base.join(market_tiered, on="market_cap_tier", how="left")
        .with_columns(pl.col("weight").fill_null(0.0))
        .with_columns((pl.col("weight") / market_total * 100).round(2).alias("market_pct"))
        .select("market_cap_tier", "market_pct")
    )


def market_cap_comparison(
    df: pl.DataFrame, market_weights: pl.DataFrame, by_retirement: bool = False
) -> pl.DataFrame:
    """Compare the equity sleeve's market-cap tier mix to a global market-cap benchmark.

    ``df`` is expected to be an already look-through-decomposed positions frame. Only
    ``equities`` rows are considered, renormalized to 100% of the equity sleeve (or, with
    ``by_retirement``, of each retirement / non-retirement sleeve). Value that does not
    resolve to a specific tier is redistributed across large/mid/small_cap by the
    benchmark's within-region developed tier weights; ``region == "emerging"`` value lands
    in the ``emerging`` tier.

    Returns rows in fixed tier order with ``market_cap_tier, portfolio_pct, market_pct,
    drift_pct`` (plus a leading ``is_retirement`` column when grouped). Empty schema frame
    when there is no equity value or the benchmark is unusable.
    """
    equities = _equities_or_none(df, market_weights)
    if equities is None:
        return pl.DataFrame(schema=_COMPARISON_SCHEMA)
    ratios = _developed_ratios(market_weights)
    if ratios is None:
        return pl.DataFrame(schema=_COMPARISON_SCHEMA)
    region_classes = ratios["_region_class"].unique().to_list()

    base = pl.DataFrame({"market_cap_tier": _TIERS})
    order_frame = pl.DataFrame(
        {"market_cap_tier": _TIERS, "_order": list(range(len(_TIERS)))}
    )
    market = _benchmark_tier_pct(market_weights, base)
    return _compare(
        equities,
        market,
        base,
        ["market_cap_tier"],
        order_frame,
        lambda sleeve: _tier_totals(sleeve, ratios, region_classes),
        by_retirement,
        _COMPARISON_SCHEMA,
    )


# ── region x cap-tier comparison ────────────────────────────────────────────


def _benchmark_region_tier_pct(market_weights: pl.DataFrame) -> pl.DataFrame | None:
    """Benchmark weight per (region, cap tier) cell, renormalized to 100%.

    Returns ``[region, market_cap_tier, market_pct]`` restricted to the seven grid cells
    (us/ex_us x large/mid/small, plus emerging). ``None`` unless all of ``us`` / ``ex_us``
    / ``emerging`` are represented.
    """
    grid = (
        market_weights.with_columns(
            _norm("region").alias("region"),
            _norm("market_segment").alias("market_cap_tier"),
        )
        .filter(
            (pl.col("region").is_in(["us", "ex_us"]) & pl.col("market_cap_tier").is_in(_DEV_TIERS))
            | ((pl.col("region") == "emerging") & (pl.col("market_cap_tier") == "emerging"))
        )
        .group_by("region", "market_cap_tier")
        .agg(pl.col("weight").sum())
    )
    if grid.is_empty() or not {"us", "ex_us", "emerging"} <= set(grid["region"].to_list()):
        return None
    total = grid.select(pl.col("weight").sum()).item()
    return grid.with_columns(
        (pl.col("weight") / total * 100).round(2).alias("market_pct")
    ).select("region", "market_cap_tier", "market_pct")


def _region_tier_totals(equities: pl.DataFrame, grid: pl.DataFrame) -> pl.DataFrame:
    """Bucket an equities frame into the region x cap-tier grid.

    ``grid`` is the ``_benchmark_region_tier_pct`` frame; its ``market_pct`` values double
    as the redistribution weights. Value with a resolved region+tier lands directly; a
    resolved region but unresolved tier is split across that region's tiers; an unresolved
    region is split across regions (by tier if the tier is known, else across the whole
    grid). ``region == "emerging"`` always lands in the emerging cell.
    """
    weights = {(r["region"], r["market_cap_tier"]): r["market_pct"] for r in grid.to_dicts()}
    grid_total = sum(weights.values())

    def _norm_ratio(items: dict) -> dict:
        s = sum(items.values())
        return {k: v / s for k, v in items.items()} if s else {}

    within_region = {
        reg: _norm_ratio({t: weights[(reg, t)] for t in _DEV_TIERS if (reg, t) in weights})
        for reg in ("us", "ex_us")
    }
    within_tier = {
        t: _norm_ratio({reg: weights[(reg, t)] for reg in ("us", "ex_us") if (reg, t) in weights})
        for t in _DEV_TIERS
    }

    cells = {cell: 0.0 for cell in _CELLS}
    grouped = (
        equities.with_columns(_norm("region").alias("_r"), _norm("market_segment").alias("_s"))
        .group_by("_r", "_s")
        .agg(pl.col("value").sum().alias("_v"))
    )
    for row in grouped.iter_rows(named=True):
        region, seg, value = row["_r"], row["_s"], row["_v"] or 0.0
        if region == "emerging":
            cells[("emerging", "emerging")] += value
        elif region in ("us", "ex_us"):
            if seg in _DEV_TIERS:
                cells[(region, seg)] += value
            else:
                for tier, frac in within_region[region].items():
                    cells[(region, tier)] += value * frac
        elif seg in _DEV_TIERS:
            for reg, frac in within_tier[seg].items():
                cells[(reg, seg)] += value * frac
        else:
            for cell, weight in weights.items():
                cells[cell] += value * (weight / grid_total)

    rows = [
        {"region": reg, "market_cap_tier": tier, "value": val}
        for (reg, tier), val in cells.items()
        if val
    ]
    return pl.DataFrame(
        rows, schema={"region": pl.Utf8, "market_cap_tier": pl.Utf8, "value": pl.Float64}
    )


def region_comparison(
    df: pl.DataFrame, market_weights: pl.DataFrame, by_retirement: bool = False
) -> pl.DataFrame:
    """Compare the equity sleeve's region x cap-tier mix to the global market-cap benchmark.

    Same input and semantics as :func:`market_cap_comparison`, but bucketed on the seven
    ``(region, cap tier)`` grid cells (``us`` / ``ex_us`` x large/mid/small, plus a single
    ``emerging`` cell). ``portfolio_pct`` and ``market_pct`` each sum to 100 across the grid
    (per sleeve when ``by_retirement``). Sum the tiers within a region to read the plain
    regional weight.

    Returns ``region, market_cap_tier, portfolio_pct, market_pct, drift_pct`` (plus a
    leading ``is_retirement`` column when grouped). Empty schema frame when there is no
    equity value or the benchmark lacks the full region grid.
    """
    equities = _equities_or_none(df, market_weights)
    if equities is None:
        return pl.DataFrame(schema=_REGION_COMPARISON_SCHEMA)
    grid = _benchmark_region_tier_pct(market_weights)
    if grid is None:
        return pl.DataFrame(schema=_REGION_COMPARISON_SCHEMA)

    base = pl.DataFrame(
        {"region": [c[0] for c in _CELLS], "market_cap_tier": [c[1] for c in _CELLS]}
    )
    order_frame = base.with_columns(_order=pl.Series(range(len(_CELLS))))
    return _compare(
        equities,
        grid,
        base,
        ["region", "market_cap_tier"],
        order_frame,
        lambda sleeve: _region_tier_totals(sleeve, grid),
        by_retirement,
        _REGION_COMPARISON_SCHEMA,
    )
