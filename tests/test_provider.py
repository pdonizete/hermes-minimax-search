"""Testes do MiniMaxWebSearchProvider.

Cobre os tres casos que quebram em producao: resposta OK, erro reportado no corpo
(JSON com ``base_resp.status_code``) e corpo nao-JSON (WAF/proxy respondendo HTTP 200
com HTML). Nao faz chamada de rede: o ``httpx.post`` e substituido por um stub.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
# ``plugins.web._common`` vive no checkout do Hermes Agent; quando o plugin roda
# out-of-tree o Hermes ja esta no sys.path. Em CI, aponte HERMES_SRC para o checkout.
HERMES_SRC = os.environ.get("HERMES_SRC")
if HERMES_SRC:
    sys.path.insert(0, HERMES_SRC)

# Import por caminho de arquivo: o diretorio do repo tem hifen e nao e um pacote
# Python valido, entao ``from provider import ...`` so funciona com o path acima —
# mas o pytest pode ter coletado o ``__init__.py`` da raiz antes. Carregar o arquivo
# explicitamente evita depender da ordem de coleta.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("minimax_provider", REPO_ROOT / "provider.py")
_provider = importlib.util.module_from_spec(_spec)
sys.modules["minimax_provider"] = _provider
_spec.loader.exec_module(_provider)
MiniMaxWebSearchProvider = _provider.MiniMaxWebSearchProvider

# O logger real do modulo carregado (o nome depende de como ele foi importado).
LOGGER = _provider.logger


def _stub_post(payload: str, status_code: int = 200):
    def _post(url, json=None, headers=None, timeout=None):
        return httpx.Response(status_code, text=payload)
    return _post


def _search(monkeypatch_payload: str, status_code: int = 200):
    original = httpx.post
    httpx.post = _stub_post(monkeypatch_payload, status_code)
    os.environ["MINIMAX_CODE_PLAN_KEY"] = "sk-cp-test"
    try:
        return MiniMaxWebSearchProvider().search("hermes agent", limit=5)
    finally:
        httpx.post = original
        os.environ.pop("MINIMAX_CODE_PLAN_KEY", None)


def test_search_returns_rows():
    payload = json.dumps({
        "base_resp": {"status_code": 0},
        "organic": [
            {"title": "Hermes", "link": "https://example.test/hermes", "snippet": "agente"},
            {"title": "Docs", "link": "https://example.test/docs", "snippet": "docs"},
        ],
    })
    out = _search(payload)
    assert out["success"] is True, out
    rows = out["data"]["web"]
    assert len(rows) == 2, rows
    assert rows[0]["url"] == "https://example.test/hermes"


def test_search_respects_limit():
    organic = [{"title": f"T{i}", "link": f"https://example.test/{i}", "snippet": "s"}
               for i in range(10)]
    payload = json.dumps({"base_resp": {"status_code": 0}, "organic": organic})
    out = _search(payload)
    assert out["success"] is True
    assert len(out["data"]["web"]) == 5


def test_search_reports_in_body_error():
    payload = json.dumps({"base_resp": {"status_code": 1004, "status_msg": "quota excedido"}})
    out = _search(payload)
    assert out["success"] is False
    assert "quota excedido" in out["error"]


def test_search_http_error():
    out = _search("server exploded", status_code=502)
    assert out["success"] is False
    assert "502" in out["error"]


def test_search_handles_non_json_body():
    """Um WAF/proxy pode responder HTTP 200 com HTML: isso nao pode estourar excecao."""
    out = _search("<html><body>Blocked by WAF</body></html>")
    assert out["success"] is False
    assert "non-JSON" in out["error"]


def test_missing_key_is_a_clean_failure():
    saved = {k: os.environ.pop(k) for k in
             ("MINIMAX_CODE_PLAN_KEY", "MINIMAX_CODING_API_KEY",
              "MINIMAX_OAUTH_TOKEN", "MINIMAX_API_KEY") if k in os.environ}
    try:
        out = MiniMaxWebSearchProvider().search("hermes agent", limit=5)
    finally:
        os.environ.update(saved)
    assert out["success"] is False
    assert "credential" in out["error"].lower()


def test_result_count_log_reads_the_real_path():
    """O log precisa ler ``data.web`` — a forma real do search_ok do Hermes."""
    payload = json.dumps({
        "base_resp": {"status_code": 0},
        "organic": [{"title": "T", "link": "https://example.test/x", "snippet": "s"}],
    })
    records = []

    class _Capture(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = _Capture()
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    try:
        out = _search(payload)
    finally:
        LOGGER.removeHandler(handler)

    counts = [r.getMessage() for r in records if "results" in r.getMessage()]
    assert counts, "nenhum log de contagem emitido"
    assert counts[-1].endswith("1 results"), counts[-1]
    assert out["success"] is True
