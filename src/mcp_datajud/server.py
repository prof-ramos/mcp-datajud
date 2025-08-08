from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .client import DataJudClient


app = FastAPI(title="MCP DataJUD", version="0.1.0")


class ExecuteRequest(BaseModel):
    tool_name: str
    params: Dict[str, Any] = {}


class SmitheryCallRequest(BaseModel):
    toolName: str
    toolArgs: Dict[str, Any] | None = None
    sessionId: str | None = None


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/tools")
def tools() -> Any:
    client = DataJudClient(api_key=os.getenv("DATAJUD_API_KEY"))
    return client.list_tools()


@app.post("/execute")
def execute(req: ExecuteRequest) -> Any:
    client = DataJudClient(api_key=os.getenv("DATAJUD_API_KEY"))
    result = client.execute_tool(tool_name=req.tool_name, **req.params)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result


# Smithery-compatible endpoints
@app.get("/api/mcp/tool/list")
def mcp_tool_list(sessionId: str | None = Query(default=None)) -> Any:  # noqa: N803 (Smithery casing)
    client = DataJudClient(api_key=os.getenv("DATAJUD_API_KEY"))
    tools = client.list_tools()
    return {"tools": tools}


@app.post("/api/mcp/tool/call")
def mcp_tool_call(req: SmitheryCallRequest) -> Any:
    client = DataJudClient(api_key=os.getenv("DATAJUD_API_KEY"))
    result = client.execute_tool(tool_name=req.toolName, **(req.toolArgs or {}))
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return {"result": result}
