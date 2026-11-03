from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from research_runner.application.ablation_study import StudyConfig, run_study
from research_runner.domain.report_generator import generate_latex_table
from research_runner.infrastructure.dataset_file import load_samples
from research_runner.infrastructure.report_files import read_report, reports_dir, write_report
from scan_orchestrator.api.research_guard import require_research_reader, require_study_runner

app = FastAPI(
    title="Verifica AI — Research Runner API",
    description="Internal API to run the ablation study and serve its latest report.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "research-runner"}


@app.get("/pesquisa/report", dependencies=[Depends(require_research_reader)])
async def latest_report() -> dict[str, Any]:
    report = read_report(reports_dir())
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No study has been run yet.")
    return {**report, "latex_table": generate_latex_table(report["modes"])}


# Admin only: the study is heavy and, with Gemini, paid.
@app.post("/pesquisa/run", dependencies=[Depends(require_study_runner)])
async def run_pesquisa() -> dict[str, Any]:
    report = await run_study(load_samples(), StudyConfig())
    write_report(report, reports_dir())
    return report
