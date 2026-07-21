#!/usr/bin/env python3
"""Smart-money idea screener — a sample agent on the TipRanks MCP server.

Surfaces a shortlist of stock ideas the "smart money" is favoring, by cross-checking
TipRanks' top Smart-Score names, what's trending, and where hedge funds and insiders
are buying — then ranking them by conviction. Claude connects to the hosted TipRanks
MCP connector (https://mcp.tipranks.com/mcp/) and calls the discovery tools itself;
the connection runs server-side via the Messages API `mcp_servers` connector.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    export TIPRANKS_MCP_API_KEY=tr_live_...      # get one at https://mcp.tipranks.com/dev/signup
    python smart_money_screener.py               # ~6 ideas
    python smart_money_screener.py --count 8 --model claude-sonnet-5

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

SYSTEM_PROMPT = """You are a buy-side analyst running an idea-generation screen for a \
professional investor. You have live TipRanks data available through tools.

Gather efficiently, then write. Be economical with tool calls — the free API tier \
allows 10 calls/minute, so lean on the screening tools rather than drilling into \
every name. Use the discovery tools to build a candidate set: `get_top_smart_score_stocks` \
(TipRanks' composite winners), `get_trending_stocks` (what's drawing attention), \
`get_hedge_fund_activity` and `get_insider_transactions` (where the smart money is \
buying). You may add `get_top_rated_stocks` for the analyst-consensus angle. **Use \
ONLY these screening/list tools. Do NOT call per-ticker tools such as `get_assets_data`, \
`get_financials`, `get_stock_quotes`, or `get_recent_analyst_ratings` — synthesize \
entirely from what the screens return. Call each tool at most once, aim for about 5 \
tools total, and never exceed 6.**

Then write a ranked shortlist of the {count} strongest ideas where multiple smart-money \
signals line up. Format each idea as:
  **TICKER — Company** (why it surfaced)
  A one-line thesis: which signals align (e.g. perfect Smart Score + hedge-fund buying \
  + Strong Buy consensus), and the single most important number.

Rank by how many independent signals corroborate each name (a stock that's a \
Smart-Score leader AND being bought by hedge funds AND has a Strong Buy consensus \
ranks above one flagged by a single screen). Open with one sentence on what the \
screens collectively suggest, and note any theme (e.g. a sector clustering). Ground \
every claim in the data you pulled; never invent tickers or numbers. End with one \
line: "Informational only — not investment advice." """


def build_user_prompt(count: int) -> str:
    return (f"Screen for the {count} best stock ideas the smart money is favoring "
            f"right now.")


def run(count: int, model: str) -> None:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    mcp_key = os.environ.get("TIPRANKS_MCP_API_KEY")
    if not mcp_key:
        sys.exit(
            "Set TIPRANKS_MCP_API_KEY to a TipRanks MCP API key (tr_live_...).\n"
            "Get one in one HTTP call or at https://mcp.tipranks.com/dev/signup"
        )

    system = SYSTEM_PROMPT.replace("{count}", str(count))
    messages = [{"role": "user", "content": build_user_prompt(count)}]
    print("Screening for smart-money ideas — Claude is calling TipRanks tools:",
          file=sys.stderr)
    resp = None
    for _ in range(MAX_TURNS):
        try:
            resp = client.beta.messages.create(
                model=model,
                max_tokens=6000,
                betas=["mcp-client-2025-11-20"],
                thinking={"type": "adaptive"},
                system=system,
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
    ideas = "".join(b.text for b in blocks[cut + 1:] if b.type == "text").strip()
    print("\n" + (ideas or "(no ideas were produced — try re-running)") + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description="TipRanks MCP smart-money idea screener")
    p.add_argument("--count", type=int, default=6,
                   help="How many ideas to surface (default 6).")
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"Claude model (default {DEFAULT_MODEL}; "
                        f"try claude-sonnet-5 for lower cost)")
    args = p.parse_args()
    run(max(1, args.count), args.model)


if __name__ == "__main__":
    main()
