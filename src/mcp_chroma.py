"""Shared helpers to call chroma-mcp tool chroma_query_documents."""

from __future__ import annotations

import json
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config import COLLECTION_NAME, MCP_TOOL


def chroma_server_params(chroma_path: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command="uvx",
        args=[
            "chroma-mcp",
            "--client-type",
            "persistent",
            "--data-dir",
            str(chroma_path.resolve()),
        ],
    )


async def query_documents(chroma_path: Path, query: str, k: int) -> dict:
    """Call MCP tool chroma_query_documents and return parsed JSON."""
    async with stdio_client(chroma_server_params(chroma_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                MCP_TOOL,
                {
                    "collection_name": COLLECTION_NAME,
                    "query_texts": [query],
                    "n_results": k,
                    "include": ["documents", "metadatas", "distances"],
                },
            )
    return json.loads(result.content[0].text)


async def query_documents_batch(
    chroma_path: Path, items: list[tuple[str, int]]
) -> list[dict]:
    """Run multiple queries in one MCP session (faster for eval)."""
    results: list[dict] = []
    async with stdio_client(chroma_server_params(chroma_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for query, k in items:
                result = await session.call_tool(
                    MCP_TOOL,
                    {
                        "collection_name": COLLECTION_NAME,
                        "query_texts": [query],
                        "n_results": k,
                        "include": ["documents", "metadatas", "distances"],
                    },
                )
                results.append(json.loads(result.content[0].text))
    return results


def distance_to_score(distance: float | None) -> float | None:
    if distance is None:
        return None
    return round(1.0 - distance, 4)


def format_results_for_agent(query: str, k: int, payload: dict) -> str:
    """Compact JSON for the LLM (document_id, chunk_id, source, score, text)."""
    ids = payload.get("ids", [[]])[0]
    documents = payload.get("documents", [[]])[0]
    metadatas = payload.get("metadatas", [[]])[0]
    distances = payload.get("distances", [[]])[0]

    hits = []
    for chunk_id, doc, meta, distance in zip(ids, documents, metadatas, distances):
        meta = meta or {}
        hits.append(
            {
                "document_id": meta.get("document_id"),
                "chunk_id": chunk_id,
                "source": meta.get("source"),
                "section": meta.get("section"),
                "score": distance_to_score(distance),
                "distance": distance,
                "text": doc,
            }
        )

    return json.dumps(
        {
            "mcp_tool": MCP_TOOL,
            "collection": COLLECTION_NAME,
            "query": query,
            "top_k": k,
            "results": hits,
        },
        ensure_ascii=False,
        indent=2,
    )
