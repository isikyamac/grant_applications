import json
from pathlib import Path

import anthropic
import pymupdf

from grant_evaluator.config import CriterionConfig


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        doc = pymupdf.open(path)
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n\n".join(pages)
    else:
        return path.read_text()


def extract_rubric(
    criteria_text: str, api_key: str, model: str
) -> list[CriterionConfig] | None:
    """Use Claude to extract a scoring rubric from RFP/solicitation text.

    Returns a list of CriterionConfig if a rubric is found, None otherwise.
    """
    prompt = f"""Analyze this RFP/solicitation document and extract the scoring rubric or evaluation criteria.

## Document
{criteria_text}

## Instructions
Extract the scoring/evaluation criteria used to evaluate proposals. For each criterion, provide:
- name: a short snake_case identifier (e.g. "technical_merit")
- description: what the criterion evaluates — be specific and include concrete requirements
  from the document that reviewers should check for
- weight: the percentage weight (all weights should sum to 100)

If the document contains explicit scoring criteria with weights, use those.
If the document describes evaluation factors without explicit weights, estimate reasonable weights.
If no evaluation criteria can be identified, respond with exactly: NO_RUBRIC_FOUND

Respond in this JSON format (and nothing else):
{{
  "criteria": [
    {{"name": "criterion_name", "description": "what it evaluates", "weight": 30}},
    ...
  ]
}}"""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()

    if "NO_RUBRIC_FOUND" in response_text:
        return None

    # Extract JSON from response (handle markdown code blocks)
    if "```" in response_text:
        start = response_text.index("```") + 3
        if response_text[start:].startswith("json"):
            start += 4
        end = response_text.find("```", start)
        if end == -1:
            response_text = response_text[start:].strip()
        else:
            response_text = response_text[start:end].strip()

    parsed = json.loads(response_text)
    criteria = []
    for c in parsed["criteria"]:
        criteria.append(
            CriterionConfig(
                name=c["name"],
                description=c["description"],
                weight=int(c["weight"]),
            )
        )
    return criteria
