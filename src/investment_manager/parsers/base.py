from abc import ABC, abstractmethod
from pathlib import Path

from ..models import Position


class InstitutionParser(ABC):
    @classmethod
    @abstractmethod
    def can_parse(cls, file_path: Path) -> bool:
        """Return True if this parser can handle the given file."""

    @abstractmethod
    def parse(self, file_path: Path) -> list[Position]:
        """Parse the file and return a list of normalized Position objects."""
