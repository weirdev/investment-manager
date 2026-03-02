from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import analysis, pipeline
from . import decomposition as decomp
from .paths import DEFAULT_DATA_PATHS, DataPaths

_WEB_DIR = Path(__file__).parent / "web"


class ConfigResponse(BaseModel):
    anonymize_locked: bool


class TableResponse(BaseModel):
    rows: list[dict[str, Any]]
    total: float


class PreciousMetalsResponse(TableResponse):
    metals_total: float


def _path_signature(paths: list[Path]) -> tuple[tuple[str, int | None, int | None], ...]:
    signature: list[tuple[str, int | None, int | None]] = []
    seen: set[Path] = set()
    for path in sorted(paths, key=str):
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            stat = path.stat()
            signature.append((str(path), stat.st_mtime_ns, stat.st_size))
        else:
            signature.append((str(path), None, None))
    return tuple(signature)


def create_app(
    data_dir: Path | None = None,
    anonymize: bool = False,
    *,
    data_paths: DataPaths | None = None,
) -> FastAPI:
    data_paths = data_paths or (DataPaths.from_data_dir(data_dir) if data_dir is not None else DEFAULT_DATA_PATHS)
    app = FastAPI(title="Investment Manager")
    pipeline_cache: dict[tuple[bool, tuple[tuple[str, int | None, int | None], ...]], object] = {}
    decomposition_cache: dict[
        tuple[bool, tuple[tuple[str, int | None, int | None], ...], tuple[tuple[str, int | None, int | None], ...]],
        object,
    ] = {}

    def _load(request_anonymize: bool = False):
        effective_anonymize = anonymize or request_anonymize
        signature = _path_signature(data_paths.pipeline_input_paths())
        key = (effective_anonymize, signature)
        if key not in pipeline_cache:
            pipeline_cache[key] = pipeline.run(data_paths=data_paths, anonymize=effective_anonymize)
        return pipeline_cache[key]

    def _load_decomposed(request_anonymize: bool = False):
        effective_anonymize = anonymize or request_anonymize
        pipeline_signature = _path_signature(data_paths.pipeline_input_paths())
        composition_signature = _path_signature([data_paths.compositions_path])
        key = (effective_anonymize, pipeline_signature, composition_signature)
        if key not in decomposition_cache:
            df = _load(request_anonymize)
            compositions = decomp.load_fund_compositions(data_paths.compositions_path)
            decomposition_cache[key] = decomp.decompose(df, compositions)
        return decomposition_cache[key]

    @app.get("/api/config", response_model=ConfigResponse)
    def api_config() -> ConfigResponse:
        return {"anonymize_locked": anonymize}

    @app.get("/api/positions", response_model=TableResponse)
    def api_positions(anonymize: bool = False, by_retirement: bool = False) -> TableResponse:
        df = _load(anonymize)
        agg = analysis.aggregate_positions(df, by_retirement=by_retirement)
        total = float(df["value"].sum())
        return {"rows": agg.to_dicts(), "total": total}

    @app.get("/api/concentration", response_model=TableResponse)
    def api_concentration(anonymize: bool = False, by_retirement: bool = False) -> TableResponse:
        df = _load(anonymize)
        breakdown = analysis.concentration_breakdown(df, by_retirement=by_retirement)
        total = float(df["value"].sum())
        return {"rows": breakdown.to_dicts(), "total": total}

    @app.get("/api/decomposition", response_model=TableResponse)
    def api_decomposition(
        no_account_type: bool = False, anonymize: bool = False, by_retirement: bool = False
    ) -> TableResponse:
        df = _load(anonymize)
        decomposed = _load_decomposed(anonymize)
        breakdown = analysis.concentration_breakdown(
            decomposed, group_by_account_type=not no_account_type, by_retirement=by_retirement
        )
        total = float(df["value"].sum())
        return {"rows": breakdown.to_dicts(), "total": total}

    @app.get("/api/allocations", response_model=TableResponse)
    def api_allocations(anonymize: bool = False, by_retirement: bool = False) -> TableResponse:
        df = _load(anonymize)
        breakdown = analysis.allocation_breakdown(df, by_retirement=by_retirement)
        total = float(df["value"].sum())
        return {"rows": breakdown.to_dicts(), "total": total}

    @app.get("/api/owners", response_model=TableResponse)
    def api_owners(anonymize: bool = False) -> TableResponse:
        df = _load(anonymize)
        breakdown = analysis.owner_breakdown(df)
        total = float(df["value"].sum())
        return {"rows": breakdown.to_dicts(), "total": total}

    @app.get("/api/precious-metals", response_model=PreciousMetalsResponse)
    def api_precious_metals(anonymize: bool = False, by_retirement: bool = False) -> PreciousMetalsResponse:
        df = _load(anonymize)
        breakdown = analysis.precious_metals_by_account(df, by_retirement=by_retirement)
        metals_total = float(breakdown["value"].sum()) if not breakdown.is_empty() else 0.0
        total = float(df["value"].sum())
        return {"rows": breakdown.to_dicts(), "metals_total": metals_total, "total": total}

    @app.get("/")
    def root():
        return RedirectResponse(url="/index.html")

    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="static")

    return app
