from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]  # src/investment_manager/ → project root
PERSONAL_DATA_DIR = PROJECT_ROOT / "personal_data"


@dataclass(frozen=True)
class DataPaths:
    personal_data_dir: Path
    raw_account_details_dir: Path
    accounts_path: Path
    metadata_path: Path
    compositions_path: Path

    @classmethod
    def from_personal_data_dir(cls, personal_data_dir: Path) -> "DataPaths":
        return cls(
            personal_data_dir=personal_data_dir,
            raw_account_details_dir=personal_data_dir / "raw_account_details",
            accounts_path=personal_data_dir / "known-accounts.csv",
            metadata_path=personal_data_dir / "asset-metadata.csv",
            compositions_path=personal_data_dir / "fund-compositions.csv",
        )

    @classmethod
    def from_data_dir(cls, raw_account_details_dir: Path) -> "DataPaths":
        return cls(
            personal_data_dir=raw_account_details_dir.parent,
            raw_account_details_dir=raw_account_details_dir,
            accounts_path=raw_account_details_dir.parent / "known-accounts.csv",
            metadata_path=raw_account_details_dir.parent / "asset-metadata.csv",
            compositions_path=raw_account_details_dir.parent / "fund-compositions.csv",
        )

    def mapping_dir_for_institution(self, institution_name: str) -> Path:
        return self.personal_data_dir / institution_name

    def discover_mapping_paths(self) -> list[Path]:
        """Find *-asset-mapping.csv files for institutions that have raw CSVs."""
        paths: list[Path] = []
        if not self.raw_account_details_dir.exists():
            return paths

        seen_institutions: set[str] = set()
        for owner_dir in sorted(self.raw_account_details_dir.iterdir()):
            if not owner_dir.is_dir():
                continue
            for institution_dir in sorted(owner_dir.iterdir()):
                if not institution_dir.is_dir() or not any(institution_dir.glob("*.csv")):
                    continue
                if institution_dir.name in seen_institutions:
                    continue
                seen_institutions.add(institution_dir.name)
                paths.extend(sorted(self.mapping_dir_for_institution(institution_dir.name).glob("*-asset-mapping.csv")))
        return paths

    def pipeline_input_paths(self) -> list[Path]:
        raw_files = sorted(self.raw_account_details_dir.rglob("*.csv")) if self.raw_account_details_dir.exists() else []
        return [
            *raw_files,
            self.accounts_path,
            self.metadata_path,
            *self.discover_mapping_paths(),
        ]

    def decomposition_input_paths(self) -> list[Path]:
        return [*self.pipeline_input_paths(), self.compositions_path]


DEFAULT_DATA_PATHS = DataPaths.from_personal_data_dir(PERSONAL_DATA_DIR)
DEFAULT_DATA_DIR = DEFAULT_DATA_PATHS.raw_account_details_dir
DEFAULT_METADATA_PATH = DEFAULT_DATA_PATHS.metadata_path
DEFAULT_ACCOUNTS_PATH = DEFAULT_DATA_PATHS.accounts_path
DEFAULT_COMPOSITIONS_PATH = DEFAULT_DATA_PATHS.compositions_path
