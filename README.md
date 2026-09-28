# Hermes MiniMax Web Search Plugin

A web search provider plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) that uses the **MiniMax API** (Token Plan, `sk-cp-` keys) as a search backend.

## Why this exists

- SearXNG and other metasearch engines depend on third-party search engines (Brave, Google, Startpage, DuckDuckGo) that aggressively rate-limit or CAPTCHA datacenter IPs.
- The MiniMax API (coding plan search endpoint) returns clean Portuguese/English results **without CAPTCHA**, **without rate-limiting by IP**, and **without relying on third-party engines**.
- If you already have a MiniMax Token Plan subscription (the same plan used for chat, vision, and music generation), you get web search "for free" — no extra cost, no extra API key.

## Requirements

- **MiniMax Token Plan** subscription (API key starts with `sk-cp-` — standard model keys do NOT work for search).
- Hermes Agent ≥ 0.21.3.

## Installation

### From the catalog (once merged)

```bash
hermes plugins install minimax-search
```

### Manual (out-of-tree, for testing)

```bash
# Clone this repo
git clone https://github.com/pdonizete/hermes-minimax-search
cd hermes-minimax-search

# Copy to your Hermes plugins directory
cp -r . ~/.hermes/plugins/minimax-search/

# Add your MiniMax API key to ~/.hermes/.env
echo 'MINIMAX_API_KEY=sk-cp-YOUR_KEY_HERE' >> ~/.hermes/.env

# Configure Hermes to use MiniMax as search backend
hermes config set web.search_backend minimax
hermes config set plugins.enabled '["minimax-search"]'

# Restart Hermes gateway
systemctl --user restart hermes-gateway.service
```

## Configuration

The plugin reads these environment variables (in order of precedence):

| Variable | Required | Description |
|----------|----------|-------------|
| `MINIMAX_API_KEY` | **Yes** | Your MiniMax Token Plan API key (`sk-cp-...`). |
| `MINIMAX_REGION` | No | Set to `cn` to use the Chinese endpoint (`api.minimaxi.com`). Defaults to global (`api.minimax.io`). |
| `MINIMAX_API_HOST` | No | Override the full API host. Takes precedence over `MINIMAX_REGION`. |

## How it works

- Endpoint: `POST https://api.minimax.io/v1/coding_plan/search` (global) or `https://api.minimaxi.com/v1/coding_plan/search` (CN).
- Payload: `{"q": "<search query>"}` — **note: `q`, not `query`**. Using `query` returns `status_code: 2013 "invalid params"`.
- Response: `{base_resp: {status_code: 0}, organic: [{title, link, snippet, date}], related_searches: [...]}`.
- Returns up to 10 results. No full-page extraction (snippet only). Extraction continues to use the configured `web.backend` / `extract_backend` (e.g., Firecrawl, parallel).

## Supported features

- ✅ Web search (returns `title`, `url`, `description`/`snippet`, `published` date)
- ✅ Portuguese and English queries (tested)
- ✅ Region detection (global vs CN) via env vars
- ❌ Full-page extraction (API returns snippets only)

## License

MIT — free to use, modify, distribute.

## Author

Paulo Donizeti Gardinalli Filho ([@pdonizete](https://github.com/pdonizete)) — built for personal use, shared for the community.

---

**Note:** This plugin is a *search backend* only. It registers a provider named `minimax` via `provides_web_providers: [minimax]`. It does not provide tools, hooks, or middleware.