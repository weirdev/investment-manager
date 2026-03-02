"""Integration tests: run the real pipeline against hermetic fixture data with no mocking."""
import pytest

from investment_manager import analysis, pipeline
from investment_manager import decomposition as decomp
from .conftest import TEST_DATA_PATHS

_EXPECTED_COLUMNS = {
    "institution_name",
    "account_name",
    "account_number",
    "account_type",
    "owner",
    "ticker",
    "value",
    "canonical_ticker",
    "asset_class",
    "security_type",
    "market_segment",
    "region",
}
@pytest.fixture(scope="module")
def positions_df():
    return pipeline.run(data_paths=TEST_DATA_PATHS)


class TestPipelineIntegration:
    def test_returns_non_empty_dataframe(self, positions_df):
        assert not positions_df.is_empty()

    def test_all_12_columns_present(self, positions_df):
        assert _EXPECTED_COLUMNS.issubset(set(positions_df.columns))


class TestAnalysisIntegration:
    def test_aggregate_positions_runs(self, positions_df):
        result = analysis.aggregate_positions(positions_df)
        assert result is not None

    def test_concentration_breakdown_percentages_sum_to_100(self, positions_df):
        result = analysis.concentration_breakdown(positions_df)
        total_pct = result["pct_of_portfolio"].sum()
        assert abs(total_pct - 100.0) < 0.1

    def test_allocation_breakdown_non_empty(self, positions_df):
        result = analysis.allocation_breakdown(positions_df)
        assert not result.is_empty()

    def test_owner_breakdown_non_empty(self, positions_df):
        result = analysis.owner_breakdown(positions_df)
        assert not result.is_empty()


class TestDecompositionIntegration:
    def test_decompose_concentration_percentages_sum_to_100(self, positions_df):
        compositions = decomp.load_fund_compositions(TEST_DATA_PATHS.compositions_path)
        decomposed = decomp.decompose(positions_df, compositions)
        result = analysis.concentration_breakdown(decomposed)
        total_pct = result["pct_of_portfolio"].sum()
        assert abs(total_pct - 100.0) < 0.1

    def test_total_value_preserved_after_decomposition(self, positions_df):
        compositions = decomp.load_fund_compositions(TEST_DATA_PATHS.compositions_path)
        decomposed = decomp.decompose(positions_df, compositions)
        original_total = positions_df["value"].sum()
        decomposed_total = decomposed["value"].sum()
        assert abs(decomposed_total - original_total) / original_total < 1e-4
