# Due-Diligence Agent — TypeScript

The TypeScript port of the [due-diligence agent](../). Give it a ticker; Claude
connects to the hosted [TipRanks MCP server](https://mcp.tipranks.com/) and writes a
structured research memo — analyst consensus, Smart Score, financials, technicals,
and the bull/bear case.

Same shape as the Python version: one `client.beta.messages.create` call with the
`mcp_servers` connector attached. Anthropic runs the MCP connection and the tool loop
server-side, so there's no per-tool wiring here.

```
$ npm start -- NVDA
Researching NVDA — Claude is calling TipRanks tools:
  → tipranks.get_assets_data
  → tipranks.get_financials
  → tipranks.get_technical_analysis
  → tipranks.get_bulls_bears_summary

# Due-Diligence Memo — NVIDIA Corp. (NVDA)
## 1. Snapshot
- Price: $203.28 | Market cap: ~$4.91T | Smart Score: 8/10
…
Informational only — not investment advice.
```

## Run it

Requires **Node.js 20+**.

1. **Get a TipRanks MCP API key** at
   [mcp.tipranks.com/dev/signup](https://mcp.tipranks.com/dev/signup) (or the one-call
   `POST /dev/api/signup` shown in the [Python README](../README.md)).

2. **Install and configure:**

   ```bash
   npm install
   cp .env.example .env      # then fill in both keys, or just export them:
   export ANTHROPIC_API_KEY=sk-ant-...
   export TIPRANKS_MCP_API_KEY=tr_live_...
   ```

3. **Run** (the `--` passes args through npm to the script):

   ```bash
   npm start -- NVDA
   npm start -- AAPL --model claude-sonnet-5   # lower-cost model
   ```

## How it works

```typescript
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic(); // reads ANTHROPIC_API_KEY

const resp = await client.beta.messages.create({
  model: "claude-opus-4-8",
  max_tokens: 8000,
  betas: ["mcp-client-2025-11-20"],
  system: SYSTEM_PROMPT,
  mcp_servers: [
    { type: "url", url: "https://mcp.tipranks.com/mcp/",
      name: "tipranks", authorization_token: TIPRANKS_MCP_API_KEY }, // sent as Authorization: Bearer
  ],
  tools: [{ type: "mcp_toolset", mcp_server_name: "tipranks" }],
  messages: [{ role: "user", content: "Produce a due-diligence memo on NVDA." }],
});
```

Anthropic returns the `mcp_tool_use` / `mcp_tool_result` blocks and the final memo in
`resp.content`. The script narrows blocks by `.type`, prints the tools Claude called
and the memo, and resumes if a long tool loop pauses (`stop_reason === "pause_turn"`).
See [`due-diligence-agent.ts`](due-diligence-agent.ts). Runs via
[`tsx`](https://github.com/privatenumber/tsx) (`npm start`) — no build step.

## Notes

- **Rate limits.** The free tier allows 10 tool calls/minute and 50/month. This agent
  is tuned to ~4 calls per memo. Upgrade at
  [/dev/billing](https://mcp.tipranks.com/dev/billing) for heavier use.
- **Model.** Defaults to `claude-opus-4-8`; pass `--model claude-sonnet-5` for a cheaper run.
- **Informational only.** TipRanks provides market data and analyst research for
  informational purposes — not investment, financial, legal, or tax advice.
