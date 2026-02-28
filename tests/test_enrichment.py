from pathlib import Path

import polars as pl
import pytest

from investment_manager.enrichment import enrich, load_asset_mapping, load_asset_metadata


def _positions(**overrides) -> pl.DataFrame:
    data = {
        "institution_name": ["Fidelity"],
        "account_name": ["Test Brokerage"],
        "account_type": ["brokerage"],
        "ticker": ["AAPL"],
        "value": [1000.0],
    }
    data.update(overrides)
    return pl.DataFrame(data)


def _mapping(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame(
            schema={"account_type": pl.Utf8, "raw_ticker": pl.Utf8, "canonical_ticker": pl.Utf8}
        )
    return pl.DataFrame(rows)


def _metadata(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame(
            schema={
                "canonical_ticker": pl.Utf8,
                "asset_class": pl.Utf8,
                "security_type": pl.Utf8,
                "market_segment": pl.Utf8,
                "region": pl.Utf8,
            }
        )
    return pl.DataFrame(rows)


class TestEnrich:
    def test_canonical_ticker_resolved_via_mapping(self):
        mapping = _mapping([
            {"account_type": "brokerage", "raw_ticker": "AAPL", "canonical_ticker": "AAPL-MAPPED"}
        ])
        result = enrich(_positions(), mapping, _metadata([]))
        assert result["canonical_ticker"][0] == "AAPL-MAPPED"

    def test_fallback_when_ticker_not_in_mapping(self):
        result = enrich(_positions(), _mapping([]), _metadata([]))
        assert result["canonical_ticker"][0] == "AAPL"

    def test_fallback_strips_trailing_stars(self):
        positions = _positions(ticker=["SPAXX**"])
        result = enrich(positions, _mapping([]), _metadata([]))
        assert result["canonical_ticker"][0] == "SPAXX"

    def test_mapping_match_is_account_type_specific(self):
        """A mapping for a different account_type should not match."""
        mapping = _mapping([
            {"account_type": "ira", "raw_ticker": "AAPL", "canonical_ticker": "AAPL-IRA"}
        ])
        result = enrich(_positions(account_type=["brokerage"]), mapping, _metadata([]))
        assert result["canonical_ticker"][0] == "AAPL"

    def test_asset_metadata_joined_correctly(self):
        metadata = _metadata([{
            "canonical_ticker": "AAPL",
            "asset_class": "equity",
            "security_type": "stock",
            "market_segment": "large-cap",
            "region": "us",
        }])
        result = enrich(_positions(), _mapping([]), metadata)
        assert result["asset_class"][0] == "equity"
        assert result["region"][0] == "us"
        assert result["market_segment"][0] == "large-cap"
        assert result["security_type"][0] == "stock"

    def test_missing_metadata_fills_unknown(self):
        result = enrich(_positions(), _mapping([]), _metadata([]))
        assert result["asset_class"][0] == "unknown"
        assert result["security_type"][0] == "unknown"
        assert result["market_segment"][0] == "unknown"
        assert result["region"][0] == "unknown"

    def test_original_columns_preserved(self):
        result = enrich(_positions(), _mapping([]), _metadata([]))
        for col in ["institution_name", "account_name", "account_type", "ticker", "value"]:
            assert col in result.columns

    def test_all_enrichment_columns_present(self):
        result = enrich(_positions(), _mapping([]), _metadata([]))
        for col in ["canonical_ticker", "asset_class", "security_type", "market_segment", "region"]:
            assert col in result.columns


class TestLoadAssetMapping:
    def test_returns_empty_df_when_no_files_exist(self, tmp_path):
        result = load_asset_mapping(paths=[tmp_path / "nonexistent.csv"])
        assert result.is_empty()
        assert set(result.columns) == {"account_type", "raw_ticker", "canonical_ticker"}

    def test_loads_csv(self, tmp_path):
        csv = tmp_path / "mapping.csv"
        csv.write_text("account_type,raw_ticker,canonical_ticker\nbrokerage,FOO,BAR\n")
        result = load_asset_mapping(paths=[csv])
        assert result.height == 1
        assert result["canonical_ticker"][0] == "BAR"

    def test_concatenates_multiple_files(self, tmp_path):
        f1 = tmp_path / "a.csv"
        f2 = tmp_path / "b.csv"
        f1.write_text("account_type,raw_ticker,canonical_ticker\nbrokerage,A,A2\n")
        f2.write_text("account_type,raw_ticker,canonical_ticker\nira,B,B2\n")
        result = load_asset_mapping(paths=[f1, f2])
        assert result.height == 2


class TestLoadAssetMetadata:
    def test_returns_empty_df_when_missing(self, tmp_path):
        result = load_asset_metadata(path=tmp_path / "nonexistent.csv")
        assert result.is_empty()
        assert set(result.columns) == {
            "canonical_ticker", "asset_class", "security_type", "market_segment", "region"
        }

    def test_loads_csv(self, tmp_path):
        csv = tmp_path / "metadata.csv"
        csv.write_text(
            "canonical_ticker,asset_class,security_type,market_segment,region\n"
            "AAPL,equity,stock,large-cap,us\n"
        )
        result = load_asset_metadata(path=csv)
        assert result.height == 1
        assert result["asset_class"][0] == "equity"
