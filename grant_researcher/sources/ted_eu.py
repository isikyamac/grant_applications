import json
import time
from sqlite3 import Connection

import httpx

from grant_researcher.db import upsert_grant

SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"

# Expert query syntax: FT = (term OR term ...) with date filter for recent notices
QUERY = (
    'FT = (aviation OR aircraft OR aerospace OR airport OR SESAR'
    ' OR "air traffic management" OR "unmanned aerial"'
    ' OR "generative AI" OR "artificial intelligence" OR "machine learning")'
    " AND publication-date > 20240101"
)

FIELDS = ["publication-number", "publication-date", "notice-title"]

PAGE_LIMIT = 100
MAX_PAGES = 5
REQUEST_DELAY = 1.0


def _build_payload(page: int = 1) -> dict:
    return {
        "query": QUERY,
        "fields": FIELDS,
        "page": page,
        "limit": PAGE_LIMIT,
    }


def _fetch_notices(client: httpx.Client) -> list[dict]:
    """Fetch matching notices, paginating with delays to avoid rate limits."""
    notices = []

    for page in range(1, MAX_PAGES + 1):
        if page > 1:
            time.sleep(REQUEST_DELAY)

        payload = _build_payload(page=page)
        try:
            resp = client.post(SEARCH_URL, json=payload)
            resp.raise_for_status()
        except httpx.HTTPError:
            break

        data = resp.json()
        results = data.get("notices", [])
        if not results:
            break

        notices.extend(results)

        total = data.get("totalNoticeCount", 0)
        if len(notices) >= total:
            break

    return notices


def _normalize(notice: dict) -> dict:
    notice_id = notice.get("publication-number", "")
    title_map = notice.get("notice-title", {})
    # Prefer English title, fall back to first available language
    if isinstance(title_map, dict):
        title = title_map.get("eng", "")
        if not title and title_map:
            title = next(iter(title_map.values()))
    else:
        title = str(title_map)

    pub_date = notice.get("publication-date", "")

    return {
        "source": "ted.europa.eu",
        "external_id": notice_id,
        "title": title,
        "agency": "TED (EU)",
        "description": "",
        "deadline": pub_date,
        "url": f"https://ted.europa.eu/en/notice/{notice_id}",
        "amount": "",
        "raw_json": json.dumps(notice, default=str),
    }


def search_grants(keywords: list[str], conn: Connection) -> int:
    """Search TED for aviation-related procurement notices, upsert results.

    The `keywords` arg from config is ignored — we use a fixed aviation query.
    """
    total = 0

    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            notices = _fetch_notices(client)
    except httpx.HTTPError:
        return 0

    for notice in notices:
        if not notice.get("publication-number"):
            continue

        grant = _normalize(notice)
        upsert_grant(conn, grant)
        total += 1

    return total
