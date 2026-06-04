"""Project paths and shared constants."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
CHROMA_PATH = ROOT / "chroma_db"
ENV_FILE = ROOT / ".env"

EVAL_DIR = ROOT / "eval"
EVAL_QUERIES = EVAL_DIR / "queries.csv"
EVAL_RESULTS = EVAL_DIR / "results.csv"
EVAL_REPORT = EVAL_DIR / "report.md"

COLLECTION_NAME = "market_manipulation_kb"
MCP_TOOL = "chroma_query_documents"
TEXT_PREVIEW_LEN = 280
