# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grant Researcher & Evaluator — a Python CLI tool that searches government grant databases, scores their relevance using Claude AI, and evaluates proposal drafts with simulated reviewer panels.

## Commands

```bash
# Install (editable)
python3 -m pip install -e .

# Grant Researcher — find and rank grants
grant-researcher run                # full pipeline: ingest → search → match → report
grant-researcher ingest             # parse proposal PDFs from proposals/
grant-researcher search             # fetch grants from all sources
grant-researcher match              # score grants with Claude (two-pass: Haiku triage → Sonnet scoring)
grant-researcher report             # print ranked results

# Grant Evaluator — score a proposal draft
python3 -c "from grant_evaluator.cli import cli; cli()" -- evaluate --proposal <filename.pdf> [--criteria <rfp.pdf>] [--guidelines <rules.pdf>]
python3 -c "from grant_evaluator.cli import cli; cli()" -- report [--proposal <filename.pdf>]
python3 -c "from grant_evaluator.cli import cli; cli()" -- run --proposal <filename.pdf> [--criteria <rfp.pdf>] [--guidelines <rules.pdf>]
```

Only `grant_researcher` has a `[project.scripts]` entry in pyproject.toml. The `grant_evaluator` CLI must be invoked via `python3 -c` as shown above (it is not registered as a console script).

## Architecture

Two independent packages sharing a single SQLite database (`grants.db`) and `config.yaml`:

### grant_researcher — Grant Discovery
- **cli.py**: Click CLI with commands: `ingest`, `search`, `match`, `report`, `run`
- **config.py**: `Config` dataclass loaded from `config.yaml` + `.env`. Resolves `project_dir` relative to the package location (`Path(__file__).resolve().parent.parent`)
- **db.py**: SQLite schema (`grants`, `proposals` tables), all DB access functions. Uses `UNIQUE(source, external_id)` for deduplication via upsert
- **matcher.py**: Two-pass Claude scoring. Pass 1: Haiku batches of 10 for triage. Pass 2: Sonnet individual scoring (0-100) with three dimensions (domain relevance, technology match, eligibility fit)
- **proposals.py**: PDF text extraction via PyMuPDF, hash-based change detection
- **sources/**: Each source module exports `search_grants(keywords, conn, ...)` → calls external API/RSS → normalizes to common grant dict → `upsert_grant()`
  - `grants_gov.py` — REST API (POST)
  - `sbir_gov.py` — SBIR solicitations
  - `trb_rip.py` — RSS feed
  - `eu_funding.py` — RSS feed (Horizon Europe, SESAR JU, Clean Aviation JU)
  - `ted_eu.py` — TED API
  - `sam_gov.py` — REST API (requires SAM_API_KEY)

### grant_evaluator — Proposal Evaluation
- **cli.py**: Click CLI with commands: `evaluate`, `report`, `run`. Depends on `grant_researcher.db` for proposal data
- **config.py**: `EvaluatorConfig` dataclass with panel_size, temperature, model, default_criteria. Loaded from `evaluator:` section in `config.yaml`
- **db.py**: SQLite schema (`evaluation_runs`, `evaluation_reviews`, `review_scores` tables). Shares the same `grants.db` file
- **criteria.py**: PDF text extraction + Claude-based rubric extraction from RFP documents. Returns `list[CriterionConfig]`
- **evaluators.py**: Runs a panel of N independent Claude reviewers, each scoring all criteria. Also runs guidelines compliance checks. Returns structured JSON scores
- **aggregator.py**: Computes median/mean/stddev across reviewers per criterion, deduplicates feedback, produces weighted overall score
- **report.py**: Terminal + markdown report generation. Markdown reports saved to `evaluations/`

### Key Data Flow
- Both modules resolve `project_dir` as `Path(__file__).parent.parent` (the repo root)
- Config is loaded from `config.yaml` at project root; API keys from `.env`
- `grant_evaluator` cross-imports `grant_researcher.db.get_proposals` to access ingested proposal text
- All Claude API calls use the `anthropic` SDK directly (no wrapper)

## Configuration

- `config.yaml`: Company profile, search keywords, and evaluator settings (panel_size, temperature, model, default_criteria with weights)
- `.env`: `ANTHROPIC_API_KEY` (required), `SAM_API_KEY` (optional)
- `proposals/`: Place proposal PDFs here for context during matching and evaluation
- `criteria/`: Place RFP/solicitation PDFs here for evaluation criteria extraction
