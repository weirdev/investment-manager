import csv
import re
from pathlib import Path

from ..models import Position
from ..registry import AccountRegistry
from .base import InstitutionParser

INSTITUTION = "Fidelity"

# Required columns that identify a Fidelity portfolio export
_FIDELITY_REQUIRED_COLS = {"Account Number", "Account Name", "Symbol", "Current Value"}


def _parse_dollar(value: str) -> float | None:
    """Convert a Fidelity dollar string like '$1,234.56' or '+$1,234.56' to float."""
    cleaned = re.sub(r"[+$,]", "", value.strip())
    if not cleaned or cleaned == "--":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _clean_ticker(symbol: str) -> str:
    """Strip trailing asterisks and whitespace from a symbol."""
    return symbol.strip().rstrip("*").strip()


class FidelityParser(InstitutionParser):
    def __init__(self, registry: AccountRegistry | None = None) -> None:
        self._registry = registry or AccountRegistry()

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        """Detect a Fidelity CSV by checking its header columns."""
        try:
            with file_path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = set(reader.fieldnames or [])
            return _FIDELITY_REQUIRED_COLS.issubset(headers)
        except Exception:
            return False

    def parse(self, file_path: Path) -> list[Position]:
        positions: list[Position] = []
        with file_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = (row.get("Symbol") or "").strip()
                if not symbol:
                    continue

                ticker = _clean_ticker(symbol)
                if not ticker:
                    continue

                raw_value = row.get("Current Value") or ""
                value = _parse_dollar(raw_value)
                if value is None:
                    continue

                account_name = (row.get("Account Name") or "").strip()
                account_type = self._registry.validate(INSTITUTION, account_name)

                positions.append(
                    Position(
                        institution_name=INSTITUTION,
                        account_name=account_name,
                        account_type=account_type,
                        ticker=ticker,
                        value=value,
                    )
                )
        return positions
