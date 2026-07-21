/**
 * Single-stock due-diligence analyst — a sample agent on the TipRanks MCP server.
 *
 * TypeScript port of ../due_diligence_agent.py. Give it a ticker; it produces a
 * structured research memo. Claude connects to the hosted TipRanks MCP connector
 * (https://mcp.tipranks.com/mcp/) and decides which tools to call — analyst ratings,
 * Smart Score, financials, technicals, bull/bear summary — then writes the memo.
 *
 * The MCP connection runs server-side on Anthropic's infrastructure via the Messages
 * API `mcp_servers` connector, so there is no tool-execution loop to maintain here:
 * you pass the connector once and Claude orchestrates the calls, and the tool results
 * come back inside the same response.
 *
 * Usage:
 *   export ANTHROPIC_API_KEY=sk-ant-...
 *   export TIPRANKS_MCP_API_KEY=tr_live_...   # get one at https://mcp.tipranks.com/dev/signup
 *   npm start -- NVDA
 *   npm start -- AAPL --model claude-sonnet-5
 *
 * Informational only. TipRanks provides market data and analyst research for
 * informational purposes — not investment, financial, legal, or tax advice.
 */
import "dotenv/config"; // optional: loads a local .env if present (no-op otherwise)
import Anthropic from "@anthropic-ai/sdk";

const MCP_URL = "https://mcp.tipranks.com/mcp/";
const DEFAULT_MODEL = "claude-opus-4-8"; // swap to "claude-sonnet-5" for lower cost
const MAX_TURNS = 8; // cap: a paused server-side tool loop resumes

const SYSTEM_PROMPT = `You are an equity research analyst writing a due-diligence memo \
for a professional investor. You have live TipRanks data available through tools.

Gather efficiently, then write. Be economical with tool calls — the free API tier \
allows 10 calls/minute, so a focused memo beats an exhaustive one. Lead with \
\`get_assets_data\`, which returns the analyst consensus, average price target, Smart \
Score, key fundamentals, 52-week range, and next earnings date in a single call. \
Then add a few targeted calls — \`get_financials\` for the revenue/earnings trend, \
\`get_technical_analysis\` for the technical read, \`get_bulls_bears_summary\` for the \
two-sided case, and at most one positioning signal (insider or hedge-fund activity). \
Call each tool at most once, aim for about 4 tools total, and never exceed 6.

Then write a concise, decision-useful memo with these sections:
  1. Snapshot — price, market cap, sector, TipRanks Smart Score.
  2. Analyst view — consensus rating, average price target, implied upside/downside.
  3. Fundamentals — revenue/earnings trend, margins, notable line items.
  4. Technicals — trend, key levels, momentum read.
  5. Bull vs. bear — the strongest argument on each side.
  6. Smart money — insider and hedge-fund direction.
  7. Catalysts & risks — what to watch next.
  8. Bottom line — a two-sentence synthesis.

Ground every claim in the data you pulled; never invent numbers. If a data point is \
unavailable, say so rather than guessing. Keep it tight — a portfolio manager should \
be able to read it in two minutes. End with one line: \
"Informational only — not investment advice."`;

function buildUserPrompt(ticker: string): string {
  return `Produce a due-diligence memo on ${ticker.toUpperCase()}.`;
}

async function run(ticker: string, model: string): Promise<void> {
  const client = new Anthropic(); // reads ANTHROPIC_API_KEY from the environment

  const mcpKey = process.env.TIPRANKS_MCP_API_KEY;
  if (!mcpKey) {
    console.error(
      "Set TIPRANKS_MCP_API_KEY to a TipRanks MCP API key (tr_live_...).\n" +
        "Get one in one HTTP call or at https://mcp.tipranks.com/dev/signup",
    );
    process.exit(1);
  }

  const messages: Anthropic.Beta.BetaMessageParam[] = [
    { role: "user", content: buildUserPrompt(ticker) },
  ];

  console.error(
    `Researching ${ticker.toUpperCase()} — Claude is calling TipRanks tools:`,
  );

  let response: Anthropic.Beta.BetaMessage | undefined;
  for (let turn = 0; turn < MAX_TURNS; turn++) {
    try {
      response = await client.beta.messages.create({
        model,
        max_tokens: 8000,
        betas: ["mcp-client-2025-11-20"],
        thinking: { type: "adaptive" },
        system: SYSTEM_PROMPT,
        // The hosted TipRanks connector. Anthropic makes the MCP connection
        // server-side; the API key is sent as `Authorization: Bearer <key>`.
        mcp_servers: [
          { type: "url", url: MCP_URL, name: "tipranks", authorization_token: mcpKey },
        ],
        // Expose every TipRanks tool; Claude picks which ones to call.
        tools: [{ type: "mcp_toolset", mcp_server_name: "tipranks" }],
        messages,
      });
    } catch (err) {
      // The connector returns a 400 "Error while communicating with MCP server"
      // when a downstream tool call fails — most commonly the free tier's
      // 10-calls/minute rate limit tripping on a burst.
      if (err instanceof Anthropic.BadRequestError) {
        console.error(
          `\nMCP request failed: ${err.message}\n` +
            "If this is a rate limit, the free tier allows 10 tool calls/minute — " +
            "wait a minute and retry, or upgrade at https://mcp.tipranks.com/dev/billing.",
        );
        process.exit(1);
      }
      throw err;
    }

    // Surface each TipRanks tool the model called this turn.
    for (const block of response.content) {
      if (block.type === "mcp_tool_use") {
        console.error(`  → tipranks.${block.name}`);
      }
    }
    messages.push({
      role: "assistant",
      content: response.content as Anthropic.Beta.BetaContentBlockParam[],
    });
    // A big server-side tool loop can pause; resume until it finishes.
    if (response.stop_reason !== "pause_turn") break;
  }

  // The memo is the text the model wrote after its last tool call.
  const blocks = response?.content ?? [];
  let cut = -1;
  blocks.forEach((b, i) => {
    if (b.type === "mcp_tool_use" || b.type === "mcp_tool_result") cut = i;
  });
  const memo = blocks
    .slice(cut + 1)
    .filter((b): b is Anthropic.Beta.BetaTextBlock => b.type === "text")
    .map((b) => b.text)
    .join("")
    .trim();

  console.log("\n" + (memo || "(no memo was produced — try re-running)") + "\n");
}

function main(): void {
  const args = process.argv.slice(2);
  let ticker: string | undefined;
  let model = DEFAULT_MODEL;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--model") {
      model = args[++i] ?? DEFAULT_MODEL;
    } else if (!ticker) {
      ticker = args[i];
    }
  }
  if (!ticker) {
    console.error("Usage: npm start -- <TICKER> [--model claude-sonnet-5]");
    process.exit(1);
  }
  run(ticker, model).catch((e) => {
    console.error(e);
    process.exit(1);
  });
}

main();
