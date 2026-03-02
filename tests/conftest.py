from pathlib import Path

from investment_manager.paths import DataPaths


TEST_PERSONAL_DATA_DIR = Path(__file__).parent / "fixture_data"
TEST_DATA_PATHS = DataPaths.from_personal_data_dir(TEST_PERSONAL_DATA_DIR)
