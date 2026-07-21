# Smart-Money Idea Screener

A compact Python agent (~140 lines) that surfaces a ranked shortlist of stock ideas
the "smart money" is favoring, using the hosted [TipRanks MCP server](https://mcp.tipranks.com/)
for its data.

It runs a few discovery screens — top Smart-Score names, what's trending, and where
hedge funds and insiders are buying — then ranks the candidates by how many
independent signals corroborate each one. The MCP connection runs **server-side on
Anthropic's infrastructure**, so there's no tool-execution loop here: you pass the
connector once and Claude orchestrates the screens.

```
$ python smart_money_screener.py --count 6
Screening for smart-money ideas — Claude is calling TipRanks tools:
  → tipranks.get_top_smart_score_stocks
  → tipranks.get_trending_stocks
  → tipranks.get_top_rated_stocks
  → tipranks.get_hedge_fund_activity

## Smart-Money Screen — 6 Best Ideas
The signals collectively point to large-cap quality with a heavy healthcare tilt…

**1. GOOGL — Alphabet** (Smart-Score board *and* trending best-rated)
Triple confirmation: perfect Smart Score 10, Strong Buy consensus, top trending attention.
…
**4. HAL — Halliburton** — analysts bullish, but 13F shows hedge funds *trimming* ~2.4M
shares: the institutional signal contradicts the analyst enthusiasm. Lower-conviction.

Informational only — not investment advice.
```

*(The agent cross-checks the screens rather than just listing — note it flags where
hedge-fund flows contradict the analyst view.)*

## Run it

1. **Get a TipRanks MCP API key** — sign up at
   [mcp.tipranks.com/dev/signup](https://mcp.tipranks.com/dev/signup), or mint a
   free-tier key in one HTTP call:

   ```bash
   curl -X POST https://mcp.tipranks.com/dev/api/signup \
     -H 'content-type: application/json' \
     -d '{"email":"you@example.com","password":"<10+ chars>","accept_terms":true,"label":"screener"}'
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
   python smart_money_screener.py                # ~6 ideas
   python smart_money_screener.py --count 8 --model claude-sonnet-5
   ```

## How it works

One Messages API call with the connector attached; Claude picks the screening tools:

```python
resp = client.beta.messages.create(
    model="claude-opus-4-8",
    betas=["mcp-client-2025-11-20"],
    system=SYSTEM_PROMPT,       # "run the discovery screens; rank by corroborating signals …"
    mcp_servers=[{"type": "url", "url": "https://mcp.tipranks.com/mcp/",
                  "name": "tipranks", "authorization_token": TIPRANKS_MCP_API_KEY}],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "tipranks"}],
    messages=[{"role": "user", "content": "Screen for the 6 best smart-money ideas."}],
)
```

Anthropic runs the tool loop server-side and returns the `mcp_tool_use` /
`mcp_tool_result` blocks plus the shortlist in `resp.content`. The script prints the
tools Claude called and the result, and resumes if a long tool loop pauses
(`stop_reason == "pause_turn"`). See [`smart_money_screener.py`](smart_money_screener.py).

## Notes

- **Rate limits.** The free tier allows 10 tool calls/minute and 50/month. This agent
  is tuned to ~5 screening calls. Upgrade at
  [/dev/billing](https://mcp.tipranks.com/dev/billing) for heavier use.
- **Model.** Defaults to `claude-opus-4-8`; pass `--model claude-sonnet-5` for a cheaper run.
- **Informational only.** TipRanks provides market data and analyst research for
  informational purposes — not investment, financial, legal, or tax advice. This is a
  demonstration, not a recommendation engine.
