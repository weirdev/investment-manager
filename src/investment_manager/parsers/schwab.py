import csv
import io
import re
from pathlib import Path

from ..models import Position
from ..registry import AccountRegistry
from .base import InstitutionParser
from .utils import parse_dollar

INSTITUTION = "Schwab"

_SKIP_SYMBOLS = {"Cash & Cash Investments", "Account Total", ""}


def _is_account_name_line(line: str) -> bool:
    """Schwab account name lines are unquoted and contain '...' before the last 4 digits."""
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith('"') and "..." in stripped


def _extract_account_number(account_name_line: str) -> str:
    """Extract the digits after '...' from a Schwab account name line (e.g. '718' from 'W_Fam_Trust_1 ...718')."""
    m = re.search(r"\.\.\.(\w+)", account_name_line)
    return m.group(1) if m else account_name_line.strip()


class SchwabParser(InstitutionParser):
    def __init__(self, registry: AccountRegistry | None = None) -> None:
        self._registry = registry or AccountRegistry()

    @classmethod
    def can_parse(cls, file_path: Path) -> bool:
        """Detect a Schwab positions export by its first-line header."""
        try:
            with file_path.open(encoding="utf-8-sig") as f:
                first_line = f.readline().strip()
            return first_line.startswith('"Positions for')
        except Exception:
            return False

    def parse(self, file_path: Path) -> list[Position]:
        positions: list[Position] = []
        current_account_name = ""
        current_account_number = ""
        current_headers: list[str] = []

        with file_path.open(encoding="utf-8-sig") as f:
            for line in f:
                line = line.rstrip("\n\r")

                if _is_account_name_line(line):
                    current_account_name = line.strip()
                    current_account_number = _extract_account_number(line)
                    current_headers = []
                    continue

                # Capture per-account column headers
                if line.startswith('"Symbol"'):
                    try:
                        current_headers = next(csv.reader(io.StringIO(line)))
                    except StopIteration:
                        pass
                    continue

                # Skip blank lines and the global header
                if not line.strip() or line.startswith('"Positions for'):
                    continue

                if not current_headers:
                    continue

                try:
                    row = next(csv.reader(io.StringIO(line)))
                except StopIteration:
                    continue

                if not row:
                    continue

                symbol = row[0].strip()
                if symbol in _SKIP_SYMBOLS:
                    continue

                data = dict(zip(current_headers, row))
                value = parse_dollar(data.get("Mkt Val (Market Value)", ""))
                if value is None:
                    continue

                account_type = self._registry.validate(INSTITUTION, current_account_number)
                owner = self._registry.get_owner(INSTITUTION, current_account_number)
                positions.append(
                    Position(
                        institution_name=INSTITUTION,
                        account_name=current_account_name,
                        account_number=current_account_number,
                        account_type=account_type,
                        owner=owner,
                        ticker=symbol,
                        value=value,
                    )
                )

        return positions
