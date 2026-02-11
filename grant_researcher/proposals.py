import hashlib
from pathlib import Path
from sqlite3 import Connection

import pymupdf

from grant_researcher.db import get_proposals, upsert_proposal


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _folder_hash(pdf_paths: list[Path]) -> str:
    """Combined SHA-256 over sorted filenames + file contents."""
    h = hashlib.sha256()
    for p in sorted(pdf_paths, key=lambda x: x.name):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def _extract_text(path: Path) -> str:
    doc = pymupdf.open(path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n\n".join(pages)


def _extract_folder_text(pdf_paths: list[Path]) -> str:
    """Concatenate text from multiple PDFs with section headers."""
    parts = []
    for p in sorted(pdf_paths, key=lambda x: x.name):
        parts.append(f"=== {p.name} ===")
        parts.append(_extract_text(p))
    return "\n\n".join(parts)


def ingest_proposals(proposals_dir: Path, conn: Connection) -> list[str]:
    """Scan proposals/ for PDFs and subfolders, extract text, and cache in DB.

    Top-level PDFs are ingested individually. Subdirectories containing PDFs
    are ingested as a single proposal entry (folder name as filename,
    concatenated text from all PDFs inside).

    Returns list of filenames that were ingested (new or updated).
    """
    existing = {p["filename"]: p["file_hash"] for p in get_proposals(conn)}
    ingested = []

    # Top-level PDFs
    for pdf_path in sorted(proposals_dir.glob("*.pdf")):
        filename = pdf_path.name
        fhash = _file_hash(pdf_path)

        if existing.get(filename) == fhash:
            continue

        text = _extract_text(pdf_path)
        upsert_proposal(conn, filename, text, fhash)
        ingested.append(filename)

    # Subdirectories (multi-part proposals)
    for subdir in sorted(proposals_dir.iterdir()):
        if not subdir.is_dir():
            continue
        pdf_paths = sorted(subdir.glob("*.pdf"))
        if not pdf_paths:
            continue

        folder_name = subdir.name
        fhash = _folder_hash(pdf_paths)

        if existing.get(folder_name) == fhash:
            continue

        text = _extract_folder_text(pdf_paths)
        upsert_proposal(conn, folder_name, text, fhash)
        ingested.append(folder_name)

    return ingested
