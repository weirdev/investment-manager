from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]  # src/investment_manager/ → project root
PERSONAL_DATA_DIR = PROJECT_ROOT / "personal_data"
DEFAULT_DATA_DIR = PERSONAL_DATA_DIR / "raw_account_details"
DEFAULT_METADATA_PATH = PERSONAL_DATA_DIR / "asset-metadata.csv"
DEFAULT_ACCOUNTS_PATH = PERSONAL_DATA_DIR / "known-accounts.csv"
DEFAULT_COMPOSITIONS_PATH = PERSONAL_DATA_DIR / "fund-compositions.csv"
