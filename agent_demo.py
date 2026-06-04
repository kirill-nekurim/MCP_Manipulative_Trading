#!/usr/bin/env python3
"""
LangChain agent with GigaChat + MCP search (chroma-mcp).

GigaChat does not accept the raw MCP tool JSON schema (anyOf/Union).
The agent uses a thin wrapper `search_knowledge_base` that calls MCP
`chroma_query_documents` under the hood.

Prerequisites:
  1. cp .env.example .env  and set GIGACHAT_CREDENTIALS
  2. python ingest.py --reset
  3. uvx available for chroma-mcp

Usage:
    python agent_demo.py --query "Find top-3 fragments about spoofing" --k 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_gigachat.chat_models import GigaChat

from mcp_chroma import (
    MCP_TOOL,
    format_results_for_agent,
    query_documents,
)

PROJECT_ROOT = Path(__file__).parent
CHROMA_PATH = PROJECT_ROOT / "chroma_db"
AGENT_TOOL = "search_knowledge_base"
TEXT_PREVIEW_LEN = 280

AGENT_INSTRUCTION = """You are a knowledge-base assistant for market manipulation documents.

Call tool "{tool_name}" once (no arguments). It searches for the user question via MCP {mcp_tool} on "{collection}" (top-{k}).

Answer in Russian. For each fragment list:
document_id, chunk_id, source, score, short text preview.

Use only data returned by the tool. Do not invent sources.
"""


def build_model() -> GigaChat:
    credentials = os.getenv("GIGACHAT_CREDENTIALS")
    if not credentials:
        raise SystemExit(
            "GIGACHAT_CREDENTIALS is not set. Copy .env.example to .env and add your API key."
        )

    verify_raw = os.getenv("GIGACHAT_VERIFY_SSL_CERTS", "false").lower()
    verify_ssl = verify_raw in ("1", "true", "yes")

    kwargs: dict = {
        "credentials": credentials,
        "scope": os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
        "model": os.getenv("GIGACHAT_MODEL", "GigaChat"),
        "verify_ssl_certs": verify_ssl,
        "temperature": 0.1,
    }
    ca_bundle = os.getenv("GIGACHAT_CA_BUNDLE_FILE")
    if ca_bundle:
        kwargs["ca_bundle_file"] = ca_bundle

    return GigaChat(**kwargs)


def make_search_tool(chroma_path: Path, user_query: str, k: int):
    """Tool without free-form query arg — GigaChat tends to translate to Russian, but
    Chroma embeddings (all-MiniLM-L6-v2) work much better on English."""

    async def search_knowledge_base() -> str:
        """Search the knowledge base for the current user question via MCP chroma_query_documents."""
        payload = await query_documents(chroma_path, user_query, k)
        return format_results_for_agent(user_query, k, payload)

    return StructuredTool.from_function(
        coroutine=search_knowledge_base,
        name=AGENT_TOOL,
        description=(
            "Search the knowledge base for the user's current question. "
            f"Uses MCP tool {MCP_TOOL}. Returns document_id, chunk_id, source, score, text."
        ),
    )


def print_tool_search_results(tool_name: str, raw: str) -> None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"\n[{tool_name}] (non-JSON)\n{raw[:500]}")
        return

    mcp_tool = data.get("mcp_tool", MCP_TOOL)
    print(f"\n--- Agent tool: {tool_name} → MCP: {mcp_tool} ---")
    for rank, hit in enumerate(data.get("results", []), start=1):
        print(
            f"{rank}. document_id={hit.get('document_id')}, "
            f"chunk_id={hit.get('chunk_id')}, score={hit.get('score')}"
        )
        print(f"   source={hit.get('source')}")
        preview = (hit.get("text") or "").replace("\n", " ").strip()
        if len(preview) > TEXT_PREVIEW_LEN:
            preview = preview[:TEXT_PREVIEW_LEN] + "..."
        print(f"   text={preview}")
    print()


def print_agent_trace(messages: list) -> None:
    print("\n=== Agent trace ===")
    for msg in messages:
        if isinstance(msg, ToolMessage):
            print_tool_search_results(msg.name or AGENT_TOOL, msg.content)
        elif isinstance(msg, AIMessage):
            text = msg.content
            if isinstance(text, list):
                text = str(text)
            if text and str(text).strip():
                print(f"[assistant]\n{text}\n")


async def run_agent(query: str, k: int, chroma_path: Path) -> None:
    if not chroma_path.is_dir():
        raise SystemExit(f"Index not found at {chroma_path}. Run: python ingest.py --reset")

    model = build_model()
    tools = [make_search_tool(chroma_path, user_query=query, k=k)]
    agent = create_agent(model, tools)

    prompt = (
        AGENT_INSTRUCTION.format(
            tool_name=AGENT_TOOL,
            mcp_tool=MCP_TOOL,
            collection="market_manipulation_kb",
            k=k,
        )
        + f"\nUser request: {query}"
    )

    print(f"Query: {query}")
    print(f"Top-k: {k}")
    print(f"Model: {os.getenv('GIGACHAT_MODEL', 'GigaChat')}")
    print(f"Agent tool: {AGENT_TOOL} → MCP: {MCP_TOOL}")
    print(f"Chroma search query (from CLI): {query}")

    result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})
    messages = result.get("messages", [])
    print_agent_trace(messages)


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    parser = argparse.ArgumentParser(description="GigaChat agent + Chroma MCP search")
    parser.add_argument("--query", "-q", required=True, help="User question")
    parser.add_argument("--k", type=int, default=3, help="Number of fragments")
    parser.add_argument(
        "--chroma-path",
        type=Path,
        default=CHROMA_PATH,
        help="Chroma persistence directory",
    )
    args = parser.parse_args()

    if args.k < 1:
        raise SystemExit("--k must be >= 1")

    asyncio.run(run_agent(args.query, args.k, args.chroma_path))


if __name__ == "__main__":
    main()
