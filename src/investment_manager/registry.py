import csv
import warnings
from pathlib import Path

from .models import Account
from .paths import DEFAULT_ACCOUNTS_PATH


class AccountRegistry:
    def __init__(self, path: Path = DEFAULT_ACCOUNTS_PATH) -> None:
        self._accounts: dict[tuple[str, str], Account] = {}
        if path.exists():
            self._load(path)

    def _load(self, path: Path) -> None:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "institution_name" not in row or "account_number" not in row:
                    continue
                account_number = row["account_number"].strip()
                if not account_number:
                    continue
                key = (row["institution_name"].strip(), account_number)
                self._accounts[key] = Account(
                    institution_name=row["institution_name"].strip(),
                    account_name=row["account_name"].strip(),
                    account_number=account_number,
                    account_type=row["account_type"].strip(),
                    owner=row.get("owner", "").strip() or "unknown",
                )

    def lookup(self, institution_name: str, account_number: str) -> Account | None:
        return self._accounts.get((institution_name, account_number))

    def get_owner(self, institution_name: str, account_number: str) -> str:
        """Return owner from registry, or 'unknown' if not found."""
        account = self.lookup(institution_name, account_number)
        return account.owner if account is not None else "unknown"

    def validate(self, institution_name: str, account_number: str) -> str:
        """Return account_type from registry, or warn and return 'unknown'."""
        account = self.lookup(institution_name, account_number)
        if account is None:
            warnings.warn(
                f"Account not in registry: {institution_name!r} / account #{account_number!r}. "
                "Add it to personal_data/known-accounts.csv to assign an account_type.",
                stacklevel=2,
            )
            return "unknown"
        return account.account_type
