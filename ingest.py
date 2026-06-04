#!/usr/bin/env python3
"""
Index markdown corpus into a local persistent Chroma collection.

Chunks are split by level-2 headings (##). Each chunk gets stable IDs and metadata
required by the homework: document_id, chunk_id, source, section, chunk_index, etc.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

DOCS_DIR = Path(__file__).parent / "docs"
CHROMA_PATH = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "market_manipulation_kb"

META_LINE = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")


def parse_metadata(header_lines: list[str]) -> dict[str, str]:
    """Parse **Key:** value lines from document header."""
    meta: dict[str, str] = {}
    for line in header_lines:
        match = META_LINE.match(line.strip())
        if match:
            key = match.group(1).strip().lower().replace(" ", "_")
            meta[key] = match.group(2).strip()
    return meta


def slugify_section(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "_", slug).strip("_")
    return slug or "section"


def split_by_sections(text: str) -> tuple[str | None, list[tuple[str, str]]]:
    """
    Split markdown body into (title, [(section_heading, section_body), ...]).
    Sections start at ## headings.
    """
    lines = text.splitlines()
    title: str | None = None
    header_end = 0

    for i, line in enumerate(lines):
        if line.startswith("# ") and title is None:
            title = line[2:].strip()
            header_end = i + 1
            continue
        if line.startswith("## "):
            header_end = i
            break
        if i > 0 and line.startswith("## "):
            header_end = i
            break

    header_lines = lines[1:header_end] if title else lines[:header_end]
    meta_end = header_end
    # Metadata block is only **Key:** lines right after title
    if title:
        for j in range(1, header_end):
            if lines[j].strip() and not META_LINE.match(lines[j].strip()):
                meta_end = j
                break

    body_lines = lines[header_end:]
    sections: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_body: list[str] = []

    for line in body_lines:
        if line.startswith("## "):
            if current_heading is not None:
                body = "\n".join(current_body).strip()
                if body:
                    sections.append((current_heading, body))
            current_heading = line[3:].strip()
            current_body = []
        else:
            current_body.append(line)

    if current_heading is not None:
        body = "\n".join(current_body).strip()
        if body:
            sections.append((current_heading, body))

    return title, sections


def load_document(path: Path, docs_root: Path) -> list[dict[str, Any]]:
    """Load one markdown file and return chunk records."""
    raw = path.read_text(encoding="utf-8")
    title, sections = split_by_sections(raw)

    lines = raw.splitlines()
    header_lines: list[str] = []
    if title:
        for line in lines[1:]:
            if line.startswith("## "):
                break
            header_lines.append(line)
    else:
        for line in lines:
            if line.startswith("## "):
                break
            header_lines.append(line)

    meta = parse_metadata(header_lines)
    document_id = meta.get("document_id") or path.stem
    source = str(path.relative_to(docs_root.parent))
    doc_type = meta.get("document_type", "")
    url = meta.get("url", "")
    language = meta.get("language", "")
    last_updated = meta.get("last_updated", "")

    chunks: list[dict[str, Any]] = []
    for index, (section, body) in enumerate(sections, start=1):
        chunk_id = f"{document_id}_chunk_{index:02d}"
        # Prefix helps retrieval tie text to section heading
        document_text = f"## {section}\n\n{body}"

        record: dict[str, Any] = {
            "id": chunk_id,
            "document": document_text,
            "metadata": {
                "document_id": document_id,
                "chunk_id": chunk_id,
                "source": source,
                "section": section,
                "section_slug": slugify_section(section),
                "chunk_index": index,
                "title": title or path.stem,
                "document_type": doc_type,
                "url": url,
                "language": language,
                "last_updated": last_updated,
                "file_path": source,
            },
        }
        chunks.append(record)

    return chunks


def collect_chunks(docs_dir: Path) -> list[dict[str, Any]]:
    all_chunks: list[dict[str, Any]] = []
    md_files = sorted(docs_dir.rglob("*.md"))
    for path in md_files:
        file_chunks = load_document(path, docs_dir)
        if not file_chunks:
            print(f"  skip (no ## sections): {path.relative_to(docs_dir.parent)}")
            continue
        all_chunks.extend(file_chunks)
        print(f"  {path.relative_to(docs_dir.parent)}: {len(file_chunks)} chunks")
    return all_chunks


def chroma_metadata(meta: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Chroma accepts only scalar metadata; drop empty strings."""
    cleaned: dict[str, str | int | float | bool] = {}
    for key, value in meta.items():
        if value is None or value == "":
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def ingest(
    docs_dir: Path,
    chroma_path: Path,
    collection_name: str,
    reset: bool,
) -> None:
    print(f"Loading documents from {docs_dir} ...")
    chunks = collect_chunks(docs_dir)
    if not chunks:
        raise SystemExit("No chunks found. Check docs/ and ## section structure.")

    print(f"\nTotal chunks: {len(chunks)}")

    import chromadb

    client = chromadb.PersistentClient(path=str(chroma_path))
    if reset:
        try:
            client.delete_collection(collection_name)
            print(f"Deleted existing collection: {collection_name}")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 50
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["document"] for c in batch],
            metadatas=[chroma_metadata(c["metadata"]) for c in batch],
        )

    print(f"\nIndexed {len(chunks)} chunks into '{collection_name}' at {chroma_path}")
    print(f"Collection count: {collection.count()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index docs/ into Chroma")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=DOCS_DIR,
        help="Root directory with markdown corpus (default: ./docs)",
    )
    parser.add_argument(
        "--chroma-path",
        type=Path,
        default=CHROMA_PATH,
        help="Persistent Chroma storage path (default: ./chroma_db)",
    )
    parser.add_argument(
        "--collection",
        default=COLLECTION_NAME,
        help=f"Collection name (default: {COLLECTION_NAME})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the collection before indexing",
    )
    args = parser.parse_args()

    if not args.docs_dir.is_dir():
        raise SystemExit(f"Docs directory not found: {args.docs_dir}")

    ingest(
        docs_dir=args.docs_dir,
        chroma_path=args.chroma_path,
        collection_name=args.collection,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
