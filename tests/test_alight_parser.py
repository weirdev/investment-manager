from pathlib import Path

import pytest

from investment_manager.models import Account
from investment_manager.parsers.alight import AlightParser
from investment_manager.registry import AccountRegistry

FIXTURE = Path(__file__).parent / "fixtures" / "john" / "alight" / "alight_sample.csv"
NON_ALIGHT = Path(__file__).parent / "fixtures" / "alight" / "not_alight.csv"


def _make_registry() -> AccountRegistry:
    reg = AccountRegistry.__new__(AccountRegistry)
    reg._accounts = {}
    return reg


class TestCanParse:
    def test_detects_alight_csv(self):
        assert AlightParser.can_parse(FIXTURE) is True

    def test_rejects_nonexistent_file(self):
        assert AlightParser.can_parse(NON_ALIGHT) is False


class TestParse:
    def setup_method(self):
        self.parser = AlightParser(registry=_make_registry())

    def test_returns_list_of_positions(self):
        positions = self.parser.parse(FIXTURE)
        assert isinstance(positions, list)

    def test_correct_position_count(self):
        positions = self.parser.parse(FIXTURE)
        # 2 from Test 401k Plan, 1 from Test 403b Plan; zero-balance row excluded
        assert len(positions) == 3

    def test_institution_name_is_alight(self):
        positions = self.parser.parse(FIXTURE)
        assert all(p.institution_name == "Alight" for p in positions)

    def test_skips_zero_balance_rows(self):
        positions = self.parser.parse(FIXTURE)
        tickers = {p.ticker for p in positions}
        assert "Zero Balance Fund" not in tickers

    def test_value_parsed_correctly(self):
        positions = self.parser.parse(FIXTURE)
        vtr = next(p for p in positions if p.ticker == "Vanguard Target Retirement 2060")
        assert vtr.value == pytest.approx(2000.00)

    def test_account_names_preserved(self):
        positions = self.parser.parse(FIXTURE)
        names = {p.account_name for p in positions}
        assert "Test 401k Plan" in names
        assert "Test 403b Plan" in names

    def test_unknown_account_type_when_registry_empty(self):
        positions = self.parser.parse(FIXTURE)
        assert all(p.account_type == "unknown" for p in positions)
        assert all(p.owner == "unknown" for p in positions)

    def test_registry_lookup_used_for_account_type(self):
        reg = _make_registry()
        reg._accounts[("Alight", "Test 401k Plan")] = Account(
            institution_name="Alight",
            account_name="Test 401k Plan",
            account_number="Test 401k Plan",
            account_type="401k",
            owner="unknown",
        )
        parser = AlightParser(registry=reg)
        positions = parser.parse(FIXTURE)
        plan_a = [p for p in positions if p.account_name == "Test 401k Plan"]
        assert all(p.account_type == "401k" for p in plan_a)
