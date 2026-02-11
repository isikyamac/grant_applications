import json
import queue
import sqlite3
import threading
from dataclasses import replace
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from grant_evaluator.config import EvaluatorConfig
from grant_evaluator.db import (
    create_run,
    get_all_runs,
    get_latest_run,
    get_review_scores,
    get_run_reviews,
    init_evaluation_db,
    update_run_aggregate,
    update_run_compliance,
)

app = Flask(__name__, template_folder=Path(__file__).parent / "templates")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


def _get_config() -> EvaluatorConfig:
    return EvaluatorConfig.load()


def _get_conn(db_path: Path) -> sqlite3.Connection:
    """Create a fresh connection with both researcher and evaluator tables."""
    from grant_researcher.db import init_db

    init_db(db_path)
    conn = init_evaluation_db(db_path)
    return conn


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    config = _get_config()
    conn = _get_conn(config.db_path)
    from grant_researcher.db import get_proposals

    proposals = get_proposals(conn)
    criteria_files = []
    if config.criteria_path.exists():
        criteria_files = sorted(p.name for p in config.criteria_path.iterdir() if p.is_file())
    runs = get_all_runs(conn)
    conn.close()
    return render_template(
        "index.html",
        proposals=proposals,
        criteria_files=criteria_files,
        runs=runs,
        config=config,
    )


@app.route("/upload", methods=["POST"])
def upload():
    config = _get_config()
    conn = _get_conn(config.db_path)

    proposal_name = request.form.get("proposal_name", "").strip()
    proposal_files = request.files.getlist("proposal_files")
    criteria_file = request.files.get("criteria_file")
    guidelines_files = request.files.getlist("guidelines_files")

    proposals_dir = config.project_dir / "proposals"
    proposals_dir.mkdir(exist_ok=True)

    # Save proposal files
    uploaded_proposal = None
    valid_proposals = [f for f in proposal_files if f.filename]
    if len(valid_proposals) == 1:
        f = valid_proposals[0]
        f.save(str(proposals_dir / f.filename))
        uploaded_proposal = f.filename
    elif len(valid_proposals) > 1:
        if not proposal_name:
            proposal_name = Path(valid_proposals[0].filename).stem
        subfolder = proposals_dir / proposal_name
        subfolder.mkdir(exist_ok=True)
        for f in valid_proposals:
            f.save(str(subfolder / f.filename))
        uploaded_proposal = proposal_name

    # Save criteria / guidelines to criteria dir
    criteria_dir = config.criteria_path
    criteria_dir.mkdir(exist_ok=True)

    uploaded_criteria = None
    if criteria_file and criteria_file.filename:
        criteria_file.save(str(criteria_dir / criteria_file.filename))
        uploaded_criteria = criteria_file.filename

    uploaded_guidelines = []
    for gf in guidelines_files:
        if gf.filename:
            gf.save(str(criteria_dir / gf.filename))
            uploaded_guidelines.append(gf.filename)

    # Ingest proposals into DB
    from grant_researcher.proposals import ingest_proposals

    ingested = ingest_proposals(proposals_dir, conn)
    conn.close()

    return jsonify(
        {
            "proposal": uploaded_proposal,
            "criteria": uploaded_criteria,
            "guidelines": uploaded_guidelines,
            "ingested": ingested,
        }
    )


@app.route("/evaluate")
def evaluate():
    config = _get_config()

    proposal_name = request.args.get("proposal", "")
    criteria_name = request.args.get("criteria") or None
    guidelines_csv = request.args.get("guidelines", "")
    guidelines_names = [g.strip() for g in guidelines_csv.split(",") if g.strip()]

    # Override config with user-provided values
    config = replace(
        config,
        panel_size=int(request.args.get("panel_size", config.panel_size)),
        temperature=float(request.args.get("temperature", config.temperature)),
        model=request.args.get("model", config.model),
    )

    progress_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
    result_holder: dict = {}

    def progress_cb(msg):
        progress_queue.put(("progress", msg))

    def run_evaluation():
        try:
            from grant_evaluator.aggregator import aggregate_reviews
            from grant_evaluator.criteria import extract_rubric, extract_text
            from grant_evaluator.evaluators import run_compliance_check, run_panel
            from grant_evaluator.report import write_markdown_report
            from grant_researcher.db import get_proposals

            conn = _get_conn(config.db_path)

            # Resolve proposal
            proposals = get_proposals(conn)
            prop = None
            candidates = [proposal_name]
            if not proposal_name.endswith(".pdf"):
                candidates.append(proposal_name + ".pdf")
            for c in candidates:
                for p in proposals:
                    if p["filename"] == c:
                        prop = p
                        break
                if prop:
                    break
            if not prop:
                raise ValueError(f"Proposal '{proposal_name}' not found in database.")

            progress_cb(f"Evaluating: {prop['filename']}")

            # Load guidelines
            guidelines_text = None
            if guidelines_names:
                parts = []
                for name in guidelines_names:
                    path = config.criteria_path / name
                    if not path.exists():
                        raise ValueError(f"Guidelines file not found: {path}")
                    progress_cb(f"Loading guidelines from {name}...")
                    parts.append(extract_text(path))
                guidelines_text = "\n\n".join(parts)

            # Resolve criteria
            criteria_file = None
            criteria_text = None
            criteria_list = config.default_criteria

            if criteria_name:
                criteria_path = config.criteria_path / criteria_name
                if not criteria_path.exists():
                    raise ValueError(f"Criteria file not found: {criteria_path}")
                progress_cb(f"Extracting text from {criteria_name}...")
                criteria_text = extract_text(criteria_path)
                progress_cb("Extracting scoring rubric...")
                rubric = extract_rubric(criteria_text, config.anthropic_api_key, config.model)
                if rubric:
                    progress_cb(f"Extracted {len(rubric)} criteria from rubric")
                    criteria_list = rubric
                    criteria_file = criteria_name
                else:
                    progress_cb("No rubric found, using default criteria.")
            elif guidelines_text:
                progress_cb("Extracting scoring rubric from guidelines...")
                rubric = extract_rubric(guidelines_text, config.anthropic_api_key, config.model)
                if rubric:
                    progress_cb(f"Extracted {len(rubric)} criteria from guidelines")
                    criteria_list = rubric
                else:
                    progress_cb("No rubric found in guidelines, using default criteria.")

            progress_cb(f"Using {len(criteria_list)} criteria, panel of {config.panel_size}")
            progress_cb(f"Model: {config.model}, Temperature: {config.temperature}")

            rubric_dicts = [
                {"name": c.name, "description": c.description, "weight": c.weight}
                for c in criteria_list
            ]
            run_id = create_run(
                conn, prop["id"], criteria_file, criteria_text, rubric_dicts, config.panel_size
            )

            # Phase 1: Compliance
            if guidelines_text:
                progress_cb("Phase 1: Guidelines compliance check...")
                compliance_results = run_compliance_check(
                    prop["text"], guidelines_text, config, on_progress=progress_cb
                )
                update_run_compliance(conn, run_id, compliance_results)
                passed = sum(1 for c in compliance_results if c["status"] == "pass")
                progress_cb(f"Compliance: {passed}/{len(compliance_results)} checks passed")

            # Phase 2: Panel review
            phase = "Phase 2: " if guidelines_text else ""
            progress_cb(f"{phase}Running reviewer panel...")
            reviews = run_panel(
                conn, run_id, prop["text"], criteria_list, criteria_text, config,
                on_progress=progress_cb,
            )

            progress_cb("Aggregating scores...")
            summary = aggregate_reviews(reviews, criteria_list)
            update_run_aggregate(conn, run_id, summary["overall_score"], summary)
            progress_cb(f"Overall score: {summary['overall_score']}/100")

            # Write markdown report
            stem = Path(prop["filename"]).stem
            report_path = config.project_dir / "evaluations" / f"{stem}_evaluation.md"
            report_path.parent.mkdir(exist_ok=True)
            write_markdown_report(conn, report_path, prop["filename"], prop["id"])
            progress_cb(f"Report saved to {report_path.name}")

            # Build result data for frontend
            run = get_latest_run(conn, prop["id"])
            run_reviews = get_run_reviews(conn, run["id"])
            review_data = []
            for rev in run_reviews:
                scores = get_review_scores(conn, rev["id"])
                review_data.append(
                    {
                        "reviewer_number": rev["reviewer_number"],
                        "overall_score": rev["overall_score"],
                        "scores": [
                            {
                                "criterion": s["criterion"],
                                "score": s["score"],
                                "strengths": json.loads(s["strengths"]) if s["strengths"] else [],
                                "weaknesses": json.loads(s["weaknesses"]) if s["weaknesses"] else [],
                                "suggestions": json.loads(s["suggestions"]) if s["suggestions"] else [],
                            }
                            for s in scores
                        ],
                    }
                )

            compliance = None
            if run.get("compliance_results") and run["compliance_results"]:
                compliance = json.loads(run["compliance_results"])

            result_holder["data"] = {
                "run_id": run["id"],
                "overall_score": summary["overall_score"],
                "summary": summary,
                "compliance": compliance,
                "reviews": review_data,
                "report_file": report_path.name,
            }
            conn.close()
        except Exception as e:
            result_holder["error"] = str(e)
        finally:
            progress_queue.put(("done", None))

    def generate():
        thread = threading.Thread(target=run_evaluation, daemon=True)
        thread.start()
        while True:
            event_type, data = progress_queue.get()
            if event_type == "done":
                if result_holder.get("error"):
                    yield f"event: error\ndata: {json.dumps({'error': result_holder['error']})}\n\n"
                else:
                    yield f"event: result\ndata: {json.dumps(result_holder['data'])}\n\n"
                break
            else:
                yield f"event: progress\ndata: {json.dumps({'message': data})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/run/<int:run_id>")
def get_run(run_id):
    config = _get_config()
    conn = _get_conn(config.db_path)
    row = conn.execute("SELECT * FROM evaluation_runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Run not found"}), 404

    run = dict(row)
    summary = json.loads(run["aggregate_summary"]) if run.get("aggregate_summary") else None
    compliance = json.loads(run["compliance_results"]) if run.get("compliance_results") and run["compliance_results"] else None

    run_reviews = get_run_reviews(conn, run_id)
    review_data = []
    for rev in run_reviews:
        scores = get_review_scores(conn, rev["id"])
        review_data.append(
            {
                "reviewer_number": rev["reviewer_number"],
                "overall_score": rev["overall_score"],
                "scores": [
                    {
                        "criterion": s["criterion"],
                        "score": s["score"],
                        "strengths": json.loads(s["strengths"]) if s["strengths"] else [],
                        "weaknesses": json.loads(s["weaknesses"]) if s["weaknesses"] else [],
                        "suggestions": json.loads(s["suggestions"]) if s["suggestions"] else [],
                    }
                    for s in scores
                ],
            }
        )

    conn.close()
    return jsonify(
        {
            "run_id": run["id"],
            "overall_score": run.get("aggregate_score"),
            "summary": summary,
            "compliance": compliance,
            "reviews": review_data,
        }
    )


def main():
    app.run(debug=True, host="127.0.0.1", port=5000, threaded=True)


if __name__ == "__main__":
    main()
