import asyncio
from datetime import datetime, timezone

from fastmcp import FastMCP

mcp = FastMCP("MCP_Timeout_MCS")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@mcp.tool
async def delay_5s() -> str:
    """Sleep for 5 seconds, then return a confirmation string with the current UTC timestamp.

    Use this to verify that a short-running tool call completes inside the Microsoft Copilot
    Studio MCP timeout window.
    """
    await asyncio.sleep(5)
    return f"Survived 5s — {_utc_now_iso()}"


@mcp.tool
async def delay_10s() -> str:
    """Sleep for 10 seconds, then return a confirmation string with the current UTC timestamp.

    Use this to test whether MCS tolerates a 10-second tool execution before timing out.
    """
    await asyncio.sleep(10)
    return f"Survived 10s — {_utc_now_iso()}"


@mcp.tool
async def delay_30s() -> str:
    """Sleep for 30 seconds, then return a confirmation string with the current UTC timestamp.

    Use this to test whether MCS tolerates a 30-second tool execution before timing out.
    """
    await asyncio.sleep(30)
    return f"Survived 30s — {_utc_now_iso()}"


@mcp.tool
async def delay_60s() -> str:
    """Sleep for 60 seconds, then return a confirmation string with the current UTC timestamp.

    Use this to test whether MCS tolerates a 60-second tool execution before timing out.
    """
    await asyncio.sleep(60)
    return f"Survived 60s — {_utc_now_iso()}"


@mcp.tool
async def delay_90s() -> str:
    """Sleep for 90 seconds, then return a confirmation string with the current UTC timestamp.

    Use this to test whether MCS tolerates a 90-second tool execution before timing out.
    """
    await asyncio.sleep(90)
    return f"Survived 90s — {_utc_now_iso()}"


@mcp.tool
async def delay_120s() -> str:
    """Sleep for 120 seconds, then return a confirmation string with the current UTC timestamp.

    Use this to test whether MCS tolerates a 120-second tool execution before timing out.
    """
    await asyncio.sleep(120)
    return f"Survived 120s — {_utc_now_iso()}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8765)
