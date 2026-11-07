from __future__ import annotations

import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class PharosMcpClient:
    def __init__(self, url: str = "https://mcp.pharos.xyz/mcp") -> None:
        self.url = url

    def _call(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        return asyncio.run(self._call_async(tool_name, arguments))

    async def _call_async(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        async with AsyncExitStack() as stack:
            read_stream, write_stream = await stack.enter_async_context(streamable_http_client(self.url))
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if getattr(result, "isError", False):
                raise RuntimeError(self._result_text(result))
            text = self._result_text(result)
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"MCP returned non-JSON data: {text[:300]}") from exc

    @staticmethod
    def _result_text(result: Any) -> str:
        parts = []
        for item in getattr(result, "content", []) or []:
            if hasattr(item, "text"):
                parts.append(item.text)
        return "\n".join(parts)

    def get_block_number(self) -> int:
        return _extract_int(self._call("get_block_number", {}), "blockNumber")

    def get_logs(self, address: str, topic0: str, from_block: int, to_block: int) -> list[dict]:
        payload = self._call("get_logs", {"address": address, "topics": [topic0],
                                          "fromBlock": from_block, "toBlock": to_block})
        if isinstance(payload, dict) and "error" in payload:
            raise RuntimeError(str(payload["error"]))
        if isinstance(payload, dict):
            payload = payload.get("logs", payload.get("result", []))
        if not isinstance(payload, list):
            raise ValueError("MCP get_logs response did not contain a log list")
        return [item for item in payload if isinstance(item, dict)]

    def get_block_timestamp(self, block_number: int) -> int | None:
        payload = self._call("get_block", {"block": block_number, "includeTransactions": False})
        if isinstance(payload, dict) and "result" in payload:
            payload = payload["result"]
        if not isinstance(payload, dict) or "timestamp" not in payload:
            return None
        return _extract_int(payload, "timestamp")

    def get_decimals(self, contract: str) -> int:
        payload = self._call("eth_call", {"transaction": {"to": contract, "data": "0x313ce567"},
                                           "block": "latest"})
        if isinstance(payload, dict):
            payload = payload.get("result", payload.get("data"))
        return _extract_int(payload, "decimals")


def _extract_int(payload: Any, field: str) -> int:
    value = payload.get(field) if isinstance(payload, dict) else payload
    if isinstance(value, dict) and "result" in value:
        value = value["result"]
    if isinstance(value, str):
        return int(value, 16) if value.startswith("0x") else int(value)
    if isinstance(value, int):
        return value
    raise ValueError(f"MCP response did not contain {field}")
