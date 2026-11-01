from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from decode import decode_string, decode_uint256, format_units

MCP_URL = os.getenv("PHAROS_MCP_URL", "https://mcp.pharos.xyz/mcp")
CONTRACT = "0xc879c018db60520f4355c26ed1a6d572cdac1815"


@dataclass(frozen=True)
class Read:
    selector: str
    decoder: object


READS = {
    "name": Read("0x06fdde03", decode_string),
    "symbol": Read("0x95d89b41", decode_string),
    "totalSupply": Read("0x18160ddd", decode_uint256),
    "decimals": Read("0x313ce567", decode_uint256),
}


async def call_tool(name: str, arguments: dict) -> dict:
    async with streamable_http_client(MCP_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            response = await asyncio.wait_for(session.call_tool(name, arguments), timeout=15)
    text = next((item.text for item in response.content if hasattr(item, "text")), None)
    if not text:
        raise RuntimeError(f"{name} returned no text content")
    parsed = json.loads(text)
    if "error" in parsed:
        raise RuntimeError(f"{name}: {parsed['error']}")
    return parsed


async def inspect() -> None:
    print(f"Connecting to {MCP_URL}...", flush=True)
    print("Reading block number...", flush=True)
    block_response = await call_tool("get_block_number", {})
    block_number = int(block_response["blockNumber"])

    values = {}
    for label, read in READS.items():
        print(f"Reading {label}...", flush=True)
        response = await call_tool(
            "eth_call",
            {"transaction": {"to": CONTRACT, "data": read.selector}, "block": block_number},
        )
        raw = response.get("result")
        if not isinstance(raw, str) or raw == "0x":
            raise RuntimeError(f"{label} returned empty data")
        values[label] = (raw, read.decoder(raw))

    decimals = values["decimals"][1]
    print("Network: Pharos Pacific Mainnet (chain ID 1672)")
    print(f"Contract address: {CONTRACT}")
    print(f"Block number: {block_number}")
    print(f"Name: {values['name'][1]}")
    print(f"Symbol: {values['symbol'][1]}")
    print(f"Decimals: {decimals}")
    print(f"Total supply: {format_units(values['totalSupply'][1], decimals)} {values['symbol'][1]}")
    print(f"Raw total supply: {values['totalSupply'][1]}")


if __name__ == "__main__":
    try:
        asyncio.run(inspect())
    except Exception as exc:
        print(f"Inspection failed: {exc}")
        raise SystemExit(1)