# Due-Diligence Agent

A ~90-line Python agent that turns a ticker into a structured research memo, using
the hosted [TipRanks MCP server](https://mcp.tipranks.com/) for all its data.

You give it a ticker; Claude connects to the TipRanks connector and decides which
tools to call — analyst consensus & price target, Smart Score, financials,
technical picture, bull/bear summary, insider and hedge-fund activity, upcoming
catalysts — then writes an eight-section memo. The MCP connection runs **server-side
on Anthropic's infrastructure**, so there's no tool-execution loop to maintain: you
pass the connector once and Claude orchestrates the calls.

```
$ python due_diligence_agent.py NVDA
Researching NVDA …

  → tipranks.get_assets_data
  → tipranks.get_recent_analyst_ratings
  → tipranks.get_financials
  → tipranks.get_technical_analysis
  → tipranks.get_bulls_bears_summary
  → tipranks.get_hedge_fund_activity

# NVIDIA (NVDA) — Due-Diligence Memo
1. Snapshot — …
…
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
client.beta.messages.stream(
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

Anthropic makes the MCP connection on the server side, exposes every TipRanks tool
to the model, and runs the tool loop for you. The script only needs to (a) stream
the output and (b) resume if the server-side tool loop pauses (`stop_reason ==
"pause_turn"`). See [`due_diligence_agent.py`](due_diligence_agent.py).

## Notes

- **Rate limits.** The free tier allows 50 tool calls/month. A single memo makes
  several tool calls, so heavy use will hit the cap — upgrade at
  [/dev/billing](https://mcp.tipranks.com/dev/billing) for more headroom.
- **Model.** Defaults to `claude-opus-4-8`; pass `--model claude-sonnet-5` for a
  cheaper run.
- **Informational only.** TipRanks provides market data and analyst research for
  informational purposes — not investment, financial, legal, or tax advice. This
  sample is a demonstration, not a recommendation engine.
