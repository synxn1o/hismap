from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="HiSMap Pipeline Review")

# In-memory store for demo. Production would use DB.
pipeline_runs: dict[int, dict] = {}
run_counter = 0


@app.get("/api/review/runs")
async def list_runs():
    return list(pipeline_runs.values())


@app.get("/api/review/runs/{run_id}")
async def get_run(run_id: int):
    run = pipeline_runs.get(run_id)
    if not run:
        return {"error": "Not found"}, 404
    return run


@app.post("/api/review/runs/{run_id}/approve")
async def approve_run(run_id: int):
    run = pipeline_runs.get(run_id)
    if not run:
        return {"error": "Not found"}, 404
    run["human_review_status"] = "approved"
    return run


@app.post("/api/review/runs/{run_id}/reject")
async def reject_run(run_id: int):
    run = pipeline_runs.get(run_id)
    if not run:
        return {"error": "Not found"}, 404
    run["human_review_status"] = "rejected"
    return run


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def review_ui():
        return FileResponse(str(static_dir / "index.html"))
