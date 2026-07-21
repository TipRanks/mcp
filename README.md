# TipRanks MCP Server

**Live financial data and analyst research for AI agents — over the [Model Context Protocol](https://modelcontextprotocol.io).**

Plug Claude, ChatGPT, Cursor, or any MCP-compatible client into live TipRanks data: analyst ratings, Smart Score, price targets, technicals, options, insider and hedge-fund activity, congressional trading, ETFs, commodities, forex, crypto, earnings, news — plus read access to your own TipRanks portfolios.

- **Endpoint:** `https://mcp.tipranks.com/mcp/`
- **Transport:** Streamable HTTP
- **Auth:** OAuth 2.1 (PKCE + Dynamic Client Registration) or API key
- **Official MCP Registry:** [`com.tipranks/tipranks`](https://registry.modelcontextprotocol.io/?search=tipranks)
- **Docs:** https://mcp.tipranks.com/ · **Privacy:** https://mcp.tipranks.com/privacy · **Terms:** https://mcp.tipranks.com/terms

> **Informational only.** TipRanks provides market data and analyst research for informational purposes — not investment, financial, legal, or tax advice. Quotes and other data may be delayed. All tools are **read-only**; the connector never places trades or modifies your account.

---

## Connect

### Claude.ai / Claude Desktop / Claude Code
Add a custom connector pointing at `https://mcp.tipranks.com/mcp/` and complete the OAuth sign-in with your TipRanks account.

### ChatGPT
Available as a ChatGPT app — search the app directory for **TipRanks**.

### Cursor / VS Code / other MCP clients
Add a remote (streamable-HTTP) MCP server with URL `https://mcp.tipranks.com/mcp/`. Clients that support OAuth will discover the flow automatically via the server's `/.well-known/oauth-protected-resource` metadata.

Full per-client setup instructions: **https://mcp.tipranks.com/**

---

## Authentication & scopes

Authenticated services use **OAuth 2.1** (PKCE `S256`, Dynamic Client Registration). Two scopes:

| Scope | Default | Grants |
|---|---|---|
| `tipranks:read` | ✔ | Market data: analyst ratings, Smart Score, technicals, news, screening, ETFs, commodities, forex, crypto |
| `tipranks:portfolio` | — | Read your TipRanks portfolios (holdings, performance, allocation) — limited to portfolios you own at authorization time |

Developers can alternatively use an API key — see the [developer portal](https://mcp.tipranks.com/dev/signup).

## Rate limits

| Plan | Tool calls / month |
|---|---|
| Free | 10 |
| Premium | 100 |
| Ultimate | 200 |

Resets on the 1st of each month (UTC). API-key tiers (free / smart / advanced / professional) carry their own per-minute and monthly limits.

---

## Tools

70+ read-only tools, grouped by domain:

- **Stocks & research** — quotes, prices, analyst ratings & consensus, price targets, Smart Score, bull/bear summary, peers, catalysts
- **Fundamentals** — financials, earnings history & estimates, earnings-call summaries, dividends, KPIs, buybacks, stock splits
- **Ownership & sentiment** — insider transactions, hedge-fund holdings & activity, congressional (politician) trading, blogger & investor sentiment, top experts
- **Discovery & screening** — trending stocks, top-rated & top Smart-Score stocks, market movers, sector & market performance, ETF screener
- **ETFs** — analysis, forecast, holdings, exposures, top stocks
- **Options** — expirations, chains, contracts, unusual trades
- **Calendars & events** — earnings, IPO, economic, clinical-trial/FDA calendars, market commentary, news & articles
- **Cross-asset** — commodities, forex, crypto, indices (quotes + historical)
- **Your portfolios** — list, holdings, overview, performance, analysis *(requires `tipranks:portfolio`)*

The connector is **read-only** end to end — every tool is annotated `readOnlyHint: true`, `destructiveHint: false`.

---

## Privacy Policy

See **https://mcp.tipranks.com/privacy**. In brief: OAuth tokens and API keys are stored only as SHA-256 hashes (no plaintext credentials at rest); the connector reads TipRanks and market data on your behalf and does not sell personal data. Contact: support@tipranks.com.

## Support

- **Docs:** https://mcp.tipranks.com/
- **Developer portal:** https://mcp.tipranks.com/dev
- **Email:** support@tipranks.com

---

*© TipRanks. This repository contains the public connector descriptor and documentation for the hosted TipRanks MCP service. It does not contain the server implementation.*
