import shutil
from pathlib import Path

import polars as pl

from investment_manager import pipeline
from investment_manager.paths import DataPaths

from .conftest import TEST_DATA_PATHS


class TestRun:
    def test_returns_dataframe(self):
        df = pipeline.run(data_paths=TEST_DATA_PATHS)
        assert isinstance(df, pl.DataFrame)

    def test_expected_columns(self):
        df = pipeline.run(data_paths=TEST_DATA_PATHS)
        assert {
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
        }.issubset(set(df.columns))

    def test_has_rows(self):
        df = pipeline.run(data_paths=TEST_DATA_PATHS)
        assert df.height > 0

    def test_value_column_is_float(self):
        df = pipeline.run(data_paths=TEST_DATA_PATHS)
        assert df["value"].dtype == pl.Float64

    def test_empty_dir_returns_empty_dataframe(self, tmp_path):
        data_paths = DataPaths.from_personal_data_dir(tmp_path)
        df = pipeline.run(data_paths=data_paths)
        assert df.is_empty()
        assert set(df.columns) == {
            "institution_name",
            "account_name",
            "account_number",
            "account_type",
            "owner",
            "is_retirement",
            "ticker",
            "value",
            "canonical_ticker",
            "asset_class",
            "security_type",
            "market_segment",
            "region",
        }

    def test_deduplication_of_shared_accounts(self, tmp_path):
        """Shared accounts in multiple owner dirs appear exactly once in output."""
        personal_root = tmp_path / "personal_data"
        raw_dir = personal_root / "raw_account_details"
        data_paths = DataPaths.from_personal_data_dir(personal_root)
        fidelity_fixture = (
            TEST_DATA_PATHS.raw_account_details_dir / "john" / "fidelity" / "fidelity_sample.csv"
        )
        for owner in ("owner_a", "owner_b"):
            dest = raw_dir / owner / "fidelity"
            dest.mkdir(parents=True)
            shutil.copy(fidelity_fixture, dest / "fidelity_sample.csv")
        shutil.copy(TEST_DATA_PATHS.accounts_path, data_paths.accounts_path)
        shutil.copy(TEST_DATA_PATHS.metadata_path, data_paths.metadata_path)

        df = pipeline.run(data_paths=data_paths)
        dupes = df.filter(
            pl.struct(["institution_name", "account_name", "ticker"]).is_duplicated()
        )
        assert dupes.is_empty(), "Duplicate (institution_name, account_name, ticker) rows found"

    def test_data_dir_uses_sibling_registry_and_metadata(self, tmp_path):
        personal_root = tmp_path / "custom_personal_data"
        raw_dir = personal_root / "raw_account_details" / "john" / "fidelity"
        raw_dir.mkdir(parents=True)
        shutil.copy(
            TEST_DATA_PATHS.raw_account_details_dir / "john" / "fidelity" / "fidelity_sample.csv",
            raw_dir / "fidelity_sample.csv",
        )
        (personal_root / "known-accounts.csv").write_text(
            "institution_name,account_name,account_number,account_type,is_retirement,owner\n"
            "Fidelity,Alt Brokerage,X11111111,custom_taxable,false,casey\n"
            "Fidelity,Alt IRA,X22222222,custom_ira,true,casey\n",
            encoding="utf-8",
        )
        (personal_root / "asset-metadata.csv").write_text(
            "canonical_ticker,asset_class,security_type,market_segment,region\n"
            "AAPL,custom_equity,stock,mega_cap,us\n"
            "MSFT,custom_equity,stock,mega_cap,us\n"
            "SPAXX,cash,money_market,cash,us\n"
            "VOO,custom_equity,etf,large_cap,us\n",
            encoding="utf-8",
        )

        df = pipeline.run(data_dir=personal_root / "raw_account_details")
        assert set(df["account_type"].unique().to_list()) == {"custom_taxable", "custom_ira"}
        assert set(df["owner"].unique().to_list()) == {"casey"}
        assert set(df["asset_class"].unique().to_list()) == {"custom_equity", "cash"}
