from datetime import datetime, timezone
from sqlite3 import Connection

from grant_researcher.db import _parse_deadline, get_scored_grants


def _is_expired(deadline: str | None) -> bool:
    """Return True if the deadline is a parseable date in the past."""
    if not deadline:
        return False
    dt = _parse_deadline(deadline)
    return dt is not None and dt < datetime.now(timezone.utc)


def print_report(conn: Connection) -> int:
    """Print a ranked table of scored grants. Returns count of grants displayed."""
    grants = [g for g in get_scored_grants(conn) if not _is_expired(g["deadline"])]

    if not grants:
        print("No scored grants to display. Run 'grant-researcher match' first.")
        return 0

    print()
    print(f"{'Score':>5}  {'Agency':<12} {'Deadline':<12} {'Title'}")
    print(f"{'─'*5}  {'─'*12} {'─'*12} {'─'*40}")

    for g in grants:
        score = g["score"]
        agency = (g["agency"] or "")[:12]
        deadline = (g["deadline"] or "N/A")[:12]
        title = (g["title"] or "")[:80]
        print(f"{score:>5}  {agency:<12} {deadline:<12} {title}")

    print()

    # Print details for top grants
    top = [g for g in grants if g["score"] >= 60]
    if top:
        print(f"── Top Matches ({len(top)}) ──")
        print()
        for g in top:
            print(f"  [{g['score']}] {g['title']}")
            print(f"       Agency:   {g['agency']}")
            print(f"       Deadline: {g['deadline'] or 'N/A'}")
            print(f"       URL:      {g['url']}")
            print(f"       Reason:   {g['score_reasoning']}")
            print()

    return len(grants)
