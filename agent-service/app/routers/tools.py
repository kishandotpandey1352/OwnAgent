from fastapi import APIRouter

from app.tools.registry import list_tool_definitions


router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/list")
def list_tools():
    return {
        "ok": True,
        "tools": [
            tool.model_dump(mode="json") for tool in list_tool_definitions()
        ],
    }