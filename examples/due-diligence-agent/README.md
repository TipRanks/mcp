# Due-Diligence Agent

A compact Python agent (~110 lines) that turns a ticker into a structured research
memo, using the hosted [TipRanks MCP server](https://mcp.tipranks.com/) for all its data.

You give it a ticker; Claude connects to the TipRanks connector and decides which
tools to call — analyst consensus & price target, Smart Score, financials, technical
picture, bull/bear summary — then writes an eight-section memo. The MCP connection
runs **server-side on Anthropic's infrastructure**, so there's no tool-execution loop
to maintain: you pass the connector once and Claude orchestrates the calls, and the
tool results come back inside the same response.

```
$ python due_diligence_agent.py NVDA
Researching NVDA — Claude is calling TipRanks tools:
  → tipranks.get_assets_data
  → tipranks.get_financials
  → tipranks.get_technical_analysis
  → tipranks.get_bulls_bears_summary

# Due-Diligence Memo — NVIDIA Corp. (NVDA)
## 1. Snapshot
- Price: $203.28 | Market cap: ~$4.91T | Smart Score: 8/10
## 2. Analyst View
- Consensus: Strong Buy · avg price target $309.94 → implied ~+52% upside
… (fundamentals, technicals, bull/bear, smart money, catalysts, bottom line) …

Informational only — not investment advice.
```

## Run it

1. **Get a TipRanks MCP API key** — sign up at
   [mcp.tipranks.com/dev/signup](https://mcp.tipranks.com/dev/signup), or mint a
   free-tier key in one HTTP call:

   ```bash
   curl -X POST https://mcp.tipranks.com/dev/api/signup \
     -H 'content-type: application/json' \
     -d '{"email":"you@example.com","password":"<10+ chars>","accept_terms":true,"label":"dd-agent"}'
   # → { "api_key": "tr_live_...", "mcp_url": "https://mcp.tipranks.com/mcp/", "tier": "free", ... }
   ```

2. **Install and configure:**

   ```bash
   pip install -r requirements.txt
   cp .env.example .env      # then fill in both keys, or just export them:
   export ANTHROPIC_API_KEY=sk-ant-...
   export TIPRANKS_MCP_API_KEY=tr_live_...
   ```

3. **Run:**

   ```bash
   python due_diligence_agent.py NVDA
   python due_diligence_agent.py AAPL --model claude-sonnet-5   # lower-cost model
   ```

## How it works

The whole integration is one Messages API call with the connector attached:

```python
resp = client.beta.messages.create(
    model="claude-opus-4-8",
    max_tokens=8000,
    betas=["mcp-client-2025-11-20"],
    system=SYSTEM_PROMPT,
    mcp_servers=[{
        "type": "url",
        "url": "https://mcp.tipranks.com/mcp/",
        "name": "tipranks",
        "authorization_token": TIPRANKS_MCP_API_KEY,   # sent as Authorization: Bearer
    }],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "tipranks"}],
    messages=[{"role": "user", "content": "Produce a due-diligence memo on NVDA."}],
)
```

Anthropic makes the MCP connection on the server side, exposes every TipRanks tool to
the model, runs the tool loop, and returns the `mcp_tool_use` / `mcp_tool_result`
blocks and the final memo in `resp.content`. The script only (a) prints the tools the
model called and the memo, and (b) resumes if a long tool loop pauses (`stop_reason
== "pause_turn"`). See [`due_diligence_agent.py`](due_diligence_agent.py).

## Notes

- **Rate limits.** The free tier allows **5 tool calls/minute** and 50/month. This
  agent is deliberately tuned to ~4 focused calls per memo so it runs on a free key;
  a burstier or higher-volume agent will hit the per-minute limit (the script prints a
  hint if it does). Upgrade at [/dev/billing](https://mcp.tipranks.com/dev/billing) —
  Smart raises it to 30/minute and 1,000/month — for heavier use.
- **Model.** Defaults to `claude-opus-4-8`; pass `--model claude-sonnet-5` for a
  cheaper run.
- **Informational only.** TipRanks provides market data and analyst research for
  informational purposes — not investment, financial, legal, or tax advice. This
  sample is a demonstration, not a recommendation engine.
