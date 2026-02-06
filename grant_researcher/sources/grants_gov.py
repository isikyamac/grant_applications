import json
from sqlite3 import Connection

import httpx

from grant_researcher.db import upsert_grant

SEARCH_URL = "https://api.grants.gov/v1/api/search2"


def _build_payload(keyword: str, page: int = 0, rows: int = 25) -> dict:
    return {
        "keyword": keyword,
        "oppStatuses": "forecasted|posted",
        "sortBy": "openDate|desc",
        "rows": rows,
        "startRecordNum": page * rows,
    }


def _normalize(opp: dict) -> dict:
    return {
        "source": "grants.gov",
        "external_id": str(opp.get("id", "")),
        "title": opp.get("title", ""),
        "agency": opp.get("agency", opp.get("agencyCode", "")),
        "description": opp.get("synopsis", ""),
        "deadline": opp.get("closeDate", ""),
        "url": f"https://www.grants.gov/search-results-detail/{opp.get('id', '')}",
        "amount": str(opp.get("awardCeiling", "")),
        "raw_json": json.dumps(opp),
    }


def search_grants(keywords: list[str], conn: Connection) -> int:
    """Search Grants.gov for each keyword, upsert results. Returns count of grants stored."""
    total = 0
    with httpx.Client(timeout=30) as client:
        for keyword in keywords:
            payload = _build_payload(keyword)
            resp = client.post(SEARCH_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            opportunities = data.get("data", {}).get("oppHits", [])
            for opp in opportunities:
                grant = _normalize(opp)
                upsert_grant(conn, grant)
                total += 1

    return total
