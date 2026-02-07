import math
import re
from sqlite3 import Connection
from typing import Callable

import anthropic

from grant_researcher.config import Config
from grant_researcher.db import get_proposals, get_unscored_grants, update_score

BATCH_SIZE = 10


def _build_batch_filter_prompt(
    grants: list[dict], config: Config, proposal_texts: list[str]
) -> str:
    proposals_section = ""
    if proposal_texts:
        condensed = []
        for i, text in enumerate(proposal_texts, 1):
            snippet = text[:2000]
            condensed.append(f"--- Proposal {i} ---\n{snippet}")
        proposals_section = (
            "\n\n## Company Proposals (for context)\n" + "\n\n".join(condensed)
        )

    grant_list = []
    for i, g in enumerate(grants, 1):
        desc_snippet = (g["description"] or "N/A")[:300]
        grant_list.append(f"{i}. {g['title']} | {g['agency']} | {desc_snippet}")
    grants_text = "\n".join(grant_list)

    return f"""You are filtering government grant opportunities for relevance to a company.

## Company Profile
- Name: {config.company.name}
- Description: {config.company.description}
- Focus Areas: {', '.join(config.company.focus_areas)}
- Eligibility: {', '.join(config.company.eligibility)}
{proposals_section}

## Grant Opportunities
{grants_text}

## Instructions
Review each grant and identify which ones are potentially relevant to the company (would score above 20 out of 100). A grant can be relevant for ANY of these reasons:
1. Domain relevance — the grant targets the company's industry or focus areas
2. Technology/capability match — the grant funds technologies the company works with (e.g. AI, machine learning, generative AI) even if the grant is not industry-specific
3. Eligibility fit — the grant targets a category the company belongs to (e.g. SME, small business, startup)

A generic AI or SME grant where the company is clearly eligible and has matching capabilities IS relevant.

Respond with ONLY a comma-separated list of the grant numbers that are potentially relevant. If none are relevant, respond with "NONE".

Example response: 1, 3, 7"""


def _parse_batch_filter_response(text: str, grants: list[dict]) -> list[dict]:
    text = text.strip()
    if text.upper() == "NONE":
        return []

    numbers = re.findall(r"\d+", text)
    seen = set()
    candidates = []
    for n in numbers:
        idx = int(n) - 1
        if 0 <= idx < len(grants) and idx not in seen:
            seen.add(idx)
            candidates.append(grants[idx])
    return candidates


def _build_prompt(grant: dict, config: Config, proposal_texts: list[str]) -> str:
    proposals_section = ""
    if proposal_texts:
        condensed = []
        for i, text in enumerate(proposal_texts, 1):
            snippet = text[:2000]
            condensed.append(f"--- Proposal {i} ---\n{snippet}")
        proposals_section = (
            "\n\n## Company Proposals (for context)\n" + "\n\n".join(condensed)
        )

    return f"""You are evaluating whether a government grant opportunity is relevant to a company.

## Company Profile
- Name: {config.company.name}
- Description: {config.company.description}
- Focus Areas: {', '.join(config.company.focus_areas)}
- Eligibility: {', '.join(config.company.eligibility)}
{proposals_section}

## Grant Opportunity
- Title: {grant['title']}
- Agency: {grant['agency']}
- Description: {grant['description'] or 'N/A'}
- Deadline: {grant['deadline'] or 'N/A'}
- Amount: {grant['amount'] or 'N/A'}

## Instructions
Score this grant's relevance to the company from 0 to 100 based on three dimensions:
1. Domain relevance — does the grant target the company's industry or focus areas?
2. Technology/capability match — does the grant fund technologies the company works with (e.g. AI, machine learning, generative AI), even if the grant is not industry-specific?
3. Eligibility fit — does the grant target a category the company belongs to (e.g. SME, small business, startup)?

A grant that strongly matches on 2 or more dimensions should score high even if it's not specific to the company's industry. For example, a generic "AI for SMEs" grant is a good fit for an AI company that is an SME.

Scoring guide:
- 0-20: No meaningful match on any dimension
- 21-40: Weak match on one dimension
- 41-60: Moderate match on one dimension, or weak match on two
- 61-80: Strong match on two dimensions
- 81-100: Strong match on all three dimensions

Respond in exactly this format:
SCORE: <number>
REASONING: <1-2 sentence explanation>"""


def _parse_response(text: str) -> tuple[int, str]:
    score = 0
    reasoning = text

    for line in text.strip().splitlines():
        line = line.strip()
        if line.upper().startswith("SCORE:"):
            try:
                score = int(line.split(":", 1)[1].strip())
                score = max(0, min(100, score))
            except ValueError:
                pass
        elif line.upper().startswith("REASONING:"):
            reasoning = line.split(":", 1)[1].strip()

    return score, reasoning


def match_grants(
    config: Config,
    conn: Connection,
    on_progress: Callable[[str], None] | None = None,
) -> int:
    """Score unscored grants using a two-pass approach. Returns count of grants scored."""
    if not config.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    unscored = get_unscored_grants(conn)

    if not unscored:
        return 0

    proposals = get_proposals(conn)
    proposal_texts = [p["text"] for p in proposals]

    # --- Pass 1: Batch triage with Haiku ---
    num_batches = math.ceil(len(unscored) / BATCH_SIZE)
    if on_progress:
        on_progress(
            f"Pass 1: Filtering {len(unscored)} grants in {num_batches} batch(es)..."
        )

    candidates = []
    for i in range(0, len(unscored), BATCH_SIZE):
        batch = unscored[i : i + BATCH_SIZE]
        prompt = _build_batch_filter_prompt(batch, config, proposal_texts)

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        batch_candidates = _parse_batch_filter_response(response_text, batch)
        candidates.extend(batch_candidates)

        # Mark filtered-out grants with score=0
        candidate_ids = {g["id"] for g in batch_candidates}
        for grant in batch:
            if grant["id"] not in candidate_ids:
                update_score(conn, grant["id"], 0, "Filtered out in batch triage.")

    if on_progress:
        on_progress(f"Pass 1 complete: {len(candidates)} candidate(s) identified.")

    # --- Pass 2: Individual scoring with Sonnet ---
    if candidates and on_progress:
        on_progress(f"Pass 2: Scoring {len(candidates)} candidate(s) individually...")

    for grant in candidates:
        prompt = _build_prompt(grant, config, proposal_texts)

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        score, reasoning = _parse_response(response_text)
        update_score(conn, grant["id"], score, reasoning)

    total_scored = len(unscored)
    if on_progress:
        on_progress(f"Done. Scored {total_scored} grant(s).")

    return total_scored
