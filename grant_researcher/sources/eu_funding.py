import json
import re
import warnings
from sqlite3 import Connection

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from grant_researcher.db import upsert_grant

RSS_URL = "https://ec.europa.eu/info/funding-tenders/opportunities/data/referenceData/grantTenders-rss.xml"

AVIATION_KEYWORDS = [
    "aviation",
    "airport",
    "aircraft",
    "aerospace",
    "air traffic",
    "atm",
    "sesar",
    "runway",
    "drone",
    "uas",
    "unmanned aerial",
    "clean aviation",
    "flight",
    "airspace",
    "pilot",
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
        pub_date = pub_tag.text.strip() if pub_tag else ""

        calls.append({
            "call_id": call_id,
            "title": title,
            "description": description,
            "url": url,
            "pub_date": pub_date,
        })

    return calls


def _is_aviation_relevant(title: str, description: str) -> bool:
    """Check if the call is related to aviation based on keywords."""
    text = f"{title} {description}".lower()
    return any(kw in text for kw in AVIATION_KEYWORDS)


def _normalize(record: dict) -> dict:
    return {
        "source": "eu.funding",
        "external_id": record.get("call_id", ""),
        "title": record.get("title", ""),
        "agency": "European Commission",
        "description": record.get("description", ""),
        "deadline": record.get("pub_date", ""),
        "url": record.get("url", ""),
        "amount": "",
        "raw_json": json.dumps(record),
    }


def search_grants(keywords: list[str], conn: Connection) -> int:
    """Fetch EU Funding & Tenders RSS feed, filter for aviation, upsert results.

    The `keywords` arg from config is ignored — we filter locally using
    AVIATION_KEYWORDS since the RSS feed returns all recent calls.
    """
    total = 0

    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            xml_text = _fetch_rss(client)
    except httpx.HTTPError:
        return 0

    for call in _parse_rss(xml_text):
        if not _is_aviation_relevant(call.get("title", ""), call.get("description", "")):
            continue

        if not call.get("call_id"):
            continue

        grant = _normalize(call)
        upsert_grant(conn, grant)
        total += 1

    return total
