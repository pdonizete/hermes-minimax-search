"""MiniMax web search provider — loaded as an out-of-tree Hermes plugin.

Registers ``MiniMaxWebSearchProvider`` under the name ``minimax``; select it
with ``web.search_backend: minimax`` in config.yaml.
"""

from __future__ import annotations

from .provider import MiniMaxWebSearchProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(MiniMaxWebSearchProvider())
