from pathlib import Path

import pytest

from investment_manager.models import Account
from investment_manager.parsers.interactive_brokers import InteractiveBrokersParser
from investment_manager.registry import AccountRegistry

FIXTURE = Path(__file__).parent / "fixtures" / "john" / "interactive-brokers" / "ib_sample.csv"
NON_IB = Path(__file__).parent / "fixtures" / "interactive-brokers" / "not_ib.csv"


def _make_registry() -> AccountRegistry:
    reg = AccountRegistry.__new__(AccountRegistry)
    reg._accounts = {}
    return reg


class TestCanParse:
    def test_detects_ib_csv(self):
        assert InteractiveBrokersParser.can_parse(FIXTURE) is True

    def test_rejects_nonexistent_file(self):
        assert InteractiveBrokersParser.can_parse(NON_IB) is False


class TestParse:
    def setup_method(self):
        self.parser = InteractiveBrokersParser(registry=_make_registry())

    def test_correct_position_count(self):
        positions = self.parser.parse(FIXTURE)
        # 3 positions in Test Trust; Test Brokerage has only cash rows (skipped)
        assert len(positions) == 3

    def test_institution_name(self):
        positions = self.parser.parse(FIXTURE)
        assert all(p.institution_name == "Interactive Brokers" for p in positions)

    def test_value_parsed_correctly(self):
        positions = self.parser.parse(FIXTURE)
        voo = next(p for p in positions if p.ticker == "VOO")
        assert voo.value == pytest.approx(2000.00)

    def test_account_names_preserved(self):
        positions = self.parser.parse(FIXTURE)
        names = {p.account_name for p in positions}
        assert "Test Trust" in names

    def test_skips_cash_section_rows(self):
        positions = self.parser.parse(FIXTURE)
        # Test Brokerage has no positions, only cash — should not appear
        names = {p.account_name for p in positions}
        assert "Test Brokerage" not in names

    def test_unknown_account_type_when_registry_empty(self):
        positions = self.parser.parse(FIXTURE)
        assert all(p.account_type == "unknown" for p in positions)
        assert all(p.owner == "unknown" for p in positions)

    def test_registry_lookup_used_for_account_type(self):
        reg = _make_registry()
        reg._accounts[("Interactive Brokers", "U22222222")] = Account(
            institution_name="Interactive Brokers",
            account_name="Test Trust",
            account_number="U22222222",
            account_type="trust",
            owner="unknown",
        )
        parser = InteractiveBrokersParser(registry=reg)
        positions = parser.parse(FIXTURE)
        trust_positions = [p for p in positions if p.account_name == "Test Trust"]
        assert all(p.account_type == "trust" for p in trust_positions)
