from pathlib import Path

import pytest

from investment_manager.models import Account
from investment_manager.parsers.schwab import SchwabParser
from investment_manager.registry import AccountRegistry

FIXTURE = Path(__file__).parent / "fixtures" / "john" / "schwab" / "schwab_sample.csv"
NON_SCHWAB = Path(__file__).parent / "fixtures" / "schwab" / "not_schwab.csv"


def _make_registry() -> AccountRegistry:
    reg = AccountRegistry.__new__(AccountRegistry)
    reg._accounts = {}
    return reg


class TestCanParse:
    def test_detects_schwab_csv(self):
        assert SchwabParser.can_parse(FIXTURE) is True

    def test_rejects_nonexistent_file(self):
        assert SchwabParser.can_parse(NON_SCHWAB) is False


class TestParse:
    def setup_method(self):
        self.parser = SchwabParser(registry=_make_registry())

    def test_returns_list_of_positions(self):
        positions = self.parser.parse(FIXTURE)
        assert isinstance(positions, list)

    def test_correct_position_count(self):
        positions = self.parser.parse(FIXTURE)
        # 2 from Test Brokerage, 1 from Test IRA; cash and account-total rows excluded
        assert len(positions) == 3

    def test_institution_name_is_schwab(self):
        positions = self.parser.parse(FIXTURE)
        assert all(p.institution_name == "Schwab" for p in positions)

    def test_skips_cash_rows(self):
        positions = self.parser.parse(FIXTURE)
        tickers = {p.ticker for p in positions}
        assert "Cash & Cash Investments" not in tickers

    def test_value_parsed_correctly(self):
        positions = self.parser.parse(FIXTURE)
        vti = next(p for p in positions if p.ticker == "VTI")
        assert vti.value == pytest.approx(2000.00)

    def test_account_names_preserved(self):
        positions = self.parser.parse(FIXTURE)
        names = {p.account_name for p in positions}
        assert "Test Brokerage ...001" in names
        assert "Test IRA ...002" in names

    def test_unknown_account_type_when_registry_empty(self):
        positions = self.parser.parse(FIXTURE)
        assert all(p.account_type == "unknown" for p in positions)
        assert all(p.owner == "unknown" for p in positions)

    def test_account_numbers_extracted_from_suffix(self):
        positions = self.parser.parse(FIXTURE)
        numbers = {p.account_number for p in positions}
        assert "001" in numbers
        assert "002" in numbers

    def test_registry_lookup_used_for_account_type(self):
        reg = _make_registry()
        reg._accounts[("Schwab", "001")] = Account(
            institution_name="Schwab",
            account_name="Test Brokerage ...001",
            account_number="001",
            account_type="brokerage",
            owner="unknown",
        )
        parser = SchwabParser(registry=reg)
        positions = parser.parse(FIXTURE)
        brokerage = [p for p in positions if p.account_name == "Test Brokerage ...001"]
        assert all(p.account_type == "brokerage" for p in brokerage)
