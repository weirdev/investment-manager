from pathlib import Path
import os

import uvicorn

from investment_manager.paths import DataPaths
from investment_manager.server import create_app


FIXTURES_DIR = Path(__file__).parent / "fixture_data"


def main() -> None:
    host = os.environ.get("FRONTEND_TEST_HOST", "127.0.0.1")
    port = int(os.environ.get("FRONTEND_TEST_PORT", "8001"))
    app = create_app(data_paths=DataPaths.from_personal_data_dir(FIXTURES_DIR), anonymize=False)
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
