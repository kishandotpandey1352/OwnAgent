from fastapi import FastAPI
from app.routers.automation import router as automation_router
from app.routers.governance import router as governance_router
from app.routers.multi_agent_runtime import router as multi_agent_runtime_router

from app.routers.agents import router as agents_router
from app.routers.memory import router as memory_router
from app.routers.tools import router as tools_router
from app.routers.data import router as data_router
from app.routers.facts import (
    router as facts_router,
)
app = FastAPI(
    title="Finance AI Agent Service",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "finance-ai-agent-service",
        "version": "0.1.0",
    }


app.include_router(memory_router)
app.include_router(agents_router)
app.include_router(tools_router)
app.include_router(data_router)
app.include_router(facts_router)
app.include_router(facts_router)
app.include_router(multi_agent_runtime_router)
app.include_router(governance_router)
app.include_router(automation_router)
