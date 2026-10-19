from dataclasses import asdict
from typing import Any, Dict, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from research_runner.application.benchmark_service import BenchmarkService
from research_runner.domain.ablation_models import AblationMode
from research_runner.domain.report_generator import (
    generate_markdown_table,
    generate_latex_table,
    generate_full_tcc_report,
)


app = FastAPI(
    title="Verifica AI — Research Runner API",
    description="API interna para execução de benchmarks de ablação, cálculo de métricas para TCC e observabilidade.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = BenchmarkService()


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "service": "research-runner"}


@app.get("/pesquisa")
async def get_pesquisa_summary() -> Dict[str, Any]:
    evaluations = service.run_all_modes()
    md_table = generate_markdown_table(evaluations)
    latex_table = generate_latex_table(evaluations)
    full_report = generate_full_tcc_report(evaluations)

    evals_data = []
    for ev in evaluations:
        evals_data.append({
            "mode": ev.mode.value,
            "metrics": asdict(ev.metrics),
            "stage_breakdown": ev.stage_breakdown,
        })

    return {
        "markdown_table": md_table,
        "latex_table": latex_table,
        "full_report": full_report,
        "evaluations": evals_data,
    }


@app.post("/pesquisa/run")
async def run_pesquisa(
    mode: str = Query("cascade", description="Modo de ablação ('heuristic', 'classical_nlp', 'pure_vlm', 'cascade', 'all')")
) -> Dict[str, Any]:
    if mode == "all":
        evaluations = service.run_all_modes()
        return {
            "evaluations": [
                {
                    "mode": ev.mode.value,
                    "metrics": asdict(ev.metrics),
                    "stage_breakdown": ev.stage_breakdown,
                }
                for ev in evaluations
            ],
            "markdown_table": generate_markdown_table(evaluations),
            "latex_table": generate_latex_table(evaluations),
        }

    mode_enum = AblationMode(mode)
    ev = service.run_mode(mode_enum)
    return {
        "mode": ev.mode.value,
        "metrics": asdict(ev.metrics),
        "stage_breakdown": ev.stage_breakdown,
    }
