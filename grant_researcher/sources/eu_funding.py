import json
import re
import warnings
from datetime import datetime, timezone
from sqlite3 import Connection

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from grant_researcher.db import upsert_grant

RSS_URL = "https://ec.europa.eu/info/funding-tenders/opportunities/data/referenceData/grantTenders-rss.xml"

KEYWORDS = [
    # Aviation domain
    "aviation", "airport", "aircraft", "aerospace", "air traffic",
    "atm", "sesar", "runway", "drone", "uas", "unmanned aerial",
    "clean aviation", "flight", "airspace",
    # Technology / capability
    "artificial intelligence", "machine learning", "deep learning",
    "generative ai", "foundation model", "large language model",
    # Company profile
    "sme", "small business", "startup", "start-up", "accelerator",
    "pre-accelerator", "innovation",
]


def _fetch_rss(client: httpx.Client) -> str:
    resp = client.get(RSS_URL, headers={"Accept": "application/rss+xml,text/xml"})
    resp.raise_for_status()
    return resp.text


def _parse_rss(xml_text: str) -> list[dict]:
    """Parse RSS XML and return list of call dicts."""
    soup = BeautifulSoup(xml_text, "html.parser")
    calls = []

    for item in soup.find_all("item"):
        title_tag = item.find("title")
        link_tag = item.find("link")
        desc_tag = item.find("description")
        pub_tag = item.find("pubdate")

        if not link_tag:
            continue

        url = link_tag.text.strip() if link_tag.string else ""
        # Handle BeautifulSoup's link tag behavior — sometimes the URL is
        # the next sibling text node rather than inside the tag
        if not url:
            next_sib = link_tag.next_sibling
            if next_sib and isinstance(next_sib, str):
                url = next_sib.strip()

        if not url:
            continue

        # Extract call identifier from URL — typically in callCode= param
        # e.g. ...;callCode=RENEWFM-2025-INVEST-MULTI
        call_id_match = re.search(r"callCode=([A-Za-z0-9_-]+)", url)
        call_id = call_id_match.group(1) if call_id_match else url.split("/")[-1]

        title = title_tag.text.strip() if title_tag else ""
        description = desc_tag.text.strip() if desc_tag else ""

        # Extract real deadline from description HTML
        # Format: <b>Deadline</b>: Thu, 26 Sep 2024 17:00:00 (Brussels local time)
        deadline = ""
        deadline_match = re.search(
            r"Deadline</b>:\s*(\w+,\s+\d+\s+\w+\s+\d{4}\s+[\d:]+)", description
        )
        if deadline_match:
            deadline = deadline_match.group(1)

        calls.append({
            "call_id": call_id,
            "title": title,
            "description": description,
            "url": url,
            "deadline": deadline,
        })

    return calls


def _is_relevant(title: str, description: str) -> bool:
    """Check if the call matches aviation, AI, or SME keywords."""
    text = f"{title} {description}".lower()
    return any(kw in text for kw in KEYWORDS)


def _is_deadline_future(deadline_str: str) -> bool:
    """Return True if the deadline is in the future or unparseable."""
    if not deadline_str:
        return True  # keep calls with no deadline (open-ended)
    try:
        # "Thu, 26 Sep 2024 17:00:00"
        dt = datetime.strptime(deadline_str, "%a, %d %b %Y %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        return dt > datetime.now(timezone.utc)
    except ValueError:
        return True  # keep if we can't parse


def _normalize(record: dict) -> dict:
    return {
        "source": "eu.funding",
        "external_id": record.get("call_id", ""),
        "title": record.get("title", ""),
        "agency": "European Commission",
        "description": record.get("description", ""),
        "deadline": record.get("deadline", ""),
        "url": record.get("url", ""),
        "amount": "",
        "raw_json": json.dumps(record),
    }


def search_grants(keywords: list[str], conn: Connection) -> int:
    """Fetch EU Funding & Tenders RSS feed, filter for relevance, upsert results.

    The `keywords` arg from config is ignored — we filter locally using
    KEYWORDS (aviation + AI + SME) since the RSS feed returns all recent calls.
    """
    total = 0

    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            xml_text = _fetch_rss(client)
    except httpx.HTTPError:
        return 0

    for call in _parse_rss(xml_text):
        if not call.get("call_id"):
            continue

        if not _is_deadline_future(call.get("deadline", "")):
            continue

        if not _is_relevant(call.get("title", ""), call.get("description", "")):
            continue

        grant = _normalize(call)
        upsert_grant(conn, grant)
        total += 1

    return total
