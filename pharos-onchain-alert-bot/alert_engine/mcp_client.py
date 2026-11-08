from __future__ import annotations

import json
import urllib.request


class MCPError(RuntimeError):
    pass


class PharosMCPClient:
    def __init__(self, endpoint: str = "https://mcp.pharos.xyz/mcp", timeout: float = 20) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self._request_id = 0

    def call(self, tool: str, arguments: dict) -> object:
        self._request_id += 1
        body = {"jsonrpc": "2.0", "id": self._request_id, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
        request = urllib.request.Request(self.endpoint, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read())
        except Exception as exc:
            raise MCPError(str(exc)) from exc
        if "error" in payload:
            raise MCPError(str(payload["error"]))
        result = payload.get("result", {})
        if isinstance(result, dict) and result.get("isError"):
            raise MCPError(str(result))
        content = result.get("content", []) if isinstance(result, dict) else []
        if content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except json.JSONDecodeError:
                return content[0]["text"]
        return result

    def chain_info(self) -> object:
        return self.call("get_chain_info", {})

    def block_number(self) -> int:
        value = self.call("get_block_number", {})
        value = value.get("blockNumber", value) if isinstance(value, dict) else value
        return int(value, 16) if isinstance(value, str) and value.startswith("0x") else int(value)

    def logs(self, address: str, topic: str, from_block: int, to_block: int) -> list[dict]:
        value = self.call("get_logs", {"address": address, "topics": [topic], "fromBlock": from_block, "toBlock": to_block})
        return value if isinstance(value, list) else value.get("logs", [])

    def token_decimals(self, address: str) -> int:
        value = self.call("eth_call", {"transaction": {"to": address, "data": "0x313ce567"}, "block": "latest"})
        raw = value.get("result", value) if isinstance(value, dict) else value
        return int(raw, 16) if isinstance(raw, str) else int(raw)