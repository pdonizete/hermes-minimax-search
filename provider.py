"""MiniMax web search via the Token Plan search API.

Search-only: the endpoint returns titles/links/snippets, never page bodies.
Env: ``MINIMAX_API_KEY`` (a Token Plan ``sk-cp-`` credential), or the aliases
``MINIMAX_CODE_PLAN_KEY`` / ``MINIMAX_CODING_API_KEY`` / ``MINIMAX_OAUTH_TOKEN``
checked in that order. ``MINIMAX_REGION=cn`` / ``MINIMAX_API_HOST`` pointing at
``minimaxi.com`` switches to the CN host.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import httpx

from plugins.web._common import (
    SEARCH_LIMIT_CAP, BaseWebSearchProvider, provider_env, run_search, search_fail, search_ok, setup_schema, title_hit,
)

logger = logging.getLogger(__name__)

_ENDPOINT_GLOBAL = "https://api.minimax.io/v1/coding_plan/search"
_ENDPOINT_CN = "https://api.minimaxi.com/v1/coding_plan/search"

# Token Plan credentials live under these names; MINIMAX_API_KEY is last so an
# explicit Token Plan var always wins over the generic model-API key.
_KEY_ENVS = ("MINIMAX_CODE_PLAN_KEY", "MINIMAX_CODING_API_KEY", "MINIMAX_OAUTH_TOKEN", "MINIMAX_API_KEY")

# The search API returns up to 10 organic rows and has no server-side page/count
# knob — the payload is just {"q": ...}. Clamp to the vendor's real ceiling.
_MAX_COUNT = 10


def _resolve_api_key() -> str:
    for name in _KEY_ENVS:
        value = (provider_env(name) or "").strip()
        if value:
            return value
    return ""


def _is_cn_host(value: str) -> bool:
    return "minimaxi.com" in value.strip()


def _resolve_endpoint() -> str:
    """CN when the region or the shared host override says so, else global.

    Mirrors the provider-side host selection so a key minted on one region is
    never POSTed to the other one's endpoint.
    """
    if (provider_env("MINIMAX_REGION") or "").strip().lower() == "cn":
        return _ENDPOINT_CN
    if _is_cn_host(os.environ.get("MINIMAX_API_HOST", "")):
        return _ENDPOINT_CN
    return _ENDPOINT_GLOBAL


def _missing_key_error() -> str:
    return (
        "No MiniMax Token Plan credential found. Set MINIMAX_CODE_PLAN_KEY (or MINIMAX_API_KEY) to an "
        "sk-cp- Token Plan key from https://platform.minimax.io/user-center/basic-information/interface-key. "
        "Ordinary MiniMax model API keys are not accepted by the search endpoint."
    )


def _normalize(data: Dict[str, Any], limit: int) -> Dict[str, Any]:
    """``organic[]`` (title/link/snippet/date) → the shared web_search row shape."""
    rows: List[Dict[str, Any]] = []
    for index, entry in enumerate(data.get("organic") or []):
        if not isinstance(entry, dict):
            continue
        url = (entry.get("link") or "").strip()
        if not url:
            continue
        row = title_hit((entry.get("title") or "").strip(), url, (entry.get("snippet") or "").strip(), index + 1)
        published = (entry.get("date") or "").strip()
        if published:
            row["published"] = published
        rows.append(row)
        if len(rows) >= limit:
            break
    return search_ok(rows)


class MiniMaxWebSearchProvider(BaseWebSearchProvider):
    """MiniMax Token Plan search (keyed; search-only)."""

    NAME = "minimax"
    DISPLAY_NAME = "MiniMax"
    KEY_ENV = "MINIMAX_API_KEY"

    def is_available(self) -> bool:
        return bool(_resolve_api_key())

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        def _body() -> Dict[str, Any]:
            api_key = _resolve_api_key()
            if not api_key:
                return search_fail(_missing_key_error())
            endpoint = _resolve_endpoint()
            cap = min(max(int(limit or 1), 1), _MAX_COUNT, SEARCH_LIMIT_CAP)
            logger.info("MiniMax search: '%s' (limit=%d) via %s", query, cap, endpoint)
            response = httpx.post(
                endpoint,
                json={"q": query},
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            if response.status_code >= 400:
                detail = response.text.strip()[:300]
                return search_fail(f"MiniMax search failed (HTTP {response.status_code}): {detail}")
            data = response.json()
            base = data.get("base_resp") or {}
            # status_code 0 == success; the vendor reports app errors in-body, not via HTTP.
            if base.get("status_code"):
                return search_fail(f"MiniMax search error {base.get('status_code')}: {base.get('status_msg') or 'unknown'}")
            rows = _normalize(data, cap)
            logger.info("MiniMax search: %d results", len(rows.get("data", {}).get("web", [])))
            return rows

        return run_search("MiniMax", logger, _body)

    def get_setup_schema(self) -> Dict[str, Any]:
        return setup_schema(
            "MiniMax", "paid · Token Plan", "Search via the MiniMax Token Plan API. Search-only (no page extraction).",
            "MINIMAX_API_KEY", "MiniMax Token Plan key (sk-cp-…)", "https://platform.minimax.io/user-center/basic-information/interface-key",
        )
