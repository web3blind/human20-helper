from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_MCP_URL = "https://human20.app/mcp"


def _load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class Human20McpClient:
    def __init__(self, base_url: str | None = None, bearer_token: str | None = None) -> None:
        _load_local_env()
        self.base_url = base_url or os.environ.get("HUMAN20_MCP_URL", DEFAULT_MCP_URL)
        self.bearer_token = bearer_token or os.environ.get("HUMAN20_BEARER_TOKEN")
        if not self.bearer_token:
            raise RuntimeError("HUMAN20_BEARER_TOKEN is required")

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": "human20-helper",
            "method": method,
            "params": params or {},
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            self.base_url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        try:
            with request.urlopen(req, timeout=30) as response:
                data = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Human20 MCP HTTP {exc.code}: {details}") from exc

        decoded = json.loads(data)
        if "error" in decoded:
            raise RuntimeError(json.dumps(decoded["error"], ensure_ascii=False))
        return decoded

    def initialize(self) -> dict[str, Any]:
        return self.call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "human20-helper", "version": "0.1.0"},
            },
        )

    def list_tools(self) -> dict[str, Any]:
        return self.call("tools/list")

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.call("tools/call", {"name": name, "arguments": arguments or {}})

    def structured_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        result = self.call_tool(name, arguments).get("result", {})
        if "structuredContent" in result:
            return result["structuredContent"]
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Call Human20 MCP")
    parser.add_argument("method", help="JSON-RPC method or tools/call")
    parser.add_argument("--tool")
    parser.add_argument("--args", default="{}")
    args = parser.parse_args()

    client = Human20McpClient()
    if args.method == "tools/call":
        if not args.tool:
            parser.error("--tool is required for tools/call")
        result = client.call_tool(args.tool, json.loads(args.args))
    else:
        result = client.call(args.method, json.loads(args.args))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
