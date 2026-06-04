#!/usr/bin/env python3
"""Direct semantic search over Chroma (without MCP)."""

from __future__ import annotations

import argparse
from pathlib import Path

from config import CHROMA_PATH, COLLECTION_NAME, TEXT_PREVIEW_LEN
from mcp_chroma import distance_to_score


def search(query: str, k: int, chroma_path: Path, collection_name: str) -> None:
    import chromadb

    if not chroma_path.is_dir():
        raise SystemExit(f"Index not found at {chroma_path}. Run: python src/ingest.py --reset")

    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as exc:
        raise SystemExit(
            f"Collection '{collection_name}' not found. Run: python src/ingest.py --reset"
        ) from exc

    if collection.count() == 0:
        raise SystemExit("Collection is empty. Run: python src/ingest.py --reset")

    results = collection.query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    print(f"Query: {query}")
    print(f"Top-k: {k}\n")

    if not ids:
        print("No results found.")
        return

    for rank, (chunk_id, doc, meta, distance) in enumerate(
        zip(ids, documents, metadatas, distances), start=1
    ):
        meta = meta or {}
        print(
            f"{rank}. document_id={meta.get('document_id', '?')}, "
            f"chunk_id={chunk_id}, score={distance_to_score(distance)}, distance={distance}"
        )
        print(f"   source={meta.get('source', '?')}")
        if meta.get("section"):
            print(f"   section={meta['section']}")
        preview = (doc or "").replace("\n", " ").strip()
        if len(preview) > TEXT_PREVIEW_LEN:
            preview = preview[:TEXT_PREVIEW_LEN] + "..."
        print(f"   text={preview}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the knowledge base in Chroma")
    parser.add_argument("--query", "-q", required=True)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--chroma-path", type=Path, default=CHROMA_PATH)
    parser.add_argument("--collection", default=COLLECTION_NAME)
    args = parser.parse_args()

    if args.k < 1:
        raise SystemExit("--k must be >= 1")

    search(args.query, args.k, args.chroma_path, args.collection)


if __name__ == "__main__":
    main()
