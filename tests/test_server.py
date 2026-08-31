from pathlib import Path
from unittest.mock import patch

import polars as pl

from investment_manager.paths import DataPaths
from investment_manager.server import create_app

from .conftest import TEST_DATA_PATHS


def _sample_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "institution_name": ["Fidelity"],
            "account_name": ["Brokerage"],
            "account_number": ["X11111111"],
            "account_type": ["brokerage"],
            "owner": ["john"],
            "is_retirement": [False],
            "ticker": ["AAPL"],
            "value": [1000.0],
            "canonical_ticker": ["AAPL"],
            "asset_class": ["equities"],
            "security_type": ["stock"],
            "market_segment": ["large_cap"],
            "region": ["us"],
        }
    )


class TestCreateAppCaching:
    def test_positions_cache_reuses_pipeline_result_for_identical_requests(self):
        app = create_app(data_paths=TEST_DATA_PATHS)
        df = _sample_df()
        positions = next(route.endpoint for route in app.routes if getattr(route, "path", None) == "/api/positions")

        with patch("investment_manager.server.pipeline.run", return_value=df) as run_mock:
            first = positions()
            second = positions()

        assert first["total"] == 1000.0
        assert second["total"] == 1000.0
        assert run_mock.call_count == 1

    def test_pipeline_cache_invalidates_when_input_file_changes(self, tmp_path: Path):
        personal_root = tmp_path / "personal_data"
        raw_dir = personal_root / "raw_account_details" / "john" / "fidelity"
        raw_dir.mkdir(parents=True)
        raw_file = raw_dir / "sample.csv"
        raw_file.write_text("Account Number,Account Name,Symbol,Current Value\n", encoding="utf-8")
        (personal_root / "known-accounts.csv").write_text("", encoding="utf-8")
        (personal_root / "asset-metadata.csv").write_text("", encoding="utf-8")

        app = create_app(data_paths=DataPaths.from_personal_data_dir(personal_root))
        df = _sample_df()
        positions = next(route.endpoint for route in app.routes if getattr(route, "path", None) == "/api/positions")

        with patch("investment_manager.server.pipeline.run", return_value=df) as run_mock:
            positions()
            raw_file.write_text(
                "Account Number,Account Name,Symbol,Current Value\n"
                "X11111111,Brokerage,AAPL,$1000.00\n",
                encoding="utf-8",
            )
            positions()

        assert run_mock.call_count == 2

    def test_rebalancing_returns_four_tier_rows_and_caches(self):
        app = create_app(data_paths=TEST_DATA_PATHS)
        df = _sample_df()
        rebalancing = next(
            route.endpoint for route in app.routes if getattr(route, "path", None) == "/api/rebalancing"
        )

        with patch("investment_manager.server.pipeline.run", return_value=df) as run_mock:
            first = rebalancing()
            second = rebalancing()

        assert run_mock.call_count == 1
        assert set(first) == {"market_cap", "regions", "total", "equity_total"}
        assert first["equity_total"] == 1000.0
        assert [r["market_cap_tier"] for r in first["market_cap"]] == [
            "large_cap",
            "mid_cap",
            "small_cap",
            "emerging",
        ]
        assert len(first["regions"]) == 7
        assert second["market_cap"] == first["market_cap"]

    def test_rebalancing_by_retirement_tags_rows(self):
        app = create_app(data_paths=TEST_DATA_PATHS)
        df = _sample_df()
        rebalancing = next(
            route.endpoint for route in app.routes if getattr(route, "path", None) == "/api/rebalancing"
        )

        with patch("investment_manager.server.pipeline.run", return_value=df):
            result = rebalancing(by_retirement=True)

        assert all("is_retirement" in r for r in result["market_cap"])
        assert all("is_retirement" in r for r in result["regions"])
        assert {r["is_retirement"] for r in result["market_cap"]} == {False}
        assert len(result["market_cap"]) == 4
        assert len(result["regions"]) == 7
