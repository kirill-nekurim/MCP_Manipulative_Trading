#!/usr/bin/env python3
"""LangChain agent with GigaChat + MCP search (chroma-mcp)."""

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

from config import CHROMA_PATH, COLLECTION_NAME, ENV_FILE, TEXT_PREVIEW_LEN
from mcp_chroma import MCP_TOOL, format_results_for_agent, query_documents

AGENT_TOOL = "search_knowledge_base"

AGENT_INSTRUCTION = """You are a knowledge-base assistant for market manipulation documents.

Call tool "{tool_name}" once (no arguments). It searches for the user question via MCP {mcp_tool} on "{collection}" (top-{k}).

Answer in Russian. For each fragment list:
document_id, chunk_id, source, score, short text preview.

Use only data returned by the tool. Do not invent sources.
"""


def build_model() -> GigaChat:
    credentials = os.getenv("GIGACHAT_CREDENTIALS")
    if not credentials:
        raise SystemExit("Set GIGACHAT_CREDENTIALS in .env (see .env.example).")

    verify_ssl = os.getenv("GIGACHAT_VERIFY_SSL_CERTS", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    kwargs: dict = {
        "credentials": credentials,
        "scope": os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
        "model": os.getenv("GIGACHAT_MODEL", "GigaChat"),
        "verify_ssl_certs": verify_ssl,
        "temperature": 0.1,
    }
    if ca := os.getenv("GIGACHAT_CA_BUNDLE_FILE"):
        kwargs["ca_bundle_file"] = ca
    return GigaChat(**kwargs)


def make_search_tool(chroma_path, user_query: str, k: int):
    async def search_knowledge_base() -> str:
        payload = await query_documents(chroma_path, user_query, k)
        return format_results_for_agent(user_query, k, payload)

    return StructuredTool.from_function(
        coroutine=search_knowledge_base,
        name=AGENT_TOOL,
        description=(
            "Search the knowledge base for the user's current question. "
            f"Uses MCP tool {MCP_TOOL}."
        ),
    )


def print_tool_search_results(tool_name: str, raw: str) -> None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"\n[{tool_name}] (non-JSON)\n{raw[:500]}")
        return

    print(f"\n--- Agent tool: {tool_name} → MCP: {data.get('mcp_tool', MCP_TOOL)} ---")
    for rank, hit in enumerate(data.get("results", []), start=1):
        print(
            f"{rank}. document_id={hit.get('document_id')}, "
            f"chunk_id={hit.get('chunk_id')}, score={hit.get('score')}"
        )
        print(f"   source={hit.get('source')}")
        preview = (hit.get("text") or "").replace("\n", " ").strip()
        if len(preview) > TEXT_PREVIEW_LEN:
            preview = preview[:TEXT_PREVIEW_LEN] + "..."
        print(f"   text={preview}\n")


def print_agent_trace(messages: list) -> None:
    print("\n=== Agent trace ===")
    for msg in messages:
        if isinstance(msg, ToolMessage):
            print_tool_search_results(msg.name or AGENT_TOOL, msg.content)
        elif isinstance(msg, AIMessage) and msg.content:
            text = str(msg.content) if not isinstance(msg.content, str) else msg.content
            if text.strip():
                print(f"[assistant]\n{text}\n")


async def run_agent(query: str, k: int, chroma_path) -> None:
    if not chroma_path.is_dir():
        raise SystemExit("chroma_db missing. Run: python src/ingest.py --reset")

    agent = create_agent(build_model(), [make_search_tool(chroma_path, query, k)])
    prompt = (
        AGENT_INSTRUCTION.format(
            tool_name=AGENT_TOOL,
            mcp_tool=MCP_TOOL,
            collection=COLLECTION_NAME,
            k=k,
        )
        + f"\nUser request: {query}"
    )

    print(f"Query: {query}\nTop-k: {k}")
    print(f"Model: {os.getenv('GIGACHAT_MODEL', 'GigaChat')}")
    print(f"Agent tool: {AGENT_TOOL} → MCP: {MCP_TOOL}")
    print(f"Chroma search query (from CLI): {query}")

    result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]})
    print_agent_trace(result.get("messages", []))


def main() -> None:
    load_dotenv(ENV_FILE)
    parser = argparse.ArgumentParser(description="GigaChat agent + MCP search")
    parser.add_argument("--query", "-q", required=True)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--chroma-path", type=Path, default=CHROMA_PATH)
    args = parser.parse_args()

    if args.k < 1:
        raise SystemExit("--k must be >= 1")

    asyncio.run(run_agent(args.query, args.k, args.chroma_path))


if __name__ == "__main__":
    main()
