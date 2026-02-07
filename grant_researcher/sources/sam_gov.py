import json
from datetime import datetime, timedelta
from sqlite3 import Connection

import httpx

from grant_researcher.db import upsert_grant

SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"


def _build_params(keyword: str, api_key: str) -> dict:
    today = datetime.now()
    posted_from = (today - timedelta(days=90)).strftime("%m/%d/%Y")
    posted_to = today.strftime("%m/%d/%Y")

    return {
        "api_key": api_key,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "title": keyword,
        "ptype": "o,p,k",
        "limit": 100,
        "offset": 0,
    }


def _normalize(opp: dict) -> dict:
    notice_id = opp.get("noticeId", "")
    return {
        "source": "sam.gov",
        "external_id": notice_id,
        "title": opp.get("title", ""),
        "agency": opp.get("fullParentPathName", opp.get("departmentName", "")),
        "description": opp.get("description", opp.get("organizationType", "")),
        "deadline": opp.get("responseDeadLine", opp.get("archiveDate", "")),
        "url": f"https://sam.gov/opp/{notice_id}/view",
        "amount": "",
        "raw_json": json.dumps(opp),
    }


def search_grants(keywords: list[str], conn: Connection, api_key: str) -> int:
    """Search SAM.gov for each keyword, upsert results. Returns count of grants stored."""
    total = 0
    with httpx.Client(timeout=30) as client:
        for keyword in keywords:
            params = _build_params(keyword, api_key)
            resp = client.get(SEARCH_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            opportunities = data.get("opportunitiesData", [])
            for opp in opportunities:
                grant = _normalize(opp)
                if grant["external_id"]:
                    upsert_grant(conn, grant)
                    total += 1

    return total
