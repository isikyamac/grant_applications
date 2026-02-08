import statistics
from collections import defaultdict

from grant_evaluator.config import CriterionConfig


def _deduplicate_strings(items: list[str]) -> list[str]:
    """Deduplicate similar strings by lowercased comparison."""
    seen = {}
    for item in items:
        key = item.strip().lower()
        if key not in seen:
            seen[key] = item
    return list(seen.values())


def _items_mentioned_by_n(all_items: list[list[str]], min_count: int) -> list[str]:
    """Return items mentioned by at least min_count reviewers."""
    counts = defaultdict(int)
    canonical = {}
    for reviewer_items in all_items:
        seen_this_reviewer = set()
        for item in reviewer_items:
            key = item.strip().lower()
            if key not in seen_this_reviewer:
                seen_this_reviewer.add(key)
                counts[key] += 1
                if key not in canonical:
                    canonical[key] = item
    return [canonical[k] for k, v in counts.items() if v >= min_count]


def aggregate_reviews(
    reviews: list[dict], criteria: list[CriterionConfig]
) -> dict:
    """Aggregate scores across all reviewers.

    Args:
        reviews: list of dicts with keys "reviewer_number", "scores", "overall"
        criteria: list of CriterionConfig used for this evaluation

    Returns:
        dict with "overall_score", "per_criterion", and per-criterion aggregates
    """
    weight_map = {c.name: c.weight for c in criteria}

    # Group scores by criterion
    by_criterion: dict[str, list[dict]] = defaultdict(list)
    for review in reviews:
        for score_entry in review["scores"]:
            by_criterion[score_entry["criterion"]].append(score_entry)

    per_criterion = {}
    for criterion_name, entries in by_criterion.items():
        scores = [e["score"] for e in entries]
        all_strengths = [e.get("strengths", []) for e in entries]
        all_weaknesses = [e.get("weaknesses", []) for e in entries]
        all_suggestions = [e.get("suggestions", []) for e in entries]

        median_score = statistics.median(scores)
        mean_score = statistics.mean(scores)
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0

        # Items mentioned by 2+ reviewers (or all if panel_size < 3)
        min_mentions = min(2, len(entries))
        strengths = _items_mentioned_by_n(all_strengths, min_mentions)
        weaknesses = _items_mentioned_by_n(all_weaknesses, min_mentions)
        # Suggestions: union of all, deduplicated
        flat_suggestions = [s for sublist in all_suggestions for s in sublist]
        suggestions = _deduplicate_strings(flat_suggestions)

        per_criterion[criterion_name] = {
            "median_score": median_score,
            "mean_score": round(mean_score, 1),
            "std_dev": round(std_dev, 1),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "suggestions": suggestions,
            "weight": weight_map.get(criterion_name, 0),
        }

    # Overall score: weighted median
    total_weight = sum(weight_map.values())
    if total_weight > 0:
        overall_score = sum(
            per_criterion[name]["median_score"] * weight_map[name]
            for name in per_criterion
            if name in weight_map
        ) / total_weight
    else:
        overall_score = 0.0

    return {
        "overall_score": round(overall_score, 1),
        "per_criterion": per_criterion,
        "panel_size": len(reviews),
    }
