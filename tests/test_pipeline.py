from pathlib import Path

import polars as pl
import pytest

from investment_manager import pipeline
from investment_manager.registry import AccountRegistry

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _empty_registry() -> AccountRegistry:
    reg = AccountRegistry.__new__(AccountRegistry)
    reg._accounts = {}
    return reg


class TestRun:
    def test_returns_dataframe(self):
        df = pipeline.run(data_dir=FIXTURES_DIR, registry=_empty_registry())
        assert isinstance(df, pl.DataFrame)

    def test_expected_columns(self):
        df = pipeline.run(data_dir=FIXTURES_DIR, registry=_empty_registry())
        assert {
            "institution_name",
            "account_name",
            "account_type",
            "ticker",
            "value",
            "canonical_ticker",
            "asset_class",
            "security_type",
            "market_segment",
            "region",
        }.issubset(set(df.columns))

    def test_has_rows(self):
        df = pipeline.run(data_dir=FIXTURES_DIR, registry=_empty_registry())
        assert df.height > 0

    def test_value_column_is_float(self):
        df = pipeline.run(data_dir=FIXTURES_DIR, registry=_empty_registry())
        assert df["value"].dtype == pl.Float64

    def test_empty_dir_returns_empty_dataframe(self, tmp_path):
        df = pipeline.run(data_dir=tmp_path, registry=_empty_registry())
        assert df.is_empty()
        assert set(df.columns) == {
            "institution_name",
            "account_name",
            "account_type",
            "ticker",
            "value",
        }
