import csv
import warnings
from pathlib import Path

from .models import Account

_DEFAULT_PATH = Path(__file__).parents[1] / "schemas" / "known-accounts.csv"


class AccountRegistry:
    def __init__(self, path: Path = _DEFAULT_PATH) -> None:
        self._accounts: dict[tuple[str, str], Account] = {}
        if path.exists():
            self._load(path)

    def _load(self, path: Path) -> None:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "institution_name" not in row:
                    continue
                key = (row["institution_name"].strip(), row["account_name"].strip())
                self._accounts[key] = Account(
                    institution_name=row["institution_name"].strip(),
                    account_name=row["account_name"].strip(),
                    account_type=row["account_type"].strip(),
                )

    def lookup(self, institution_name: str, account_name: str) -> Account | None:
        return self._accounts.get((institution_name, account_name))

    def validate(self, institution_name: str, account_name: str) -> str:
        """Return account_type from registry, or warn and return 'unknown'."""
        account = self.lookup(institution_name, account_name)
        if account is None:
            warnings.warn(
                f"Account not in registry: {institution_name!r} / {account_name!r}. "
                "Add it to src/schemas/known-accounts.csv to assign an account_type.",
                stacklevel=2,
            )
            return "unknown"
        return account.account_type
