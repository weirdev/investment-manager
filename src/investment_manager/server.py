from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import analysis, pipeline
from . import decomposition as decomp

_WEB_DIR = Path(__file__).parent / "web"


def create_app(data_dir: Path, anonymize: bool = False) -> FastAPI:
    app = FastAPI(title="Investment Manager")

    def _load(request_anonymize: bool = False) -> object:
        return pipeline.run(data_dir=data_dir, anonymize=anonymize or request_anonymize)

    @app.get("/api/config")
    def api_config():
        return {"anonymize_locked": anonymize}

    @app.get("/api/positions")
    def api_positions(anonymize: bool = False):
        df = _load(anonymize)
        agg = analysis.aggregate_positions(df)
        total = float(df["value"].sum())
        return {"rows": agg.to_dicts(), "total": total}

    @app.get("/api/concentration")
    def api_concentration(anonymize: bool = False):
        df = _load(anonymize)
        breakdown = analysis.concentration_breakdown(df)
        total = float(df["value"].sum())
        return {"rows": breakdown.to_dicts(), "total": total}

    @app.get("/api/decomposition")
    def api_decomposition(no_account_type: bool = False, anonymize: bool = False):
        df = _load(anonymize)
        compositions = decomp.load_fund_compositions()
        decomposed = decomp.decompose(df, compositions)
        breakdown = analysis.concentration_breakdown(
            decomposed, group_by_account_type=not no_account_type
        )
        total = float(df["value"].sum())
        return {"rows": breakdown.to_dicts(), "total": total}

    @app.get("/api/allocations")
    def api_allocations(anonymize: bool = False):
        df = _load(anonymize)
        breakdown = analysis.allocation_breakdown(df)
        total = float(df["value"].sum())
        return {"rows": breakdown.to_dicts(), "total": total}

    @app.get("/api/owners")
    def api_owners(anonymize: bool = False):
        df = _load(anonymize)
        breakdown = analysis.owner_breakdown(df)
        total = float(df["value"].sum())
        return {"rows": breakdown.to_dicts(), "total": total}

    @app.get("/api/precious-metals")
    def api_precious_metals(anonymize: bool = False):
        df = _load(anonymize)
        breakdown = analysis.precious_metals_by_account(df)
        metals_total = float(breakdown["value"].sum()) if not breakdown.is_empty() else 0.0
        total = float(df["value"].sum())
        return {"rows": breakdown.to_dicts(), "metals_total": metals_total, "total": total}

    @app.get("/")
    def root():
        return RedirectResponse(url="/index.html")

    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="static")

    return app
