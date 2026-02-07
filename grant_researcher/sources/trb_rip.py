import json
import re
import time
from sqlite3 import Connection

import httpx
from bs4 import BeautifulSoup

from grant_researcher.db import upsert_grant

RSS_URL = "https://rip.trb.org/Record/RSS"

# Title prefixes that indicate non-grant items (events, publications, legal digests)
_SKIP_PREFIXES = [
    "ACRP Insight Event",
    "Synthesis of Information",
    "Legal Aspects of",
    "Legal Responsibilities",
    "Legal Implications",
    "Legal Issues",
]

# Broad keywords to cast a wide net — the RSS feed returns max 15 results per
# query, so we use many overlapping terms to maximize coverage of aviation/
# airport/safety research projects.
TRB_KEYWORDS = [
    "airport",
    "aviation",
    "runway",
    "air traffic",
    "FAA",
    "ACRP",
    "aircraft safety",
    "drone airport",
    "UAS",
    "unmanned aircraft",
    "airport AI",
    "aviation safety",
]

# Pause between requests to be respectful to the server
REQUEST_DELAY = 0.5


def _parse_rss(xml_text: str) -> list[dict]:
    """Parse RSS XML and return list of project dicts."""
    soup = BeautifulSoup(xml_text, "html.parser")
    projects = []

    for item in soup.find_all("item"):
        title_tag = item.find("title")
        guid_tag = item.find("guid")
        desc_tag = item.find("description")

        if not guid_tag:
            continue

        url = guid_tag.text.strip()
        accession = url.split("/")[-1]
        if not accession:
            continue

        title = title_tag.text.strip() if title_tag else ""
        description = desc_tag.text.strip() if desc_tag else ""

        projects.append({
            "accession": accession,
            "title": title,
            "description": description,
            "url": url,
        })

    return projects


def _is_non_grant(title: str) -> bool:
    """Return True if the title indicates a non-grant item (event, synthesis, etc.)."""
    for prefix in _SKIP_PREFIXES:
        if title.startswith(prefix):
            return True
    return False


def _title_key(title: str) -> str:
    """Normalize a title for dedup: lowercase, strip punctuation/whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", title.lower())).strip()


def _normalize(record: dict) -> dict:
    accession = record.get("accession", "")
    return {
        "source": "trb.rip",
        "external_id": accession,
        "title": record.get("title", ""),
        "agency": "TRB",
        "description": record.get("description", ""),
        "deadline": "",
        "url": record.get("url", f"https://rip.trb.org/View/{accession}"),
        "amount": "",
        "raw_json": json.dumps(record),
    }


def search_grants(keywords: list[str], conn: Connection) -> int:
    """Search TRB RIP RSS feed with broad aviation keywords, upsert results.

    The `keywords` arg from config is ignored — we use our own broader set
    since TRB RIP's RSS only returns 15 results per query.
    """
    total = 0
    seen_ids = set()
    seen_titles = set()

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for keyword in TRB_KEYWORDS:
            try:
                resp = client.get(RSS_URL, params={"q": keyword},
                                  headers={"Accept": "application/rss+xml,text/xml"})
                resp.raise_for_status()
            except httpx.HTTPError:
                continue

            for project in _parse_rss(resp.text):
                if project["accession"] in seen_ids:
                    continue
                seen_ids.add(project["accession"])

                title = project.get("title", "")
                if _is_non_grant(title):
                    continue

                # Skip near-duplicate titles (e.g. "Project #20" vs "Project 20")
                tk = _title_key(title)
                if tk in seen_titles:
                    continue
                seen_titles.add(tk)

                grant = _normalize(project)
                upsert_grant(conn, grant)
                total += 1

            time.sleep(REQUEST_DELAY)

    return total
