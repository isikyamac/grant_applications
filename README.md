# Grant Researcher & Evaluator

A Python tool that searches for government grants, scores their relevance using Claude, and evaluates proposal drafts with simulated reviewer panels.

## How It Works

1. **Ingest** — extracts text from your company's proposal PDFs for context
2. **Search** — queries multiple grant sources using configurable keywords:
   - **Grants.gov** — federal grant opportunities
   - **SBIR.gov** — Small Business Innovation Research solicitations
   - **TRB RIP** — Transportation Research Board research projects (RSS)
   - **EU Funding & Tenders** — Horizon Europe, SESAR JU, Clean Aviation JU calls (RSS)
   - **TED** — EU public procurement tenders (API)
   - **SAM.gov** — federal contract opportunities (requires API key)
3. **Match** — scores grants against your company profile using a two-pass approach:
   - *Pass 1 (Haiku)*: batches of 10 grants are triaged quickly to filter out irrelevant ones
   - *Pass 2 (Sonnet)*: promising candidates get individually scored from 0–100 with reasoning
4. **Report** — prints a ranked table of results to the terminal

## Setup

```bash
python3 -m pip install -e .
```

Create a `.env` file with your API keys:

```
ANTHROPIC_API_KEY=sk-...
SAM_API_KEY=...          # optional, for SAM.gov
```

Edit `config.yaml` with your company profile and search keywords.

## Usage

Run the full pipeline:

```bash
python3 -c "from grant_researcher.cli import cli; cli()" -- run
```

Or run individual steps:

```bash
python3 -c "from grant_researcher.cli import cli; cli()" -- ingest    # parse proposal PDFs
python3 -c "from grant_researcher.cli import cli; cli()" -- search    # fetch grants from all sources
python3 -c "from grant_researcher.cli import cli; cli()" -- match     # score grants with Claude
python3 -c "from grant_researcher.cli import cli; cli()" -- report    # print ranked results
```

## Grant Evaluator

Score proposal drafts using a panel of AI reviewers. Available as both a CLI and a web UI.

### Web UI

```bash
grant-evaluator-web
```

Opens a browser-based interface at http://127.0.0.1:5000 where you can:

- Upload proposal PDFs (single or multi-part), criteria/RFP documents, and guidelines
- Configure panel size, temperature, and model
- Run evaluations with live progress streaming
- View inline evaluation reports with scores, compliance checks, and detailed feedback
- Browse past evaluation runs

### CLI

```bash
python3 -c "from grant_evaluator.cli import cli; cli()" -- evaluate --proposal <filename.pdf> [--criteria <rfp.pdf>] [--guidelines <rules.pdf>]
python3 -c "from grant_evaluator.cli import cli; cli()" -- report [--proposal <filename.pdf>]
python3 -c "from grant_evaluator.cli import cli; cli()" -- run --proposal <filename.pdf> [--criteria <rfp.pdf>] [--guidelines <rules.pdf>]
```

## Configuration

**config.yaml:**

```yaml
company:
  name: Your Company
  description: What your company does
  focus_areas:
    - area 1
    - area 2
  eligibility:
    - Small business
search:
  keywords:
    - keyword 1
    - keyword 2
```

Place proposal PDFs in the `proposals/` directory for additional matching context. For multi-part proposals, create a subfolder (e.g. `proposals/my-grant/PartA.pdf`, `proposals/my-grant/PartB.pdf`).

Place RFP/criteria and guidelines PDFs in the `criteria/` directory for evaluation rubric extraction.
