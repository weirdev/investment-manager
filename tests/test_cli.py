from unittest.mock import patch

import polars as pl
import pytest
from typer.testing import CliRunner

from investment_manager.cli import app

runner = CliRunner()

_SCHEMA = {
    "institution_name": pl.Utf8,
    "account_name": pl.Utf8,
    "account_number": pl.Utf8,
    "account_type": pl.Utf8,
    "owner": pl.Utf8,
    "ticker": pl.Utf8,
    "value": pl.Float64,
    "canonical_ticker": pl.Utf8,
    "asset_class": pl.Utf8,
    "security_type": pl.Utf8,
    "market_segment": pl.Utf8,
    "region": pl.Utf8,
}


def _mock_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "institution_name": ["Fidelity"],
            "account_name": ["Brokerage"],
            "account_number": ["Z123"],
            "account_type": ["taxable"],
            "owner": ["john"],
            "ticker": ["VTI"],
            "value": [10000.0],
            "canonical_ticker": ["VTI"],
            "asset_class": ["equities"],
            "security_type": ["etf"],
            "market_segment": ["us_broad_market"],
            "region": ["us"],
        }
    )


def _mock_metals_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "institution_name": ["Fidelity"],
            "account_name": ["Brokerage"],
            "account_number": ["Z123"],
            "account_type": ["taxable"],
            "owner": ["john"],
            "ticker": ["PAXG"],
            "value": [5000.0],
            "canonical_ticker": ["PAXG"],
            "asset_class": ["precious_metals"],
            "security_type": ["token"],
            "market_segment": ["gold"],
            "region": ["global"],
        }
    )


def _empty_df() -> pl.DataFrame:
    return pl.DataFrame(schema=_SCHEMA)


class TestPositionsCommand:
    def test_exit_code_0_on_success(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["positions"])
        assert result.exit_code == 0

    def test_total_in_output(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["positions"])
        assert "Total:" in result.output

    def test_exit_code_1_on_empty(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_empty_df()):
            result = runner.invoke(app, ["positions"])
        assert result.exit_code == 1


class TestConcentrationCommand:
    def test_exit_code_0_on_success(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["concentration"])
        assert result.exit_code == 0

    def test_total_in_output(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["concentration"])
        assert "Total:" in result.output

    def test_exit_code_1_on_empty(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_empty_df()):
            result = runner.invoke(app, ["concentration"])
        assert result.exit_code == 1


class TestAllocationsCommand:
    def test_exit_code_0_on_success(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["allocations"])
        assert result.exit_code == 0

    def test_total_in_output(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["allocations"])
        assert "Total:" in result.output

    def test_exit_code_1_on_empty(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_empty_df()):
            result = runner.invoke(app, ["allocations"])
        assert result.exit_code == 1


class TestOwnersCommand:
    def test_exit_code_0_on_success(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["owners"])
        assert result.exit_code == 0

    def test_total_in_output(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["owners"])
        assert "Total:" in result.output

    def test_exit_code_1_on_empty(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_empty_df()):
            result = runner.invoke(app, ["owners"])
        assert result.exit_code == 1


class TestPreciousMetalsCommand:
    def test_exit_code_0_on_success(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_metals_df()):
            result = runner.invoke(app, ["precious-metals"])
        assert result.exit_code == 0

    def test_precious_metals_total_in_output(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_metals_df()):
            result = runner.invoke(app, ["precious-metals"])
        assert "Precious metals total:" in result.output

    def test_exit_code_1_on_empty(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_empty_df()):
            result = runner.invoke(app, ["precious-metals"])
        assert result.exit_code == 1

    def test_exit_code_1_on_no_metals(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["precious-metals"])
        assert result.exit_code == 1


class TestDecompositionCommand:
    def test_exit_code_0_on_success(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["decomposition"])
        assert result.exit_code == 0

    def test_total_in_output(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["decomposition"])
        assert "Total:" in result.output

    def test_no_account_type_flag_exits_0(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_mock_df()):
            result = runner.invoke(app, ["decomposition", "--no-account-type"])
        assert result.exit_code == 0

    def test_exit_code_1_on_empty(self):
        with patch("investment_manager.cli.pipeline.run", return_value=_empty_df()):
            result = runner.invoke(app, ["decomposition"])
        assert result.exit_code == 1
