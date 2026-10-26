"""MiniMax web search provider — loaded as an out-of-tree Hermes plugin.

Registers ``MiniMaxWebSearchProvider`` under the name ``minimax``; select it
with ``web.search_backend: minimax`` in config.yaml.
"""

from __future__ import annotations

try:
    # Import normal, quando o Hermes carrega o plugin como pacote.
    from .provider import MiniMaxWebSearchProvider
except ImportError:  # pragma: no cover - import isolado (pytest, tooling)
    # O diretorio do repo tem hifen e nao e um pacote Python valido, entao este
    # arquivo pode ser importado SEM contexto de pacote (ex.: pytest coletando a
    # raiz). Nesse caso o import relativo falha e carregamos o modulo por caminho.
    import importlib.util
    from pathlib import Path

    _spec = importlib.util.spec_from_file_location(
        "minimax_provider", Path(__file__).resolve().parent / "provider.py"
    )
    _provider = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_provider)
    MiniMaxWebSearchProvider = _provider.MiniMaxWebSearchProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(MiniMaxWebSearchProvider())
