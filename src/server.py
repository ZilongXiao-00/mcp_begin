import json
from typing import Literal

from mcp.server.fastmcp import FastMCP

from src.http_client import upstream_get
from src.logger import get_logger


mcp = FastMCP("aihot-mcp-server")


def format_result(result: object) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


def format_error(status: int | None, error: str | None) -> str:
    if status is None:
        return f"Error: upstream request failed: {error or 'unknown network error'}"
    return f"Error: upstream returned HTTP {status}: {error or ''}"


@mcp.tool()
async def get_daily() -> str:
    """Get the latest AI HOT daily report."""
    logger = get_logger()
    logger.info("tool_call tool=get_daily params={}")

    result = await upstream_get("/api/public/daily")
    if not result.ok:
        return format_error(result.status, result.error)

    return format_result(result.data)


@mcp.tool()
async def get_items(
    mode: Literal["selected", "all"] = "selected",
    category: str | None = None,
    take: int = 10,
    q: str | None = None,
) -> str:
    """Query recent AI HOT items."""
    logger = get_logger()
    logger.info(
        "tool_call tool=get_items params=%s",
        {"mode": mode, "category": category, "take": take, "q": q},
    )

    if mode not in ("selected", "all"):
        return "Error: mode must be 'selected' or 'all'"
    if take < 1 or take > 100:
        return "Error: take must be between 1 and 100"

    params = {"mode": mode, "take": str(take)}
    if category:
        params["category"] = category
    if q:
        params["q"] = q

    result = await upstream_get("/api/public/items", params=params)
    if not result.ok:
        return format_error(result.status, result.error)

    return format_result(result.data)


if __name__ == "__main__":
    mcp.run(transport="stdio")
