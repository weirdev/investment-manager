import csv
import pytest
from pathlib import Path

from investment_manager.registry import AccountRegistry


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture()
def registry_csv(tmp_path):
    p = tmp_path / "known-accounts.csv"
    _write_csv(
        p,
        [
            {
                "institution_name": "Fidelity",
                "account_name": "Brokerage",
                "account_number": "Z123",
                "account_type": "taxable",
                "owner": "alice",
            },
            {
                "institution_name": "Schwab",
                "account_name": "IRA",
                "account_number": "S456",
                "account_type": "ira",
                "owner": "bob",
            },
        ],
    )
    return p


class TestAccountRegistryLoad:
    def test_loads_accounts_from_valid_csv(self, registry_csv):
        reg = AccountRegistry(path=registry_csv)
        assert reg.lookup("Fidelity", "Z123") is not None
        assert reg.lookup("Schwab", "S456") is not None

    def test_correct_fields(self, registry_csv):
        reg = AccountRegistry(path=registry_csv)
        acct = reg.lookup("Fidelity", "Z123")
        assert acct is not None
        assert acct.institution_name == "Fidelity"
        assert acct.account_name == "Brokerage"
        assert acct.account_number == "Z123"
        assert acct.account_type == "taxable"
        assert acct.owner == "alice"

    def test_missing_file_returns_empty_registry(self, tmp_path):
        reg = AccountRegistry(path=tmp_path / "nonexistent.csv")
        assert reg.lookup("Fidelity", "Z123") is None

    def test_skips_rows_with_blank_account_number(self, tmp_path):
        p = tmp_path / "known-accounts.csv"
        _write_csv(
            p,
            [
                {
                    "institution_name": "Fidelity",
                    "account_name": "Brokerage",
                    "account_number": "",
                    "account_type": "taxable",
                    "owner": "alice",
                },
            ],
        )
        reg = AccountRegistry(path=p)
        assert reg.lookup("Fidelity", "") is None


class TestAccountRegistryLookup:
    def test_returns_account_for_known(self, registry_csv):
        reg = AccountRegistry(path=registry_csv)
        assert reg.lookup("Fidelity", "Z123") is not None

    def test_returns_none_for_unknown(self, registry_csv):
        reg = AccountRegistry(path=registry_csv)
        assert reg.lookup("Fidelity", "UNKNOWN") is None


class TestAccountRegistryValidate:
    def test_returns_account_type_for_known(self, registry_csv):
        reg = AccountRegistry(path=registry_csv)
        assert reg.validate("Fidelity", "Z123") == "taxable"

    def test_warns_and_returns_unknown_for_unregistered(self, registry_csv):
        reg = AccountRegistry(path=registry_csv)
        with pytest.warns(UserWarning, match="Account not in registry"):
            result = reg.validate("Fidelity", "UNKNOWN")
        assert result == "unknown"


class TestAccountRegistryGetOwner:
    def test_returns_owner_for_known(self, registry_csv):
        reg = AccountRegistry(path=registry_csv)
        assert reg.get_owner("Schwab", "S456") == "bob"

    def test_returns_unknown_for_unregistered(self, registry_csv):
        reg = AccountRegistry(path=registry_csv)
        assert reg.get_owner("Schwab", "UNKNOWN") == "unknown"
