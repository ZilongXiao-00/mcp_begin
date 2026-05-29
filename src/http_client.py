from dataclasses import dataclass
from typing import Any

import httpx

from src.logger import get_logger


BASE_URL = "https://aihot.virxact.com"
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class UpstreamResult:
    ok: bool
    status: int | None
    data: Any = None
    error: str | None = None


async def upstream_get(
    path: str,
    params: dict[str, str] | None = None,
) -> UpstreamResult:
    logger = get_logger()
    url = f"{BASE_URL}{path}"

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": BROWSER_UA},
            timeout=20.0,
        ) as client:
            response = await client.get(url, params=params)
    except httpx.RequestError as exc:
        logger.error("upstream_request method=GET path=%s status=network_error error=%s", path, exc)
        return UpstreamResult(ok=False, status=None, error=str(exc))

    logger.info("upstream_request method=GET path=%s status=%s", path, response.status_code)

    if response.is_success:
        try:
            return UpstreamResult(ok=True, status=response.status_code, data=response.json())
        except ValueError:
            return UpstreamResult(
                ok=False,
                status=response.status_code,
                error="Upstream returned non-JSON response",
            )

    body = response.text[:1000]
    logger.warning("upstream_error method=GET path=%s status=%s body=%s", path, response.status_code, body)
    return UpstreamResult(ok=False, status=response.status_code, error=body)
