import polars as pl
import pytest

from investment_manager import analysis


def _sample_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "institution_name": ["Fidelity", "Fidelity", "Fidelity", "Fidelity"],
            "account_name": [
                "Test Brokerage",
                "Test Brokerage",
                "Test Brokerage",
                "Test IRA",
            ],
            "account_type": ["brokerage", "brokerage", "brokerage", "ira"],
            "ticker": ["AAPL", "MSFT", "SPAXX", "VOO"],
            "value": [1500.0, 1500.0, 2000.0, 1200.0],
        }
    )


class TestAggregatePositions:
    def test_returns_dataframe(self):
        result = analysis.aggregate_positions(_sample_df())
        assert isinstance(result, pl.DataFrame)

    def test_has_ticker_and_total_value(self):
        result = analysis.aggregate_positions(_sample_df())
        assert "ticker" in result.columns
        assert "total_value" in result.columns

    def test_total_value_correct(self):
        result = analysis.aggregate_positions(_sample_df())
        aapl_row = result.filter(pl.col("ticker") == "AAPL")
        assert aapl_row["total_value"][0] == pytest.approx(1500.0)

    def test_empty_df_returns_empty(self):
        empty = pl.DataFrame(
            schema={
                "institution_name": pl.Utf8,
                "account_name": pl.Utf8,
                "account_type": pl.Utf8,
                "ticker": pl.Utf8,
                "value": pl.Float64,
            }
        )
        result = analysis.aggregate_positions(empty)
        assert result.is_empty()


class TestAllocationBreakdown:
    def test_returns_dataframe(self):
        result = analysis.allocation_breakdown(_sample_df())
        assert isinstance(result, pl.DataFrame)

    def test_has_expected_columns(self):
        result = analysis.allocation_breakdown(_sample_df())
        assert "account_type" in result.columns
        assert "institution_name" in result.columns
        assert "total_value" in result.columns
        assert "pct_of_portfolio" in result.columns

    def test_percentages_sum_to_100(self):
        result = analysis.allocation_breakdown(_sample_df())
        total_pct = result["pct_of_portfolio"].sum()
        assert total_pct == pytest.approx(100.0, abs=0.1)

    def test_brokerage_value(self):
        result = analysis.allocation_breakdown(_sample_df())
        brokerage = result.filter(pl.col("account_type") == "brokerage")
        assert brokerage["total_value"][0] == pytest.approx(5000.0)

    def test_empty_df_returns_empty(self):
        empty = pl.DataFrame(
            schema={
                "institution_name": pl.Utf8,
                "account_name": pl.Utf8,
                "account_type": pl.Utf8,
                "ticker": pl.Utf8,
                "value": pl.Float64,
            }
        )
        result = analysis.allocation_breakdown(empty)
        assert result.is_empty()
