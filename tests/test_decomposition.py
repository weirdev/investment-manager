from pathlib import Path

import polars as pl
import pytest

from investment_manager import decomposition as decomp


_COMPOSITIONS_SCHEMA = {
    "canonical_ticker": pl.Utf8,
    "asset_class": pl.Utf8,
    "market_segment": pl.Utf8,
    "region": pl.Utf8,
    "fraction": pl.Float64,
}


def _sample_compositions() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "canonical_ticker": ["VTI", "VTI", "VTI"],
            "asset_class": ["equities", "equities", "equities"],
            "market_segment": ["large_cap", "mid_cap", "small_cap"],
            "region": ["us", "us", "us"],
            "fraction": [0.72, 0.18, 0.10],
        },
        schema=_COMPOSITIONS_SCHEMA,
    )


def _sample_positions(tickers: list[str], values: list[float]) -> pl.DataFrame:
    n = len(tickers)
    return pl.DataFrame(
        {
            "institution_name": ["TestInst"] * n,
            "account_name": ["TestAcct"] * n,
            "account_number": ["1234"] * n,
            "account_type": ["brokerage"] * n,
            "owner": ["alice"] * n,
            "ticker": tickers,
            "canonical_ticker": tickers,
            "value": values,
            "asset_class": ["equities"] * n,
            "market_segment": ["total_market"] * n,
            "region": ["us"] * n,
            "security_type": ["etf"] * n,
        }
    )


class TestLoadFundCompositions:
    def test_returns_empty_df_when_file_missing(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.csv"
        result = decomp.load_fund_compositions(path=missing)
        assert result.is_empty()
        assert set(result.columns) == set(_COMPOSITIONS_SCHEMA.keys())

    def test_loads_csv_correctly(self, tmp_path: Path):
        csv = tmp_path / "compositions.csv"
        csv.write_text(
            "canonical_ticker,asset_class,market_segment,region,fraction\n"
            "VTI,equities,large_cap,us,0.72\n"
            "VTI,equities,mid_cap,us,0.28\n"
        )
        result = decomp.load_fund_compositions(path=csv)
        assert len(result) == 2
        assert result["canonical_ticker"].to_list() == ["VTI", "VTI"]
        assert result["fraction"].to_list() == pytest.approx([0.72, 0.28])


class TestDecompose:
    def test_returns_df_unchanged_when_compositions_empty(self):
        df = _sample_positions(["AAPL", "VTI"], [1000.0, 2000.0])
        empty_comp = pl.DataFrame(schema=_COMPOSITIONS_SCHEMA)
        result = decomp.decompose(df, empty_comp)
        assert result.shape == df.shape

    def test_returns_df_unchanged_when_df_empty(self):
        empty_df = pl.DataFrame(
            schema={
                "institution_name": pl.Utf8,
                "canonical_ticker": pl.Utf8,
                "value": pl.Float64,
            }
        )
        result = decomp.decompose(empty_df, _sample_compositions())
        assert result.is_empty()

    def test_passes_through_atomic_positions(self):
        df = _sample_positions(["AAPL", "MSFT"], [1000.0, 2000.0])
        result = decomp.decompose(df, _sample_compositions())
        # No ticker in compositions → unchanged
        assert result.shape == df.shape
        assert set(result["canonical_ticker"].to_list()) == {"AAPL", "MSFT"}

    def test_expands_composite_into_correct_number_of_rows(self):
        df = _sample_positions(["VTI"], [1000.0])
        result = decomp.decompose(df, _sample_compositions())
        # VTI has 3 composition rows
        assert len(result) == 3

    def test_component_values_equal_original_times_fraction(self):
        original_value = 1000.0
        df = _sample_positions(["VTI"], [original_value])
        result = decomp.decompose(df, _sample_compositions())
        expected = [original_value * f for f in [0.72, 0.18, 0.10]]
        assert sorted(result["value"].to_list()) == pytest.approx(sorted(expected))

    def test_component_fields_come_from_compositions(self):
        df = _sample_positions(["VTI"], [1000.0])
        result = decomp.decompose(df, _sample_compositions())
        assert set(result["market_segment"].to_list()) == {"large_cap", "mid_cap", "small_cap"}
        assert set(result["asset_class"].to_list()) == {"equities"}

    def test_non_composition_columns_preserved(self):
        df = _sample_positions(["VTI"], [1000.0])
        result = decomp.decompose(df, _sample_compositions())
        assert result["institution_name"].to_list() == ["TestInst"] * 3
        assert result["account_name"].to_list() == ["TestAcct"] * 3
        assert result["owner"].to_list() == ["alice"] * 3
        assert result["account_type"].to_list() == ["brokerage"] * 3

    def test_total_value_conserved(self):
        df = _sample_positions(["AAPL", "VTI"], [500.0, 1000.0])
        result = decomp.decompose(df, _sample_compositions())
        assert result["value"].sum() == pytest.approx(df["value"].sum())

    def test_mix_of_atomic_and_composite(self):
        df = _sample_positions(["AAPL", "VTI", "MSFT"], [500.0, 1000.0, 300.0])
        result = decomp.decompose(df, _sample_compositions())
        # AAPL and MSFT are atomic (1 row each), VTI expands to 3
        assert len(result) == 2 + 3
        assert result["value"].sum() == pytest.approx(1800.0)
