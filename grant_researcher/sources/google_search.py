import json
from sqlite3 import Connection
from urllib.parse import urlparse

import httpx

from grant_researcher.db import upsert_grant

SEARCH_URL = "https://www.googleapis.com/customsearch/v1"


def _normalize(result: dict) -> dict:
    link = result.get("link", "")
    domain = urlparse(link).netloc if link else ""

    return {
        "source": "google.search",
        "external_id": link,
        "title": result.get("title", ""),
        "agency": domain,
        "description": result.get("snippet", ""),
        "deadline": "",
        "url": link,
        "amount": "",
        "raw_json": json.dumps(result),
    }


def search_grants(
    keywords: list[str], conn: Connection, api_key: str, cse_id: str
) -> int:
    """Search Google Custom Search for each keyword, upsert results. Returns count of grants stored."""
    total = 0
    with httpx.Client(timeout=30) as client:
        for keyword in keywords:
            query = f"{keyword} grant funding opportunity"
            params = {
                "q": query,
                "key": api_key,
                "cx": cse_id,
                "num": 10,
            }
            resp = client.get(SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                grant = _normalize(item)
                if grant["external_id"]:
                    upsert_grant(conn, grant)
                    total += 1

    return total
