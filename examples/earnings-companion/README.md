# Earnings-Season Companion

A compact Python agent (~130 lines) that turns a ticker into an earnings-focused
brief, using the hosted [TipRanks MCP server](https://mcp.tipranks.com/) for its data.

You give it a ticker; Claude connects to the TipRanks connector and pulls the next
report date and consensus, the beat/miss track record, a recap of the last earnings
call, and how analysts are positioned — then writes a six-section brief. The MCP
connection runs **server-side on Anthropic's infrastructure**, so there's no
tool-execution loop here: you pass the connector once and Claude orchestrates the calls.

```
$ python earnings_companion.py MSFT
Prepping MSFT earnings brief — Claude is calling TipRanks tools:
  → tipranks.get_assets_data
  → tipranks.get_earnings_history
  → tipranks.get_earnings_call_summary
  → tipranks.get_recent_analyst_ratings

# Microsoft (MSFT) — Earnings Brief
## 1. Next Report
- Date: July 29, 2026 (after hours) — 8 days out. Consensus EPS $4.24, revenue ~$87.6B.
## 2. Track Record
- Beat EPS consensus in every one of the last 8 quarters — but the stock has fallen on
  the last three beats: the market is trading guidance, not the headline.
## 3. Last Call Recap  … ## 4. Analyst Posture  … ## 5. What to Watch  … ## 6. Bottom Line

Informational only — not investment advice.
```

## Run it

1. **Get a TipRanks MCP API key** — sign up at
   [mcp.tipranks.com/dev/signup](https://mcp.tipranks.com/dev/signup), or mint a
   free-tier key in one HTTP call:

   ```bash
   curl -X POST https://mcp.tipranks.com/dev/api/signup \
     -H 'content-type: application/json' \
     -d '{"email":"you@example.com","password":"<10+ chars>","accept_terms":true,"label":"earnings-agent"}'
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
   python earnings_companion.py MSFT
   python earnings_companion.py NVDA --model claude-sonnet-5   # lower-cost model
   ```

## How it works

One Messages API call with the connector attached; Claude picks the earnings tools:

```python
resp = client.beta.messages.create(
    model="claude-opus-4-8",
    betas=["mcp-client-2025-11-20"],
    system=SYSTEM_PROMPT,       # "write an earnings brief; lead with get_assets_data …"
    mcp_servers=[{"type": "url", "url": "https://mcp.tipranks.com/mcp/",
                  "name": "tipranks", "authorization_token": TIPRANKS_MCP_API_KEY}],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "tipranks"}],
    messages=[{"role": "user", "content": "Write an earnings brief for MSFT."}],
)
```

Anthropic runs the tool loop server-side and returns the `mcp_tool_use` /
`mcp_tool_result` blocks plus the brief in `resp.content`. The script prints the tools
Claude called and the brief, and resumes if a long tool loop pauses (`stop_reason ==
"pause_turn"`). See [`earnings_companion.py`](earnings_companion.py).

## Notes

- **Rate limits.** The free tier allows 10 tool calls/minute and 50/month. This agent
  is tuned to ~4 calls per brief. Upgrade at
  [/dev/billing](https://mcp.tipranks.com/dev/billing) for heavier use.
- **Model.** Defaults to `claude-opus-4-8`; pass `--model claude-sonnet-5` for a cheaper run.
- **Informational only.** TipRanks provides market data and analyst research for
  informational purposes — not investment, financial, legal, or tax advice.
