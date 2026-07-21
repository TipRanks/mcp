#!/usr/bin/env python3
"""Earnings-season companion — a sample agent on the TipRanks MCP server.

Give it a ticker; it produces an earnings-focused brief: the next report date and
what the Street expects, the beat/miss track record, a recap of the last earnings
call, and how analysts are positioned into the print. Claude connects to the hosted
TipRanks MCP connector (https://mcp.tipranks.com/mcp/) and calls the earnings tools
itself — the connection runs server-side via the Messages API `mcp_servers`
connector, so there's no tool loop to maintain here.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    export TIPRANKS_MCP_API_KEY=tr_live_...      # get one at https://mcp.tipranks.com/dev/signup
    python earnings_companion.py MSFT
    python earnings_companion.py NVDA --model claude-sonnet-5

Informational only. TipRanks provides market data and analyst research for
informational purposes — not investment, financial, legal, or tax advice.
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

import anthropic

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

MCP_URL = "https://mcp.tipranks.com/mcp/"
DEFAULT_MODEL = "claude-opus-4-8"   # swap to "claude-sonnet-5" for lower cost
MAX_TURNS = 8

SYSTEM_PROMPT = """You are an equity analyst writing an earnings brief for a \
professional investor heading into (or just past) a company's report. You have \
live TipRanks data available through tools.

Gather efficiently, then write. Be economical with tool calls — the free API tier \
allows 10 calls/minute, so a focused brief beats an exhaustive one. Lead with \
`get_assets_data` (it returns the next earnings date, consensus, price target and \
Smart Score in one call), then add `get_earnings_history` for the actual-vs-estimate \
track record, `get_earnings_call_summary` for what management said last quarter, and \
`get_recent_analyst_ratings` for how the Street is positioned. **Call each tool at \
most once, aim for about 4 tools total, and never exceed 6.**

Then write a concise, decision-useful earnings brief with these sections:
  1. Next report — the date (and days out), plus what consensus expects.
  2. Track record — recent EPS/revenue beats vs. misses, the beat streak, and how
     the stock has tended to react.
  3. Last call recap — the key takeaways and tone from the most recent earnings call.
  4. Analyst posture — consensus rating, price target, and any recent rating moves
     into the print.
  5. What to watch — the 2-3 metrics or themes that will decide the reaction.
  6. Bottom line — a two-sentence synthesis of the setup.

Ground every claim in the data you pulled; never invent numbers. If a data point is \
unavailable (e.g. no upcoming date because it just reported), say so. Keep it tight. \
End with one line: "Informational only — not investment advice." """


def build_user_prompt(ticker: str) -> str:
    return f"Write an earnings brief for {ticker.upper()}."


def run(ticker: str, model: str) -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    mcp_key = os.environ.get("TIPRANKS_MCP_API_KEY")
    if not mcp_key:
        sys.exit(
            "Set TIPRANKS_MCP_API_KEY to a TipRanks MCP API key (tr_live_...).\n"
            "Get one in one HTTP call or at https://mcp.tipranks.com/dev/signup"
        )

    messages = [{"role": "user", "content": build_user_prompt(ticker)}]
    print(f"Prepping {ticker.upper()} earnings brief — Claude is calling TipRanks tools:",
          file=sys.stderr)
    resp = None
    for _ in range(MAX_TURNS):
        try:
            resp = client.beta.messages.create(
                model=model,
                max_tokens=6000,
                betas=["mcp-client-2025-11-20"],
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                mcp_servers=[{
                    "type": "url",
                    "url": MCP_URL,
                    "name": "tipranks",
                    "authorization_token": mcp_key,
                }],
                tools=[{"type": "mcp_toolset", "mcp_server_name": "tipranks"}],
                messages=messages,
            )
        except anthropic.BadRequestError as e:
            sys.exit(
                f"\nMCP request failed: {e}\n"
                "If this is a rate limit, the free tier allows 10 tool calls/minute — "
                "wait a minute and retry, or upgrade at https://mcp.tipranks.com/dev/billing."
            )
        for block in resp.content:
            if block.type == "mcp_tool_use":
                print(f"  → tipranks.{block.name}", file=sys.stderr)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "pause_turn":
            break

    blocks = resp.content if resp else []
    cut = max((i for i, b in enumerate(blocks)
               if b.type in ("mcp_tool_use", "mcp_tool_result")), default=-1)
    brief = "".join(b.text for b in blocks[cut + 1:] if b.type == "text").strip()
    print("\n" + (brief or "(no brief was produced — try re-running)") + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description="TipRanks MCP earnings-season companion")
    p.add_argument("ticker", help="Stock ticker, e.g. MSFT")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"Claude model (default {DEFAULT_MODEL}; "
                        f"try claude-sonnet-5 for lower cost)")
    args = p.parse_args()
    run(args.ticker, args.model)


if __name__ == "__main__":
    main()
