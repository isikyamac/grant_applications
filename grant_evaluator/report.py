import json
from pathlib import Path
from sqlite3 import Connection

from grant_evaluator.db import get_all_runs, get_latest_run, get_run_reviews, get_review_scores


def print_report(conn: Connection, proposal_id: int | None = None) -> None:
    """Print evaluation report for the latest run (or latest for a specific proposal)."""
    run = get_latest_run(conn, proposal_id)
    if not run:
        print("No evaluation runs found. Run 'evaluate' first.")
        return

    rubric = json.loads(run["rubric"]) if run["rubric"] else []
    summary = json.loads(run["aggregate_summary"]) if run["aggregate_summary"] else None
    compliance = json.loads(run["compliance_results"]) if run.get("compliance_results") else None

    # Header
    print()
    print(f"{'=' * 60}")
    print(f"  Evaluation Report — Run #{run['id']}")
    print(f"{'=' * 60}")
    print(f"  Proposal ID:    {run['proposal_id']}")
    if run["criteria_file"]:
        print(f"  Criteria File:  {run['criteria_file']}")
    else:
        print(f"  Criteria:       Default")
    print(f"  Panel Size:     {run['panel_size']}")
    print(f"  Date:           {run['created_at']}")

    if summary:
        overall = summary.get("overall_score", "N/A")
        print(f"  Overall Score:  {overall}/100")
    print()

    if not summary:
        print("  No aggregate summary available.")
        return

    # Compliance checklist
    if compliance:
        passed = sum(1 for c in compliance if c["status"] == "pass")
        total = len(compliance)
        print(f"  {'─' * 55}")
        print(f"  Guidelines Compliance ({passed}/{total} passed)")
        print(f"  {'─' * 55}")
        for check in compliance:
            status = check["status"].upper()
            icon = {"PASS": "+", "FAIL": "x", "PARTIAL": "~"}[status]
            print(f"    [{icon}] {status:<7} {check['rule']}")
            print(f"              {check['explanation']}")
        print()

    # Per-criterion breakdown
    per_criterion = summary.get("per_criterion", {})
    if per_criterion:
        print(f"  {'Criterion':<25} {'Median':>7} {'Mean':>7} {'StdDev':>7} {'Weight':>7}")
        print(f"  {'─' * 25} {'─' * 7} {'─' * 7} {'─' * 7} {'─' * 7}")

        for name, data in per_criterion.items():
            median = data.get("median_score", "N/A")
            mean = data.get("mean_score", "N/A")
            std = data.get("std_dev", "N/A")
            weight = data.get("weight", "N/A")
            label = name.replace("_", " ").title()
            print(f"  {label:<25} {median:>7} {mean:>7} {std:>7} {weight:>6}%")

        print()

    # Detailed feedback per criterion
    print(f"  {'─' * 55}")
    print(f"  Detailed Feedback")
    print(f"  {'─' * 55}")

    for name, data in per_criterion.items():
        label = name.replace("_", " ").title()
        median = data.get("median_score", "N/A")
        std = data.get("std_dev", 0)
        agreement = "High" if std < 5 else "Medium" if std < 15 else "Low"

        print(f"\n  {label} — {median}/100 (agreement: {agreement})")

        strengths = data.get("strengths", [])
        if strengths:
            print(f"    Strengths:")
            for s in strengths:
                print(f"      + {s}")

        weaknesses = data.get("weaknesses", [])
        if weaknesses:
            print(f"    Weaknesses:")
            for w in weaknesses:
                print(f"      - {w}")

        suggestions = data.get("suggestions", [])
        if suggestions:
            print(f"    Suggestions:")
            for s in suggestions:
                print(f"      > {s}")

    print()

    # Individual reviewer scores
    reviews = get_run_reviews(conn, run["id"])
    if reviews:
        print(f"  {'─' * 55}")
        print(f"  Individual Reviewer Scores")
        print(f"  {'─' * 55}")

        criterion_names = list(per_criterion.keys())
        header = f"  {'Reviewer':>10}"
        for name in criterion_names:
            label = name.replace("_", " ").title()[:12]
            header += f" {label:>12}"
        header += f" {'Overall':>10}"
        print(header)

        for review in reviews:
            scores = get_review_scores(conn, review["id"])
            score_map = {s["criterion"]: s["score"] for s in scores}
            row = f"  {'#' + str(review['reviewer_number']):>10}"
            for name in criterion_names:
                score = score_map.get(name, "N/A")
                row += f" {score:>12}"
            row += f" {review['overall_score']:>10.1f}"
            print(row)

        print()


def write_markdown_report(
    conn: Connection, output_path: Path, proposal_filename: str, proposal_id: int | None = None
) -> Path:
    """Write evaluation report as a markdown file for consumption by grant_writer."""
    run = get_latest_run(conn, proposal_id)
    if not run:
        raise RuntimeError("No evaluation runs found.")

    summary = json.loads(run["aggregate_summary"]) if run["aggregate_summary"] else None
    if not summary:
        raise RuntimeError("No aggregate summary available.")

    compliance = json.loads(run["compliance_results"]) if run.get("compliance_results") else None
    per_criterion = summary.get("per_criterion", {})
    reviews = get_run_reviews(conn, run["id"])

    lines = []
    lines.append(f"# Evaluation Report: {proposal_filename}")
    lines.append("")
    lines.append(f"**Overall Score: {summary.get('overall_score', 'N/A')}/100**")
    lines.append(f"- Panel Size: {run['panel_size']}")
    if run["criteria_file"]:
        lines.append(f"- Criteria Source: {run['criteria_file']}")
    else:
        lines.append(f"- Criteria Source: Default")
    lines.append(f"- Date: {run['created_at']}")
    lines.append("")

    # Compliance checklist (before scores — fix these first)
    if compliance:
        passed = sum(1 for c in compliance if c["status"] == "pass")
        total = len(compliance)
        lines.append(f"## Guidelines Compliance ({passed}/{total} passed)")
        lines.append("")
        lines.append("| Status | Rule | Explanation |")
        lines.append("|--------|------|-------------|")
        for check in compliance:
            status = check["status"]
            icon = {"pass": "PASS", "fail": "FAIL", "partial": "PARTIAL"}[status]
            lines.append(f"| {icon} | {check['rule']} | {check['explanation']} |")
        lines.append("")

    # Score summary table
    lines.append("## Score Summary")
    lines.append("")
    lines.append("| Criterion | Median | Mean | Std Dev | Weight |")
    lines.append("|-----------|--------|------|---------|--------|")
    for name, data in per_criterion.items():
        label = name.replace("_", " ").title()
        median = data.get("median_score", "N/A")
        mean = data.get("mean_score", "N/A")
        std = data.get("std_dev", "N/A")
        weight = data.get("weight", "N/A")
        lines.append(f"| {label} | {median} | {mean} | {std} | {weight}% |")
    lines.append("")

    # Detailed feedback per criterion
    for name, data in per_criterion.items():
        label = name.replace("_", " ").title()
        median = data.get("median_score", "N/A")
        std = data.get("std_dev", 0)
        agreement = "High" if std < 5 else "Medium" if std < 15 else "Low"

        lines.append(f"## {label} — {median}/100 (agreement: {agreement})")
        lines.append("")

        strengths = data.get("strengths", [])
        if strengths:
            lines.append("### Strengths")
            for s in strengths:
                lines.append(f"- {s}")
            lines.append("")

        weaknesses = data.get("weaknesses", [])
        if weaknesses:
            lines.append("### Weaknesses")
            for w in weaknesses:
                lines.append(f"- {w}")
            lines.append("")

        suggestions = data.get("suggestions", [])
        if suggestions:
            lines.append("### Suggestions for Improvement")
            for s in suggestions:
                lines.append(f"- {s}")
            lines.append("")

    # Individual reviewer scores
    if reviews:
        lines.append("## Individual Reviewer Scores")
        lines.append("")
        criterion_names = list(per_criterion.keys())
        header = "| Reviewer |"
        separator = "|----------|"
        for name in criterion_names:
            label = name.replace("_", " ").title()
            header += f" {label} |"
            separator += "--------|"
        header += " Overall |"
        separator += "---------|"
        lines.append(header)
        lines.append(separator)

        for review in reviews:
            scores = get_review_scores(conn, review["id"])
            score_map = {s["criterion"]: s["score"] for s in scores}
            row = f"| #{review['reviewer_number']} |"
            for name in criterion_names:
                score = score_map.get(name, "N/A")
                row += f" {score} |"
            row += f" {review['overall_score']:.1f} |"
            lines.append(row)
        lines.append("")

    output_path.write_text("\n".join(lines))
    return output_path


def print_runs_list(conn: Connection) -> None:
    """Print a summary of all evaluation runs."""
    runs = get_all_runs(conn)
    if not runs:
        print("No evaluation runs found.")
        return

    print()
    print(f"  {'ID':>4}  {'Proposal':<35} {'Score':>6}  {'Panel':>5}  {'Date'}")
    print(f"  {'─' * 4}  {'─' * 35} {'─' * 6}  {'─' * 5}  {'─' * 20}")

    for run in runs:
        score = f"{run['aggregate_score']:.1f}" if run["aggregate_score"] is not None else "N/A"
        filename = run.get("filename", f"ID:{run['proposal_id']}")[:35]
        print(
            f"  {run['id']:>4}  {filename:<35} {score:>6}  {run['panel_size']:>5}  {run['created_at']}"
        )

    print()
