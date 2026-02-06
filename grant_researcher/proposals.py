import hashlib
from pathlib import Path
from sqlite3 import Connection

import pymupdf

from grant_researcher.db import get_proposals, upsert_proposal


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_text(path: Path) -> str:
    doc = pymupdf.open(path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n\n".join(pages)


def ingest_proposals(proposals_dir: Path, conn: Connection) -> list[str]:
    """Scan proposals/ for PDFs, extract text, and cache in DB.

    Returns list of filenames that were ingested (new or updated).
    """
    existing = {p["filename"]: p["file_hash"] for p in get_proposals(conn)}
    ingested = []

    for pdf_path in sorted(proposals_dir.glob("*.pdf")):
        filename = pdf_path.name
        fhash = _file_hash(pdf_path)

        if existing.get(filename) == fhash:
            continue

        text = _extract_text(pdf_path)
        upsert_proposal(conn, filename, text, fhash)
        ingested.append(filename)

    return ingested
