from pathlib import Path

import click

from grant_evaluator.config import EvaluatorConfig
from grant_evaluator.db import init_evaluation_db


@click.group()
@click.pass_context
def cli(ctx):
    """Grant Evaluator — score proposals using a panel of AI reviewers."""
    ctx.ensure_object(dict)
    config = EvaluatorConfig.load()
    conn = init_evaluation_db(config.db_path)
    ctx.obj["config"] = config
    ctx.obj["conn"] = conn


def _resolve_proposal(conn, proposal_name: str) -> dict:
    """Look up a proposal by filename (with or without .pdf extension)."""
    from grant_researcher.db import get_proposals

    proposals = get_proposals(conn)
    if not proposals:
        raise click.ClickException(
            "No proposals in database. Run 'grant-researcher ingest' first."
        )

    # Try exact match, then with .pdf appended
    candidates = [proposal_name]
    if not proposal_name.endswith(".pdf"):
        candidates.append(proposal_name + ".pdf")

    for candidate in candidates:
        for p in proposals:
            if p["filename"] == candidate:
                return p

    available = ", ".join(p["filename"] for p in proposals)
    raise click.ClickException(
        f"Proposal '{proposal_name}' not found (looked for file and folder names). "
        f"Available: {available}"
    )


def _resolve_criteria(config, criteria_name: str | None):
    """Load criteria file and extract rubric, or return defaults."""
    from grant_evaluator.criteria import extract_rubric, extract_text

    if criteria_name is None:
        return None, None, config.default_criteria

    criteria_path = config.criteria_path / criteria_name
    if not criteria_path.exists():
        raise click.ClickException(f"Criteria file not found: {criteria_path}")

    click.echo(f"Extracting text from {criteria_name}...")
    criteria_text = extract_text(criteria_path)

    click.echo("Extracting scoring rubric from criteria document...")
    rubric = extract_rubric(criteria_text, config.anthropic_api_key, config.model)

    if rubric:
        click.echo(f"Extracted {len(rubric)} criteria from rubric:")
        for c in rubric:
            click.echo(f"  - {c.name} ({c.weight}%): {c.description}")
        return criteria_name, criteria_text, rubric
    else:
        click.echo("No rubric found in document, using default criteria.")
        return criteria_name, criteria_text, config.default_criteria


def _load_guidelines(config, guidelines_names: tuple[str, ...]) -> str | None:
    """Load one or more guidelines files, concatenate their text."""
    if not guidelines_names:
        return None

    from grant_evaluator.criteria import extract_text

    parts = []
    for name in guidelines_names:
        path = config.criteria_path / name
        if not path.exists():
            raise click.ClickException(f"Guidelines file not found: {path}")
        click.echo(f"Loading guidelines from {name}...")
        parts.append(extract_text(path))

    return "\n\n".join(parts)


@cli.command()
@click.option("--proposal", required=True, help="Proposal filename or folder name (in proposals/)")
@click.option("--criteria", default=None, help="RFP/criteria filename (in criteria/)")
@click.option("--guidelines", multiple=True, help="Rules/guidelines file(s) (in criteria/), repeatable")
@click.pass_context
def evaluate(ctx, proposal: str, criteria: str | None, guidelines: tuple[str, ...]):
    """Evaluate a proposal using a panel of AI reviewers."""
    from grant_evaluator.aggregator import aggregate_reviews
    from grant_evaluator.criteria import extract_rubric
    from grant_evaluator.db import create_run, update_run_aggregate, update_run_compliance
    from grant_evaluator.evaluators import run_compliance_check, run_panel

    config = ctx.obj["config"]
    conn = ctx.obj["conn"]

    # Resolve proposal
    prop = _resolve_proposal(conn, proposal)
    click.echo(f"Evaluating: {prop['filename']}")

    # Load guidelines
    guidelines_text = _load_guidelines(config, guidelines)

    # Resolve criteria:
    # 1. --criteria provided → extract rubric from that file
    # 2. --guidelines only → extract rubric from guidelines
    # 3. Neither → default criteria
    if criteria:
        criteria_file, criteria_text, criteria_list = _resolve_criteria(config, criteria)
    elif guidelines_text:
        click.echo("Extracting scoring rubric from guidelines...")
        rubric = extract_rubric(guidelines_text, config.anthropic_api_key, config.model)
        if rubric:
            click.echo(f"Extracted {len(rubric)} criteria from guidelines:")
            for c in rubric:
                click.echo(f"  - {c.name} ({c.weight}%): {c.description}")
            criteria_list = rubric
        else:
            click.echo("No rubric found in guidelines, using default criteria.")
            criteria_list = config.default_criteria
        criteria_file = None
        criteria_text = None
    else:
        criteria_file, criteria_text, criteria_list = None, None, config.default_criteria

    if not criteria_list:
        raise click.ClickException("No evaluation criteria available.")

    click.echo(f"\nUsing {len(criteria_list)} criteria, panel of {config.panel_size} reviewers")
    if guidelines_text:
        click.echo(f"Guidelines loaded ({len(guidelines_text)} chars)")
    click.echo(f"Model: {config.model}, Temperature: {config.temperature}\n")

    # Create evaluation run
    rubric_dicts = [{"name": c.name, "description": c.description, "weight": c.weight} for c in criteria_list]
    run_id = create_run(
        conn, prop["id"], criteria_file, criteria_text, rubric_dicts, config.panel_size
    )

    # Phase 1: Guidelines compliance check
    if guidelines_text:
        click.echo("Phase 1: Guidelines compliance check...")
        compliance_results = run_compliance_check(
            prop["text"], guidelines_text, config, on_progress=click.echo
        )
        update_run_compliance(conn, run_id, compliance_results)
        passed = sum(1 for c in compliance_results if c["status"] == "pass")
        total = len(compliance_results)
        click.echo(f"  {passed}/{total} checks passed\n")
    else:
        compliance_results = None

    # Phase 2: Rubric evaluation
    phase = "Phase 2: " if guidelines_text else ""
    click.echo(f"{phase}Running reviewer panel...")
    reviews = run_panel(
        conn, run_id, prop["text"], criteria_list, criteria_text, config,
        on_progress=click.echo,
    )

    # Aggregate
    click.echo("\nAggregating scores...")
    summary = aggregate_reviews(reviews, criteria_list)

    update_run_aggregate(conn, run_id, summary["overall_score"], summary)

    click.echo(f"Overall score: {summary['overall_score']}/100")

    # Write markdown report
    from grant_evaluator.report import write_markdown_report

    stem = Path(prop["filename"]).stem
    report_path = config.project_dir / "evaluations" / f"{stem}_evaluation.md"
    report_path.parent.mkdir(exist_ok=True)
    write_markdown_report(conn, report_path, prop["filename"], prop["id"])
    click.echo(f"Report saved to {report_path}")

    click.echo(f"\nRun #{run_id} complete. Use 'report' to see detailed results.")


@cli.command()
@click.option("--proposal", default=None, help="Show report for specific proposal filename")
@click.pass_context
def report(ctx, proposal: str | None):
    """Show the latest evaluation report."""
    from grant_evaluator.report import print_report, print_runs_list

    conn = ctx.obj["conn"]

    if proposal:
        prop = _resolve_proposal(conn, proposal)
        print_report(conn, prop["id"])
    else:
        print_runs_list(conn)
        print_report(conn)


@cli.command()
@click.option("--proposal", required=True, help="Proposal filename or folder name (in proposals/)")
@click.option("--criteria", default=None, help="RFP/criteria filename (in criteria/)")
@click.option("--guidelines", multiple=True, help="Rules/guidelines file(s) (in criteria/), repeatable")
@click.pass_context
def run(ctx, proposal: str, criteria: str | None, guidelines: tuple[str, ...]):
    """Run the full pipeline: evaluate + report."""
    ctx.invoke(evaluate, proposal=proposal, criteria=criteria, guidelines=guidelines)
    ctx.invoke(report, proposal=proposal)
