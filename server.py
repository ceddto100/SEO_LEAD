"""
server.py — Cloud Run HTTP entry point for the SEO_LEAD platform.

Routes incoming POST requests from Cloud Scheduler to the appropriate workflow.
Each workflow is triggered via POST /run/wf01 through POST /run/wf11.

Health check: GET /
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

from flask import Flask, request, jsonify

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.config import settings
from shared.logger import get_logger

log = get_logger("server")

app = Flask(__name__)


# ── Health check ─────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "seo-lead",
        "dry_run": settings.dry_run,
    })


# ── Workflow runner ──────────────────────────────────────────────────────────

def _run_workflow(wf_id: str) -> dict:
    """
    Dynamically import and run a workflow by its ID (e.g., 'wf01').

    Returns the summary dict from the workflow's run_pipeline().
    """
    workflow_map = {
        "wf01": ("01_Keyword_Market_Research", "main"),
        "wf02": ("02_Content_Strategy_Blog_Planning", "main"),
        "wf03": ("03_AI_Blog_Writing_SEO", "main"),
        "wf04": ("04_Featured_Image_Visual_Gen", "main"),
        "wf05": ("05_Auto_Publishing_System", "main"),
        "wf06": ("06_Social_Media_Repurposing", "main"),
        "wf07": ("07_Lead_Capture_Funnel", "main"),
        "wf08": ("08_CRM_AI_FollowUp", "main"),
        "wf09": ("09_Email_Marketing_Sequences", "main"),
        "wf10": ("10_Analytics_Conversion_Tracking", "main"),
        "wf11": ("11_Performance_Feedback_Loop", "main"),
    }

    if wf_id not in workflow_map:
        raise ValueError(f"Unknown workflow: {wf_id}")

    folder, module = workflow_map[wf_id]
    wf_dir = str(PROJECT_ROOT / folder)

    # Add workflow directory to path for local imports
    if wf_dir not in sys.path:
        sys.path.insert(0, wf_dir)

    # Import the workflow's main module
    import importlib
    wf_module = importlib.import_module(f"{folder}.{module}")

    # Each workflow's main() function handles everything
    log.info("Running workflow: %s (%s)", wf_id, folder)
    wf_module.main()

    return {"workflow": wf_id, "status": "completed"}


@app.route("/run/<wf_id>", methods=["POST"])
def run_workflow(wf_id: str):
    """
    Trigger a workflow.

    POST /run/wf01  →  Run Keyword Research
    POST /run/wf02  →  Run Content Strategy
    ...etc.
    """
    log.info("=== Received trigger for %s ===", wf_id)

    try:
        result = _run_workflow(wf_id)
        log.info("=== %s completed successfully ===", wf_id)
        return jsonify(result), 200

    except ValueError as exc:
        log.error("Bad request: %s", exc)
        return jsonify({"error": str(exc)}), 400

    except Exception as exc:
        log.error("Workflow %s failed: %s", wf_id, exc)
        log.error(traceback.format_exc())
        return jsonify({
            "error": f"Workflow {wf_id} failed",
            "detail": str(exc),
        }), 500


# ── Run locally for testing ─────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    log.info("Starting SEO_LEAD server on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=True)
