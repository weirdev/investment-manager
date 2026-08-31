from pathlib import Path

import polars as pl
import pytest

from investment_manager import rebalancing


_MARKET_WEIGHTS_SCHEMA = {
    "region": pl.Utf8,
    "market_segment": pl.Utf8,
    "weight": pl.Float64,
}

_TIERS = ["large_cap", "mid_cap", "small_cap", "emerging"]


def _weights() -> pl.DataFrame:
    """The committed seed benchmark, rebuilt inline."""
    return pl.DataFrame(
        {
            "region": ["us", "us", "us", "ex_us", "ex_us", "ex_us", "emerging"],
            "market_segment": [
                "large_cap",
                "mid_cap",
                "small_cap",
                "large_cap",
                "mid_cap",
                "small_cap",
                "emerging",
            ],
            "weight": [0.46, 0.09, 0.06, 0.21, 0.05, 0.03, 0.10],
        },
        schema=_MARKET_WEIGHTS_SCHEMA,
    )


def _positions(specs: list[tuple]) -> pl.DataFrame:
    """specs: list of (asset_class, market_segment, region, value[, is_retirement])."""
    return pl.DataFrame(
        {
            "asset_class": [s[0] for s in specs],
            "market_segment": [s[1] for s in specs],
            "region": [s[2] for s in specs],
            "value": [float(s[3]) for s in specs],
            "is_retirement": [bool(s[4]) if len(s) > 4 else False for s in specs],
        }
    )


class TestLoadMarketWeights:
    def test_returns_empty_df_when_file_missing(self, tmp_path: Path):
        result = rebalancing.load_market_weights(tmp_path / "nonexistent.csv")
        assert result.is_empty()
        assert set(result.columns) == set(_MARKET_WEIGHTS_SCHEMA.keys())

    def test_loads_committed_seed_file(self):
        result = rebalancing.load_market_weights()
        assert not result.is_empty()
        assert result["weight"].sum() == pytest.approx(1.0, abs=0.005)
        assert "emerging" in result["region"].to_list()

    def test_loads_csv_correctly(self, tmp_path: Path):
        csv = tmp_path / "weights.csv"
        csv.write_text(
            "region,market_segment,weight\n"
            "us,large_cap,0.7\n"
            "emerging,emerging,0.3\n"
        )
        result = rebalancing.load_market_weights(csv)
        assert len(result) == 2
        assert result["weight"].to_list() == pytest.approx([0.7, 0.3])


class TestEquitySleeveTotal:
    def test_zero_when_empty(self):
        assert rebalancing.equity_sleeve_total(pl.DataFrame()) == 0.0

    def test_zero_when_no_equities(self):
        df = _positions([("fixed_income", "total_market", "us", 1000.0)])
        assert rebalancing.equity_sleeve_total(df) == 0.0

    def test_sums_only_equities(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 1000.0),
                ("equities", "small_cap", "us", 500.0),
                ("fixed_income", "total_market", "us", 9999.0),
            ]
        )
        assert rebalancing.equity_sleeve_total(df) == pytest.approx(1500.0)


class TestMarketCapComparison:
    def test_empty_df_returns_empty(self):
        result = rebalancing.market_cap_comparison(pl.DataFrame(), _weights())
        assert result.is_empty()
        assert set(result.columns) == {"market_cap_tier", "portfolio_pct", "market_pct", "drift_pct"}

    def test_empty_weights_returns_empty(self):
        df = _positions([("equities", "large_cap", "us", 1000.0)])
        result = rebalancing.market_cap_comparison(df, pl.DataFrame(schema=_MARKET_WEIGHTS_SCHEMA))
        assert result.is_empty()

    def test_benchmark_without_developed_tiers_returns_empty(self):
        df = _positions([("equities", "large_cap", "us", 1000.0)])
        weights = pl.DataFrame(
            {"region": ["emerging"], "market_segment": ["emerging"], "weight": [1.0]},
            schema=_MARKET_WEIGHTS_SCHEMA,
        )
        assert rebalancing.market_cap_comparison(df, weights).is_empty()

    def test_output_columns(self):
        df = _positions([("equities", "large_cap", "us", 1000.0)])
        result = rebalancing.market_cap_comparison(df, _weights())
        assert set(result.columns) == {"market_cap_tier", "portfolio_pct", "market_pct", "drift_pct"}

    def test_fixed_tier_order(self):
        df = _positions([("equities", "small_cap", "us", 1000.0)])
        result = rebalancing.market_cap_comparison(df, _weights())
        assert result["market_cap_tier"].to_list() == _TIERS

    def test_all_four_tiers_present_when_zero(self):
        df = _positions([("equities", "large_cap", "us", 1000.0)])
        result = rebalancing.market_cap_comparison(df, _weights())
        assert len(result) == 4
        by_tier = {r["market_cap_tier"]: r["portfolio_pct"] for r in result.to_dicts()}
        assert by_tier["large_cap"] == pytest.approx(100.0)
        assert by_tier["mid_cap"] == 0.0
        assert by_tier["small_cap"] == 0.0
        assert by_tier["emerging"] == 0.0

    def test_non_equity_rows_excluded(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 1000.0),
                ("fixed_income", "total_market", "us", 1000.0),
                ("precious_metals", "gold", "global", 1000.0),
            ]
        )
        result = rebalancing.market_cap_comparison(df, _weights())
        large = next(r for r in result.to_dicts() if r["market_cap_tier"] == "large_cap")
        assert large["portfolio_pct"] == pytest.approx(100.0)

    def test_portfolio_pct_sums_to_100(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 4000.0),
                ("equities", "total_market", "ex_us", 3000.0),
                ("equities", "sector_tech", "us", 1000.0),
                ("equities", "large_cap", "emerging", 2000.0),
            ]
        )
        result = rebalancing.market_cap_comparison(df, _weights())
        assert result["portfolio_pct"].sum() == pytest.approx(100.0, abs=0.1)

    def test_market_pct_matches_collapsed_benchmark(self):
        df = _positions([("equities", "large_cap", "us", 1000.0)])
        result = rebalancing.market_cap_comparison(df, _weights())
        by_tier = {r["market_cap_tier"]: r["market_pct"] for r in result.to_dicts()}
        assert by_tier["large_cap"] == pytest.approx(67.0, abs=0.1)
        assert by_tier["mid_cap"] == pytest.approx(14.0, abs=0.1)
        assert by_tier["small_cap"] == pytest.approx(9.0, abs=0.1)
        assert by_tier["emerging"] == pytest.approx(10.0, abs=0.1)
        assert result["market_pct"].sum() == pytest.approx(100.0, abs=0.1)

    def test_drift_is_portfolio_minus_market(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 1000.0),
                ("equities", "small_cap", "us", 1000.0),
            ]
        )
        result = rebalancing.market_cap_comparison(df, _weights())
        for r in result.to_dicts():
            assert r["drift_pct"] == pytest.approx(
                round(r["portfolio_pct"] - r["market_pct"], 2)
            )

    def test_pure_tiers_pass_through(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 600.0),
                ("equities", "mid_cap", "us", 300.0),
                ("equities", "small_cap", "us", 100.0),
            ]
        )
        result = rebalancing.market_cap_comparison(df, _weights())
        by_tier = {r["market_cap_tier"]: r["portfolio_pct"] for r in result.to_dicts()}
        assert by_tier["large_cap"] == pytest.approx(60.0)
        assert by_tier["mid_cap"] == pytest.approx(30.0)
        assert by_tier["small_cap"] == pytest.approx(10.0)
        assert by_tier["emerging"] == 0.0

    def test_us_residual_uses_us_ratio(self):
        df = _positions([("equities", "total_market", "us", 100.0)])
        result = rebalancing.market_cap_comparison(df, _weights())
        by_tier = {r["market_cap_tier"]: r["portfolio_pct"] for r in result.to_dicts()}
        # US developed weights 0.46 / 0.09 / 0.06 -> normalized over 0.61
        assert by_tier["large_cap"] == pytest.approx(75.41, abs=0.05)
        assert by_tier["mid_cap"] == pytest.approx(14.75, abs=0.05)
        assert by_tier["small_cap"] == pytest.approx(9.84, abs=0.05)
        assert by_tier["emerging"] == 0.0

    def test_ex_us_residual_uses_ex_us_ratio(self):
        df = _positions([("equities", "total_market", "ex_us", 100.0)])
        result = rebalancing.market_cap_comparison(df, _weights())
        by_tier = {r["market_cap_tier"]: r["portfolio_pct"] for r in result.to_dicts()}
        # ex-US developed weights 0.21 / 0.05 / 0.03 -> normalized over 0.29
        assert by_tier["large_cap"] == pytest.approx(72.41, abs=0.05)
        assert by_tier["mid_cap"] == pytest.approx(17.24, abs=0.05)
        assert by_tier["small_cap"] == pytest.approx(10.34, abs=0.05)

    def test_global_residual_uses_combined_ratio(self):
        df = _positions([("equities", "total_market", "global", 100.0)])
        result = rebalancing.market_cap_comparison(df, _weights())
        by_tier = {r["market_cap_tier"]: r["portfolio_pct"] for r in result.to_dicts()}
        # combined developed 0.67 / 0.14 / 0.09 -> normalized over 0.90
        assert by_tier["large_cap"] == pytest.approx(74.44, abs=0.05)
        assert by_tier["mid_cap"] == pytest.approx(15.56, abs=0.05)
        assert by_tier["small_cap"] == pytest.approx(10.0, abs=0.05)

    def test_blank_region_residual_uses_combined_ratio(self):
        df = _positions([("equities", "total_market", "", 100.0)])
        result = rebalancing.market_cap_comparison(df, _weights())
        by_tier = {r["market_cap_tier"]: r["portfolio_pct"] for r in result.to_dicts()}
        assert by_tier["large_cap"] == pytest.approx(74.44, abs=0.05)

    def test_emerging_region_always_goes_to_emerging_tier(self):
        df = _positions(
            [
                ("equities", "total_market", "emerging", 100.0),
                ("equities", "large_cap", "emerging", 100.0),
            ]
        )
        result = rebalancing.market_cap_comparison(df, _weights())
        by_tier = {r["market_cap_tier"]: r["portfolio_pct"] for r in result.to_dicts()}
        assert by_tier["emerging"] == pytest.approx(100.0)

    def test_unknown_segment_treated_as_residual(self):
        df = _positions([("equities", "sector_energy", "us", 100.0)])
        result = rebalancing.market_cap_comparison(df, _weights())
        by_tier = {r["market_cap_tier"]: r["portfolio_pct"] for r in result.to_dicts()}
        assert by_tier["large_cap"] == pytest.approx(75.41, abs=0.05)
        assert by_tier["emerging"] == 0.0

    def test_equity_total_zero_returns_empty(self):
        df = _positions([("equities", "large_cap", "us", 0.0)])
        assert rebalancing.market_cap_comparison(df, _weights()).is_empty()

    def test_mixed_resolved_and_residual_conserves_value(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 100.0),
                ("equities", "total_market", "us", 100.0),
                ("equities", "large_cap", "emerging", 100.0),
            ]
        )
        result = rebalancing.market_cap_comparison(df, _weights())
        assert result["portfolio_pct"].sum() == pytest.approx(100.0, abs=0.1)
        by_tier = {r["market_cap_tier"]: r["portfolio_pct"] for r in result.to_dicts()}
        assert by_tier["emerging"] == pytest.approx(33.33, abs=0.05)
        # large_cap: 100 resolved + 100 * 0.7541 residual = 175.41 of 300
        assert by_tier["large_cap"] == pytest.approx(58.47, abs=0.1)


class TestMarketCapComparisonByRetirement:
    def _mixed(self) -> pl.DataFrame:
        return _positions(
            [
                ("equities", "large_cap", "us", 700.0, True),
                ("equities", "small_cap", "us", 300.0, True),
                ("equities", "large_cap", "us", 400.0, False),
                ("equities", "mid_cap", "us", 600.0, False),
            ]
        )

    def test_adds_is_retirement_column(self):
        result = rebalancing.market_cap_comparison(self._mixed(), _weights(), by_retirement=True)
        assert result.columns[0] == "is_retirement"
        assert set(result.columns) == {
            "is_retirement",
            "market_cap_tier",
            "portfolio_pct",
            "market_pct",
            "drift_pct",
        }

    def test_eight_rows_when_both_sleeves_present(self):
        result = rebalancing.market_cap_comparison(self._mixed(), _weights(), by_retirement=True)
        assert len(result) == 8

    def test_retirement_rows_come_first_in_tier_order(self):
        result = rebalancing.market_cap_comparison(self._mixed(), _weights(), by_retirement=True)
        assert result["is_retirement"].to_list() == [True] * 4 + [False] * 4
        assert result["market_cap_tier"].to_list()[:4] == _TIERS

    def test_each_sleeve_sums_to_100(self):
        result = rebalancing.market_cap_comparison(self._mixed(), _weights(), by_retirement=True)
        for is_retirement in (True, False):
            sleeve = result.filter(pl.col("is_retirement") == is_retirement)
            assert sleeve["portfolio_pct"].sum() == pytest.approx(100.0, abs=0.1)

    def test_market_pct_repeated_across_sleeves(self):
        result = rebalancing.market_cap_comparison(self._mixed(), _weights(), by_retirement=True)
        ret = result.filter(pl.col("is_retirement")).sort("market_cap_tier")
        non = result.filter(~pl.col("is_retirement")).sort("market_cap_tier")
        assert ret["market_pct"].to_list() == non["market_pct"].to_list()

    def test_drift_is_portfolio_minus_market(self):
        result = rebalancing.market_cap_comparison(self._mixed(), _weights(), by_retirement=True)
        for r in result.to_dicts():
            assert r["drift_pct"] == pytest.approx(round(r["portfolio_pct"] - r["market_pct"], 2))

    def test_sleeve_values_are_independent(self):
        result = rebalancing.market_cap_comparison(self._mixed(), _weights(), by_retirement=True)
        by_key = {(r["is_retirement"], r["market_cap_tier"]): r["portfolio_pct"] for r in result.to_dicts()}
        assert by_key[(True, "large_cap")] == pytest.approx(70.0)
        assert by_key[(True, "small_cap")] == pytest.approx(30.0)
        assert by_key[(False, "large_cap")] == pytest.approx(40.0)
        assert by_key[(False, "mid_cap")] == pytest.approx(60.0)

    def test_single_sleeve_returns_four_rows(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 700.0, True),
                ("equities", "small_cap", "us", 300.0, True),
            ]
        )
        result = rebalancing.market_cap_comparison(df, _weights(), by_retirement=True)
        assert len(result) == 4
        assert result["is_retirement"].to_list() == [True] * 4

    def test_falls_back_when_no_is_retirement_column(self):
        df = pl.DataFrame(
            {
                "asset_class": ["equities"],
                "market_segment": ["large_cap"],
                "region": ["us"],
                "value": [1000.0],
            }
        )
        result = rebalancing.market_cap_comparison(df, _weights(), by_retirement=True)
        assert "is_retirement" not in result.columns
        assert len(result) == 4

    def test_by_retirement_false_matches_default(self):
        df = self._mixed()
        grouped_off = rebalancing.market_cap_comparison(df, _weights(), by_retirement=False)
        assert "is_retirement" not in grouped_off.columns
        assert len(grouped_off) == 4


_CELLS = [
    ("us", "large_cap"),
    ("us", "mid_cap"),
    ("us", "small_cap"),
    ("ex_us", "large_cap"),
    ("ex_us", "mid_cap"),
    ("ex_us", "small_cap"),
    ("emerging", "emerging"),
]


def _grid(result: pl.DataFrame) -> dict:
    return {(r["region"], r["market_cap_tier"]): r["portfolio_pct"] for r in result.to_dicts()}


class TestRegionComparison:
    def test_empty_df_returns_empty(self):
        result = rebalancing.region_comparison(pl.DataFrame(), _weights())
        assert result.is_empty()
        assert set(result.columns) == {
            "region",
            "market_cap_tier",
            "portfolio_pct",
            "market_pct",
            "drift_pct",
        }

    def test_empty_weights_returns_empty(self):
        df = _positions([("equities", "large_cap", "us", 1000.0)])
        assert rebalancing.region_comparison(
            df, pl.DataFrame(schema=_MARKET_WEIGHTS_SCHEMA)
        ).is_empty()

    def test_benchmark_without_full_region_grid_returns_empty(self):
        df = _positions([("equities", "large_cap", "us", 1000.0)])
        weights = pl.DataFrame(
            {"region": ["us"], "market_segment": ["large_cap"], "weight": [1.0]},
            schema=_MARKET_WEIGHTS_SCHEMA,
        )
        assert rebalancing.region_comparison(df, weights).is_empty()

    def test_seven_cells_in_fixed_order(self):
        df = _positions([("equities", "large_cap", "us", 1000.0)])
        result = rebalancing.region_comparison(df, _weights())
        assert list(zip(result["region"].to_list(), result["market_cap_tier"].to_list())) == _CELLS

    def test_market_pct_matches_benchmark(self):
        df = _positions([("equities", "large_cap", "us", 1000.0)])
        result = rebalancing.region_comparison(df, _weights())
        mkt = {(r["region"], r["market_cap_tier"]): r["market_pct"] for r in result.to_dicts()}
        assert mkt[("us", "large_cap")] == pytest.approx(46.0)
        assert mkt[("us", "mid_cap")] == pytest.approx(9.0)
        assert mkt[("ex_us", "small_cap")] == pytest.approx(3.0)
        assert mkt[("emerging", "emerging")] == pytest.approx(10.0)
        assert result["market_pct"].sum() == pytest.approx(100.0, abs=0.1)

    def test_portfolio_pct_sums_to_100(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 4000.0),
                ("equities", "total_market", "ex_us", 3000.0),
                ("equities", "sector_tech", "global", 1000.0),
                ("equities", "mid_cap", "emerging", 2000.0),
            ]
        )
        result = rebalancing.region_comparison(df, _weights())
        assert result["portfolio_pct"].sum() == pytest.approx(100.0, abs=0.1)

    def test_pure_region_tier_pass_through(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 100.0),
                ("equities", "small_cap", "ex_us", 100.0),
            ]
        )
        grid = _grid(rebalancing.region_comparison(df, _weights()))
        assert grid[("us", "large_cap")] == pytest.approx(50.0)
        assert grid[("ex_us", "small_cap")] == pytest.approx(50.0)
        assert grid[("emerging", "emerging")] == 0.0

    def test_resolved_region_residual_tier_splits_within_region(self):
        df = _positions([("equities", "total_market", "us", 100.0)])
        grid = _grid(rebalancing.region_comparison(df, _weights()))
        # US developed weights 0.46 / 0.09 / 0.06 -> normalized over 0.61
        assert grid[("us", "large_cap")] == pytest.approx(75.41, abs=0.05)
        assert grid[("us", "mid_cap")] == pytest.approx(14.75, abs=0.05)
        assert grid[("us", "small_cap")] == pytest.approx(9.84, abs=0.05)
        assert grid[("ex_us", "large_cap")] == 0.0

    def test_unknown_region_resolved_tier_splits_across_regions(self):
        df = _positions([("equities", "large_cap", "", 100.0)])
        grid = _grid(rebalancing.region_comparison(df, _weights()))
        # large-cap weights US 0.46 vs ex-US 0.21 -> 68.66 / 31.34
        assert grid[("us", "large_cap")] == pytest.approx(68.66, abs=0.05)
        assert grid[("ex_us", "large_cap")] == pytest.approx(31.34, abs=0.05)
        assert grid[("us", "mid_cap")] == 0.0

    def test_unknown_region_residual_tier_spreads_across_whole_grid(self):
        df = _positions([("equities", "total_market", "global", 100.0)])
        grid = _grid(rebalancing.region_comparison(df, _weights()))
        assert grid[("us", "large_cap")] == pytest.approx(46.0, abs=0.05)
        assert grid[("emerging", "emerging")] == pytest.approx(10.0, abs=0.05)

    def test_emerging_region_ignores_cap_tier(self):
        df = _positions(
            [
                ("equities", "large_cap", "emerging", 100.0),
                ("equities", "total_market", "emerging", 100.0),
            ]
        )
        grid = _grid(rebalancing.region_comparison(df, _weights()))
        assert grid[("emerging", "emerging")] == pytest.approx(100.0)

    def test_non_equity_rows_excluded(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 1000.0),
                ("fixed_income", "total_market", "us", 5000.0),
            ]
        )
        grid = _grid(rebalancing.region_comparison(df, _weights()))
        assert grid[("us", "large_cap")] == pytest.approx(100.0)

    def test_drift_is_portfolio_minus_market(self):
        df = _positions(
            [
                ("equities", "large_cap", "us", 100.0),
                ("equities", "small_cap", "ex_us", 100.0),
            ]
        )
        result = rebalancing.region_comparison(df, _weights())
        for r in result.to_dicts():
            assert r["drift_pct"] == pytest.approx(round(r["portfolio_pct"] - r["market_pct"], 2))


class TestRegionComparisonByRetirement:
    def _mixed(self) -> pl.DataFrame:
        return _positions(
            [
                ("equities", "large_cap", "us", 700.0, True),
                ("equities", "small_cap", "ex_us", 300.0, True),
                ("equities", "large_cap", "us", 400.0, False),
                ("equities", "mid_cap", "emerging", 600.0, False),
            ]
        )

    def test_adds_is_retirement_and_fourteen_rows(self):
        result = rebalancing.region_comparison(self._mixed(), _weights(), by_retirement=True)
        assert result.columns[0] == "is_retirement"
        assert len(result) == 14
        assert result["is_retirement"].to_list() == [True] * 7 + [False] * 7

    def test_each_sleeve_sums_to_100(self):
        result = rebalancing.region_comparison(self._mixed(), _weights(), by_retirement=True)
        for is_retirement in (True, False):
            sleeve = result.filter(pl.col("is_retirement") == is_retirement)
            assert sleeve["portfolio_pct"].sum() == pytest.approx(100.0, abs=0.1)

    def test_sleeves_are_independent(self):
        result = rebalancing.region_comparison(self._mixed(), _weights(), by_retirement=True)
        by_key = {
            (r["is_retirement"], r["region"], r["market_cap_tier"]): r["portfolio_pct"]
            for r in result.to_dicts()
        }
        assert by_key[(True, "us", "large_cap")] == pytest.approx(70.0)
        assert by_key[(True, "ex_us", "small_cap")] == pytest.approx(30.0)
        assert by_key[(False, "emerging", "emerging")] == pytest.approx(60.0)
