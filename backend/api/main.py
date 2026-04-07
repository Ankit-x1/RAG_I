from fastapi import BackgroundTasks, FastAPI, Query


app = FastAPI(
    title="RAG Backend",
    version="0.1.0",
    description="Minimal API for health checks and indexing control.",
)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/index")
async def trigger_indexing(
    background_tasks: BackgroundTasks,
    wait: bool = Query(
        default=False,
        description="Run indexing inline instead of in the background.",
    ),
) -> dict[str, str]:
    from backend.indexing.pipeline import run_indexing

    if wait:
        await run_indexing()
        return {"status": "completed"}

    background_tasks.add_task(run_indexing)
    return {"status": "scheduled"}
