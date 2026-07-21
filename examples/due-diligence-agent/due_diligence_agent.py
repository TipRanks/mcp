#!/usr/bin/env python3
"""Single-stock due-diligence analyst — a sample agent on the TipRanks MCP server.

Give it a ticker; it produces a structured research memo. Claude connects to the
hosted TipRanks MCP connector (https://mcp.tipranks.com/mcp/) and decides which
tools to call — analyst ratings, Smart Score, financials, technicals, bull/bear
summary, insider and hedge-fund activity, upcoming catalysts — then writes the memo.

The MCP connection runs server-side on Anthropic's infrastructure via the Messages
API `mcp_servers` connector, so there is no tool-execution loop to maintain here:
you pass the connector once and Claude orchestrates the calls.

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

import anthropic

MCP_URL = "https://mcp.tipranks.com/mcp/"
DEFAULT_MODEL = "claude-opus-4-8"   # swap to "claude-sonnet-5" for lower cost
MAX_TURNS = 12                      # cap the server-side tool loop (pause_turn resumes)

SYSTEM_PROMPT = """You are an equity research analyst writing a due-diligence memo \
for a professional investor. You have live TipRanks data available through tools.

Gather what you need before writing — use the tools to pull the current snapshot \
and metrics, company financials, the technical picture, the Wall Street analyst \
consensus and price target, the bull and bear case, insider and hedge-fund \
activity, and any upcoming catalysts. Call several tools; a good memo triangulates \
across fundamentals, technicals, sentiment, and positioning.

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

    print(f"Researching {ticker.upper()} …\n", file=sys.stderr)
    for _ in range(MAX_TURNS):
        with client.beta.messages.stream(
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
        ) as stream:
            for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    # Surface each TipRanks tool call as it happens (nice for demos).
                    if block.type == "mcp_tool_use":
                        print(f"  → tipranks.{getattr(block, 'name', '?')}",
                              file=sys.stderr)
                elif event.type == "content_block_delta" and event.delta.type == "text_delta":
                    print(event.delta.text, end="", flush=True)
            final = stream.get_final_message()

        messages.append({"role": "assistant", "content": final.content})
        # A server-side tool loop can pause; re-send to resume (no new user turn).
        if final.stop_reason != "pause_turn":
            break

    print()  # trailing newline after the streamed memo


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
