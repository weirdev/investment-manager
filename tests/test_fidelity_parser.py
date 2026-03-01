from pathlib import Path

import pytest

from investment_manager.parsers.fidelity import FidelityParser
from investment_manager.registry import AccountRegistry

FIXTURE = Path(__file__).parent / "fixtures" / "john" / "fidelity" / "fidelity_sample.csv"
NON_FIDELITY = Path(__file__).parent / "fixtures" / "not_fidelity.csv"


def _make_registry() -> AccountRegistry:
    """Registry with the test accounts pre-loaded."""
    reg = AccountRegistry.__new__(AccountRegistry)
    reg._accounts = {}
    return reg


class TestCanParse:
    def test_detects_fidelity_csv(self):
        assert FidelityParser.can_parse(FIXTURE) is True

    def test_rejects_nonexistent_file(self):
        assert FidelityParser.can_parse(NON_FIDELITY) is False


class TestParse:
    def setup_method(self):
        self.parser = FidelityParser(registry=_make_registry())

    def test_returns_list_of_positions(self):
        positions = self.parser.parse(FIXTURE)
        assert isinstance(positions, list)
        assert len(positions) == 4

    def test_excludes_non_fidelity_accounts(self):
        positions = self.parser.parse(FIXTURE)
        tickers = {p.ticker for p in positions}
        assert "BND" not in tickers

    def test_institution_name_is_fidelity(self):
        positions = self.parser.parse(FIXTURE)
        assert all(p.institution_name == "Fidelity" for p in positions)

    def test_ticker_cleaned(self):
        positions = self.parser.parse(FIXTURE)
        tickers = {p.ticker for p in positions}
        assert "SPAXX" in tickers
        assert "SPAXX**" not in tickers

    def test_value_parsed_correctly(self):
        positions = self.parser.parse(FIXTURE)
        aapl = next(p for p in positions if p.ticker == "AAPL")
        assert aapl.value == pytest.approx(1500.00)

    def test_account_name_preserved(self):
        positions = self.parser.parse(FIXTURE)
        names = {p.account_name for p in positions}
        assert "Test Brokerage" in names
        assert "Test IRA" in names

    def test_unknown_account_type_is_unknown(self):
        positions = self.parser.parse(FIXTURE)
        # Registry is empty so all accounts resolve to 'unknown'
        assert all(p.account_type == "unknown" for p in positions)
        assert all(p.owner == "unknown" for p in positions)

    def test_registry_lookup_used_for_account_type(self):
        from investment_manager.models import Account

        reg = _make_registry()
        reg._accounts[("Fidelity", "Test Brokerage")] = Account(
            institution_name="Fidelity",
            account_name="Test Brokerage",
            account_type="brokerage",
            owner="unknown",
        )
        parser = FidelityParser(registry=reg)
        positions = parser.parse(FIXTURE)
        brokerage_positions = [p for p in positions if p.account_name == "Test Brokerage"]
        assert all(p.account_type == "brokerage" for p in brokerage_positions)
