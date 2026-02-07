import json
import time
from sqlite3 import Connection

import httpx

from grant_researcher.db import upsert_grant

SEARCH_URL = "https://api.www.sbir.gov/public/api/solicitations"


def _build_params(keyword: str) -> dict:
    return {
        "keyword": keyword,
        "open": "1",
        "rows": 50,
        "start": 0,
    }


def _normalize(sol: dict) -> dict:
    topics = sol.get("topics") or []
    topic_text = "; ".join(
        t.get("topicTitle", "") for t in topics if t.get("topicTitle")
    )
    description = sol.get("sbpiDescription", "") or topic_text

    sol_number = sol.get("solicitationNumber", sol.get("solicitation_number", ""))

    return {
        "source": "sbir.gov",
        "external_id": sol_number,
        "title": sol.get("solicitationTitle", sol.get("title", "")),
        "agency": sol.get("agency", ""),
        "description": description,
        "deadline": sol.get("closeDate", sol.get("close_date", "")),
        "url": f"https://www.sbir.gov/node/{sol.get('systemId', '')}",
        "amount": "",
        "raw_json": json.dumps(sol),
    }


def _get_with_retry(client: httpx.Client, url: str, params: dict, max_retries: int = 4) -> httpx.Response:
    for attempt in range(max_retries):
        resp = client.get(url, params=params)
        if resp.status_code == 429:
            wait = 3 * (2 ** attempt)  # 3, 6, 12, 24s
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    resp.raise_for_status()
    return resp


def search_grants(keywords: list[str], conn: Connection) -> int:
    """Search SBIR.gov for each keyword, upsert results. Returns count of grants stored."""
    total = 0
    with httpx.Client(timeout=30) as client:
        for keyword in keywords:
            params = _build_params(keyword)
            resp = _get_with_retry(client, SEARCH_URL, params)
            data = resp.json()

            solicitations = data if isinstance(data, list) else data.get("data", [])
            for sol in solicitations:
                grant = _normalize(sol)
                if grant["external_id"]:
                    upsert_grant(conn, grant)
                    total += 1

            time.sleep(0.5)

    return total
