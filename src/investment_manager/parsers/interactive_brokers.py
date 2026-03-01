import csv
from pathlib import Path

from ..models import Position
from ..registry import AccountRegistry
from .base import InstitutionParser

INSTITUTION = "Interactive Brokers"

# Columns in the first (cash) header row — used for detection
_DETECTION_COLS = {"ClientAccountID", "AccountAlias", "Cash", "CashLong", "CashShort"}


def _parse_float(value: str) -> float | None:
    """Convert a plain float string like '29508.75' to float."""
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


class InteractiveBrokersParser(InstitutionParser):
    def __init__(self, registry: AccountRegistry | None = None) -> None:
        self._registry = registry or AccountRegistry()

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        """Detect an IB Flex Query positions export by its first header row."""
        try:
            with file_path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                first_row = next(reader, None)
            if first_row is None:
                return False
            return _DETECTION_COLS.issubset(set(first_row))
        except Exception:
            return False

    def parse(self, file_path: Path) -> list[Position]:
        positions: list[Position] = []
        in_position_section = False
        position_headers: list[str] = []

        with file_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue

                # Header rows always have "ClientAccountID" as the first field
                if row[0] == "ClientAccountID":
                    in_position_section = "Symbol" in row
                    if in_position_section:
                        position_headers = row
                    continue

                if not in_position_section or not position_headers:
                    continue

                data = dict(zip(position_headers, row))

                symbol = data.get("Symbol", "").strip()
                if not symbol:
                    continue

                raw_value = data.get("PositionValue", "").strip()
                value = _parse_float(raw_value)
                if value is None:
                    continue

                account_name = data.get("AccountAlias", "").strip()
                account_type = self._registry.validate(INSTITUTION, account_name)
                owner = self._registry.get_owner(INSTITUTION, account_name)

                positions.append(
                    Position(
                        institution_name=INSTITUTION,
                        account_name=account_name,
                        account_type=account_type,
                        owner=owner,
                        ticker=symbol,
                        value=value,
                    )
                )

        return positions
