#!/usr/bin/env python3
"""
Demo semantic search over the indexed Chroma collection.

Run after ingest.py:
    python search_demo.py --query "What is spoofing?" --k 3
"""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

CHROMA_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "market_manipulation_kb"
TEXT_PREVIEW_LEN = 280


def distance_to_score(distance: float | None) -> float | None:
    """Convert Chroma cosine distance to a simple similarity score."""
    if distance is None:
        return None
    return round(1.0 - distance, 4)


def search(
    query: str,
    k: int,
    chroma_path: Path,
    collection_name: str,
) -> None:
    import chromadb

    if not chroma_path.is_dir():
        raise SystemExit(
            f"Index not found at {chroma_path}. Run: python ingest.py --reset"
        )

    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as exc:
        raise SystemExit(
            f"Collection '{collection_name}' not found. Run: python ingest.py --reset"
        ) from exc

    if collection.count() == 0:
        raise SystemExit("Collection is empty. Run: python ingest.py --reset")

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
    print(f"Top-k: {k}")
    print()

    if not ids:
        print("No results found.")
        return

    for rank, (chunk_id, doc, meta, distance) in enumerate(
        zip(ids, documents, metadatas, distances), start=1
    ):
        meta = meta or {}
        score = distance_to_score(distance)
        document_id = meta.get("document_id", "?")
        source = meta.get("source", "?")
        section = meta.get("section", "")

        print(
            f"{rank}. document_id={document_id}, chunk_id={chunk_id}, "
            f"score={score}, distance={distance}"
        )
        print(f"   source={source}")
        if section:
            print(f"   section={section}")
        preview = (doc or "").replace("\n", " ").strip()
        if len(preview) > TEXT_PREVIEW_LEN:
            preview = preview[:TEXT_PREVIEW_LEN] + "..."
        print(f"   text={preview}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the knowledge base in Chroma")
    parser.add_argument(
        "--query",
        "-q",
        required=True,
        help="Search query text",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Number of results (default: 3)",
    )
    parser.add_argument(
        "--chroma-path",
        type=Path,
        default=CHROMA_PATH,
        help="Chroma persistence directory",
    )
    parser.add_argument(
        "--collection",
        default=COLLECTION_NAME,
        help=f"Collection name (default: {COLLECTION_NAME})",
    )
    args = parser.parse_args()

    if args.k < 1:
        raise SystemExit("--k must be >= 1")

    search(
        query=args.query,
        k=args.k,
        chroma_path=args.chroma_path,
        collection_name=args.collection,
    )


if __name__ == "__main__":
    main()
