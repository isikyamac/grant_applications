import json
import sqlite3

import anthropic

from grant_evaluator.config import CriterionConfig, EvaluatorConfig
from grant_evaluator.db import create_review, create_review_score


def _build_prompt(
    proposal_text: str,
    criteria: list[CriterionConfig],
    criteria_text: str | None,
) -> str:
    criteria_section = ""
    if criteria_text:
        criteria_section = f"""## Evaluation Criteria (from RFP/solicitation)
{criteria_text}
"""
    else:
        criteria_section = "## Evaluation Criteria\nEvaluate against general best practices for grant proposals.\n"

    criteria_list = []
    for i, c in enumerate(criteria, 1):
        criteria_list.append(f"{i}. {c.name}: {c.description} (weight: {c.weight}%)")
    criteria_list_text = "\n".join(criteria_list)

    criteria_names = json.dumps([c.name for c in criteria])

    return f"""You are a grant proposal reviewer. Evaluate this proposal against each criterion below.
Score each criterion from 0 to 100.

## Proposal
{proposal_text}

{criteria_section}
## Criteria to Score
{criteria_list_text}

For EACH criterion, provide a score and detailed feedback.
Respond with ONLY this JSON (no other text):
{{
  "criteria_scores": [
    {{
      "criterion": "criterion_name",
      "score": 0,
      "strengths": ["strength 1", "strength 2"],
      "weaknesses": ["weakness 1", "weakness 2"],
      "suggestions": ["actionable suggestion 1", "actionable suggestion 2"]
    }}
  ]
}}

You MUST include an entry for each of these criteria: {criteria_names}"""


def _build_compliance_prompt(proposal_text: str, guidelines_text: str) -> str:
    return f"""You are a grant proposal compliance reviewer. Check whether this proposal adheres to the submission guidelines and rules below.

## Proposal
{proposal_text}

## Submission Guidelines / Rules
{guidelines_text}

## Instructions
Extract every checkable rule or requirement from the guidelines, then check whether the proposal complies with each one.

For each rule, determine:
- status: "pass", "fail", or "partial"
- explanation: brief explanation of what you found (or didn't find) in the proposal

Respond with ONLY this JSON (no other text):
{{
  "checks": [
    {{
      "rule": "Short description of the rule/requirement",
      "status": "pass|fail|partial",
      "explanation": "What was found or missing in the proposal"
    }}
  ]
}}"""


def _extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown code blocks."""
    text = text.strip()
    if "```" in text:
        # Find opening fence
        fence_start = text.index("```")
        after_fence = text[fence_start + 3:]
        # Skip to next newline (past language identifier)
        nl = after_fence.find("\n")
        if nl == -1:
            return text
        content_start = fence_start + 3 + nl + 1
        # Find closing fence
        closing = text.find("```", content_start)
        if closing == -1:
            return text[content_start:].strip()
        return text[content_start:closing].strip()
    # Try to find JSON object directly
    brace_start = text.find("{")
    if brace_start >= 0:
        return text[brace_start:]
    return text


def _parse_compliance_response(text: str) -> list[dict]:
    json_text = _extract_json(text)
    parsed = json.loads(json_text)
    return parsed["checks"]


def _parse_reviewer_response(text: str, criteria: list[CriterionConfig]) -> list[dict]:
    json_text = _extract_json(text)
    parsed = json.loads(json_text)
    scores = parsed["criteria_scores"]

    # Validate all criteria are present
    scored_names = {s["criterion"] for s in scores}
    expected_names = {c.name for c in criteria}
    missing = expected_names - scored_names
    if missing:
        raise ValueError(f"Reviewer did not score criteria: {missing}")

    return scores


def run_compliance_check(
    proposal_text: str,
    guidelines_text: str,
    config: EvaluatorConfig,
    on_progress=None,
) -> list[dict]:
    """Run a compliance check against guidelines. Returns list of check dicts."""
    if not config.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    if on_progress:
        on_progress("  Running compliance check...")

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    prompt = _build_compliance_prompt(proposal_text, guidelines_text)

    message = client.messages.create(
        model=config.model,
        max_tokens=4096,
        temperature=0.2,  # low temperature for factual compliance checking
        messages=[{"role": "user", "content": prompt}],
    )

    return _parse_compliance_response(message.content[0].text)


def run_panel(
    conn: sqlite3.Connection,
    run_id: int,
    proposal_text: str,
    criteria: list[CriterionConfig],
    criteria_text: str | None,
    config: EvaluatorConfig,
    on_progress=None,
) -> list[dict]:
    """Run a panel of independent reviewers. Returns list of per-reviewer score dicts."""
    if not config.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    prompt = _build_prompt(proposal_text, criteria, criteria_text)

    # Build weight lookup for computing weighted overall score
    weight_map = {c.name: c.weight for c in criteria}

    all_reviews = []

    for reviewer_num in range(1, config.panel_size + 1):
        if on_progress:
            on_progress(f"  Reviewer {reviewer_num}/{config.panel_size}...")

        message = client.messages.create(
            model=config.model,
            max_tokens=4096,
            temperature=config.temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = message.content[0].text
        scores = _parse_reviewer_response(raw_text, criteria)

        # Compute weighted overall score
        total_weight = sum(weight_map.values())
        weighted_sum = sum(
            s["score"] * weight_map.get(s["criterion"], 0) for s in scores
        )
        overall_score = weighted_sum / total_weight if total_weight else 0

        # Store review
        review_id = create_review(
            conn, run_id, reviewer_num, overall_score, raw_text, config.model
        )

        # Store individual criterion scores
        for s in scores:
            create_review_score(
                conn,
                review_id,
                s["criterion"],
                s["score"],
                s.get("strengths", []),
                s.get("weaknesses", []),
                s.get("suggestions", []),
            )

        all_reviews.append({"reviewer_number": reviewer_num, "scores": scores, "overall": overall_score})

    return all_reviews
