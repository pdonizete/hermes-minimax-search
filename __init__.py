"""MiniMax web search provider — loaded as an out-of-tree Hermes plugin.

Registers ``MiniMaxWebSearchProvider`` under the name ``minimax``; select it
with ``web.search_backend: minimax`` in config.yaml.
"""

from __future__ import annotations

# ruff: noqa: E402, I001 -- Hermes imports plugin directories without a package name.

import sys
from pathlib import Path

_PLUGIN_DIR = Path(__file__).parent
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from provider import MiniMaxWebSearchProvider  # noqa: E402  # type: ignore[import-not-found]


def register(ctx) -> None:
    ctx.register_web_search_provider(MiniMaxWebSearchProvider())
