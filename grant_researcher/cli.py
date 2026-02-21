import click

from grant_researcher.config import Config
from grant_researcher.db import init_db, grant_count, purge_expired_grants


@click.group()
@click.pass_context
def cli(ctx):
    """Grant Researcher — find and match government grants for your company."""
    ctx.ensure_object(dict)
    config = Config.load()
    conn = init_db(config.db_path)
    ctx.obj["config"] = config
    ctx.obj["conn"] = conn


@cli.command()
@click.pass_context
def ingest(ctx):
    """Parse PDFs from proposals/ into the database."""
    from grant_researcher.proposals import ingest_proposals

    config = ctx.obj["config"]
    conn = ctx.obj["conn"]

    click.echo(f"Scanning {config.proposals_dir} for PDFs and proposal folders...")
    ingested = ingest_proposals(config.proposals_dir, conn)

    if ingested:
        click.echo(f"Ingested {len(ingested)} proposal(s): {', '.join(ingested)}")
    else:
        click.echo("No new or updated proposals found.")


@cli.command()
@click.pass_context
def search(ctx):
    """Fetch grants from Grants.gov, SBIR.gov, TRB RIP, EU Funding & Tenders, TED, Google, and SAM.gov."""
    from grant_researcher.sources.grants_gov import search_grants as search_grants_gov
    from grant_researcher.sources.sbir_gov import search_grants as search_sbir
    from grant_researcher.sources.trb_rip import search_grants as search_trb
    from grant_researcher.sources.eu_funding import search_grants as search_eu
    from grant_researcher.sources.ted_eu import search_grants as search_ted
    from grant_researcher.sources.google_search import search_grants as search_google
    from grant_researcher.sources.sam_gov import search_grants as search_sam

    config = ctx.obj["config"]
    conn = ctx.obj["conn"]

    expired = purge_expired_grants(conn)
    if expired:
        click.echo(f"Purged {expired} expired grant(s).")

    keywords = config.search.keywords
    before = grant_count(conn)

    click.echo(f"Searching Grants.gov with {len(keywords)} keyword(s)...")
    try:
        search_grants_gov(keywords, conn)
    except Exception as e:
        click.echo(f"Grants.gov failed: {e}", err=True)

    click.echo(f"Searching SBIR.gov with {len(keywords)} keyword(s)...")
    try:
        search_sbir(keywords, conn)
    except Exception as e:
        click.echo(f"SBIR.gov failed: {e}", err=True)

    click.echo(f"Searching TRB RIP with {len(keywords)} keyword(s)...")
    try:
        search_trb(keywords, conn)
    except Exception as e:
        click.echo(f"TRB RIP failed: {e}", err=True)

    click.echo("Searching EU Funding & Tenders Portal...")
    try:
        search_eu(keywords, conn)
    except Exception as e:
        click.echo(f"EU Funding & Tenders failed: {e}", err=True)

    click.echo("Searching TED (Tenders Electronic Daily)...")
    try:
        search_ted(keywords, conn)
    except Exception as e:
        click.echo(f"TED failed: {e}", err=True)

    if config.google_api_key and config.google_cse_id:
        click.echo(f"Searching Google with {len(keywords)} keyword(s)...")
        try:
            search_google(keywords, conn, config.google_api_key, config.google_cse_id)
        except Exception as e:
            click.echo(f"Google Search failed: {e}", err=True)
    else:
        click.echo("Skipping Google Search (GOOGLE_API_KEY or GOOGLE_CSE_ID not set).")

    if config.sam_api_key:
        click.echo(f"Searching SAM.gov with {len(keywords)} keyword(s)...")
        try:
            search_sam(keywords, conn, config.sam_api_key)
        except Exception as e:
            click.echo(f"SAM.gov failed: {e}", err=True)
    else:
        click.echo("Skipping SAM.gov (SAM_API_KEY not set).")

    after = grant_count(conn)
    click.echo(f"Done. {after - before} new grant(s) added ({after} total in DB).")


@cli.command()
@click.pass_context
def match(ctx):
    """Score unmatched grants using Claude (requires ANTHROPIC_API_KEY)."""
    from grant_researcher.matcher import match_grants

    config = ctx.obj["config"]
    conn = ctx.obj["conn"]

    try:
        scored = match_grants(config, conn, on_progress=click.echo)
    except RuntimeError as e:
        raise click.ClickException(str(e))

    if not scored:
        click.echo("No unscored grants to process.")


@cli.command()
@click.pass_context
def report(ctx):
    """Print ranked results to the terminal."""
    from grant_researcher.report import print_report

    conn = ctx.obj["conn"]
    print_report(conn)


@cli.command()
@click.pass_context
def run(ctx):
    """Run the full pipeline: ingest → search → match → report."""
    ctx.invoke(ingest)
    ctx.invoke(search)
    ctx.invoke(match)
    ctx.invoke(report)
