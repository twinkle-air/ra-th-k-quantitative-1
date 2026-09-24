#!/usr/bin/env python3
"""Minimal stdio MCP adapter for the deterministic Ra-Th-K tools."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from start_app import APP_ROOT, choose_python


def _bootstrap() -> None:
    if os.environ.get("RTK_MCP_BOOTSTRAPPED") == "1":
        return
    python = choose_python(False)
    if Path(sys.executable).resolve() == python.resolve():
        return
    environment = dict(os.environ)
    environment["RTK_MCP_BOOTSTRAPPED"] = "1"
    raise SystemExit(subprocess.call([str(python), str(Path(__file__).resolve())], env=environment))


def _write(message: dict) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> int:
    _bootstrap()
    sys.path.insert(0, str(APP_ROOT))
    from app.services.agent_tools import invoke_tool, tool_registry
    from app.version import SKILL_VERSION

    registry = tool_registry()
    definitions = {item["name"]: item for item in registry["tools"]}
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            method = request.get("method")
            request_id = request.get("id")
            if method == "initialize":
                response = {
                    "protocolVersion": request.get("params", {}).get("protocolVersion", "2025-11-25"),
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "ra-th-k-quantitative-1", "version": SKILL_VERSION},
                }
            elif method == "ping":
                response = {}
            elif method == "tools/list":
                response = {"tools": [{
                    "name": item["name"], "description": item["description"],
                    "inputSchema": {"$defs": registry["$defs"], **item["inputSchema"]},
                    "outputSchema": {"$defs": registry["$defs"], **item["outputSchema"]},
                    "annotations": {"readOnlyHint": item["name"] != "export_report", "openWorldHint": False},
                } for item in registry["tools"]]}
            elif method == "tools/call":
                params = request.get("params") or {}
                name = params.get("name")
                if name not in definitions:
                    raise KeyError(f"Unknown tool: {name}")
                result = invoke_tool(name, params.get("arguments") or {})
                serialized = json.dumps(result, ensure_ascii=False, allow_nan=False)
                response = {
                    "content": [{"type": "text", "text": serialized}],
                    "structuredContent": result,
                    "isError": result.get("status") == "error",
                }
            elif method and method.startswith("notifications/"):
                continue
            else:
                raise KeyError(f"Unknown method: {method}")
            if request_id is not None:
                _write({"jsonrpc": "2.0", "id": request_id, "result": response})
        except Exception as exc:  # Protocol boundary: always return a JSON-RPC error.
            request_id = locals().get("request", {}).get("id")
            if request_id is not None:
                _write({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": str(exc)}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
