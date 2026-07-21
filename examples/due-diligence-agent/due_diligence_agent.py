#!/usr/bin/env python3
"""Single-stock due-diligence analyst — a sample agent on the TipRanks MCP server.

Give it a ticker; it produces a structured research memo. Claude connects to the
hosted TipRanks MCP connector (https://mcp.tipranks.com/mcp/) and decides which
tools to call — analyst ratings, Smart Score, financials, technicals, bull/bear
summary, insider and hedge-fund activity, upcoming catalysts — then writes the memo.

The MCP connection runs server-side on Anthropic's infrastructure via the Messages
API `mcp_servers` connector, so there is no tool-execution loop to maintain here:
you pass the connector once and Claude orchestrates the calls, and the tool results
come back inside the same response.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    export TIPRANKS_MCP_API_KEY=tr_live_...      # get one at https://mcp.tipranks.com/dev/signup
    python due_diligence_agent.py NVDA
    python due_diligence_agent.py AAPL --model claude-sonnet-5

Informational only. TipRanks provides market data and analyst research for
informational purposes — not investment, financial, legal, or tax advice.
"""
from __future__ import annotations

import argparse
import os
import sys

# UTF-8 output so the memo's punctuation (em-dashes, arrows) renders on any
# console, including Windows (cp1252 by default).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - older/odd stdout
    pass

import anthropic

# Optional: load a local .env (from `cp .env.example .env`) if python-dotenv is
# installed. Exporting the vars in your shell works too — this just adds the
# .env convenience without making it a hard dependency.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

MCP_URL = "https://mcp.tipranks.com/mcp/"
DEFAULT_MODEL = "claude-opus-4-8"   # swap to "claude-sonnet-5" for lower cost
MAX_TURNS = 8                       # cap: a paused server-side tool loop resumes

SYSTEM_PROMPT = """You are an equity research analyst writing a due-diligence memo \
for a professional investor. You have live TipRanks data available through tools.

Gather efficiently, then write. Be economical with tool calls — the free API tier \
allows only 5 calls/minute, so a focused memo beats an exhaustive one. Lead with \
`get_assets_data`, which returns the analyst consensus, average price target, Smart \
Score, key fundamentals, 52-week range, and next earnings date in a single call. \
Then add a few targeted calls — `get_financials` for the revenue/earnings trend, \
`get_technical_analysis` for the technical read, `get_bulls_bears_summary` for the \
two-sided case, and at most one positioning signal (insider or hedge-fund activity). \
**Call each tool at most once, aim for about 4 tools total, and never exceed 5.**

Then write a concise, decision-useful memo with these sections:
  1. Snapshot — price, market cap, sector, TipRanks Smart Score.
  2. Analyst view — consensus rating, average price target, implied upside/downside.
  3. Fundamentals — revenue/earnings trend, margins, notable line items.
  4. Technicals — trend, key levels, momentum read.
  5. Bull vs. bear — the strongest argument on each side.
  6. Smart money — insider and hedge-fund direction.
  7. Catalysts & risks — what to watch next.
  8. Bottom line — a two-sentence synthesis.

Ground every claim in the data you pulled; never invent numbers. If a data point \
is unavailable, say so rather than guessing. Keep it tight — a portfolio manager \
should be able to read it in two minutes. End with one line: \
"Informational only — not investment advice." """


def build_user_prompt(ticker: str) -> str:
    return f"Produce a due-diligence memo on {ticker.upper()}."


def run(ticker: str, model: str) -> None:
    # anthropic.Anthropic() reads ANTHROPIC_API_KEY from the environment.
    client = anthropic.Anthropic()

    mcp_key = os.environ.get("TIPRANKS_MCP_API_KEY")
    if not mcp_key:
        sys.exit(
            "Set TIPRANKS_MCP_API_KEY to a TipRanks MCP API key (tr_live_...).\n"
            "Get one in one HTTP call or at https://mcp.tipranks.com/dev/signup"
        )

    messages = [{"role": "user", "content": build_user_prompt(ticker)}]

    print(f"Researching {ticker.upper()} — Claude is calling TipRanks tools:",
          file=sys.stderr)
    resp = None
    for _ in range(MAX_TURNS):
        try:
            resp = client.beta.messages.create(
                model=model,
                max_tokens=8000,
                betas=["mcp-client-2025-11-20"],
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                # The hosted TipRanks connector. Anthropic makes the MCP connection
                # server-side; the API key is sent as `Authorization: Bearer <key>`.
                mcp_servers=[{
                    "type": "url",
                    "url": MCP_URL,
                    "name": "tipranks",
                    "authorization_token": mcp_key,
                }],
                # Expose every TipRanks tool; Claude picks which ones to call.
                tools=[{"type": "mcp_toolset", "mcp_server_name": "tipranks"}],
                messages=messages,
            )
        except anthropic.BadRequestError as e:
            # The connector returns a 400 "Error while communicating with MCP
            # server" when a downstream tool call fails — most commonly the
            # free tier's 5-calls/minute rate limit tripping on a burst.
            sys.exit(
                f"\nMCP request failed: {e}\n"
                "If this is a rate limit, the free tier allows 5 tool calls/minute — "
                "wait a minute and retry, or upgrade at https://mcp.tipranks.com/dev/billing."
            )
        # Surface each TipRanks tool the model called this turn.
        for block in resp.content:
            if block.type == "mcp_tool_use":
                print(f"  → tipranks.{block.name}", file=sys.stderr)
        messages.append({"role": "assistant", "content": resp.content})
        # A big server-side tool loop can pause; resume until it finishes.
        if resp.stop_reason != "pause_turn":
            break

    # The memo is the text the model wrote after its last tool call.
    blocks = resp.content if resp else []
    cut = max((i for i, b in enumerate(blocks)
               if b.type in ("mcp_tool_use", "mcp_tool_result")), default=-1)
    memo = "".join(b.text for b in blocks[cut + 1:] if b.type == "text").strip()
    print("\n" + (memo or "(no memo was produced — try re-running)") + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description="TipRanks MCP due-diligence agent")
    p.add_argument("ticker", help="Stock ticker, e.g. NVDA")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"Claude model (default {DEFAULT_MODEL}; "
                        f"try claude-sonnet-5 for lower cost)")
    args = p.parse_args()
    run(args.ticker, args.model)


if __name__ == "__main__":
    main()
