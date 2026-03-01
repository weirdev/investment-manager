import csv
from pathlib import Path

from ..models import Position
from ..registry import AccountRegistry
from .base import InstitutionParser
from .utils import parse_dollar

INSTITUTION = "Alight"

_DETECTION_COLS = {"Plan", "Fund Name", "Closing Balance"}


class AlightParser(InstitutionParser):
    def __init__(self, registry: AccountRegistry | None = None) -> None:
        self._registry = registry or AccountRegistry()

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        """Detect an Alight 401(k) export by its header columns."""
        try:
            with file_path.open(newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = set(reader.fieldnames or [])
            return _DETECTION_COLS.issubset(headers)
        except Exception:
            return False

    def parse(self, file_path: Path) -> list[Position]:
        positions: list[Position] = []
        with file_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                plan = (row.get("Plan") or "").strip()
                if not plan:
                    continue

                fund_name = (row.get("Fund Name") or "").strip()
                if not fund_name:
                    continue

                raw_value = row.get("Closing Balance") or ""
                value = parse_dollar(raw_value)
                if value is None or value == 0.0:
                    continue

                account_type = self._registry.validate(INSTITUTION, plan)
                owner = self._registry.get_owner(INSTITUTION, plan)

                positions.append(
                    Position(
                        institution_name=INSTITUTION,
                        account_name=plan,
                        account_number=plan,
                        account_type=account_type,
                        owner=owner,
                        ticker=fund_name,
                        value=value,
                    )
                )
        return positions
