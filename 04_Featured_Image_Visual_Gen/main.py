"""
04_Featured_Image_Visual_Gen/main.py

Orchestrator for Workflow 04: Featured Image & Visual Generation.
Reads PublishQueue for articles needing images, generates AI prompts,
creates images via DALL-E 3, and updates Sheets.
"""
from __future__ import annotations
import argparse, json, sys, time
from datetime import datetime
from pathlib import Path
from typing import Any

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
_wf_dir = str(Path(__file__).resolve().parent)
if _wf_dir not in sys.path:
    sys.path.insert(0, _wf_dir)

from shared.config import settings
from shared.logger import get_logger
from shared.notifier import send_notification
from shared.google_sheets import SheetsClient
from image_prompt_generator import generate_image_prompts
from image_creator import generate_all_images

log = get_logger("workflow_04")

IMAGE_LIBRARY_HEADERS = ["Article Title", "Image URL", "Alt Text", "File Name", "Date"]

def run_pipeline(articles: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.time()
    log.info("=" * 70)
    log.info("WORKFLOW 04: FEATURED IMAGE & VISUAL GENERATION")
    log.info("=" * 70)
    log.info("Articles needing images: %d", len(articles))

    output_dir = Path(__file__).resolve().parent / "output" / "images"
    results = []

    for i, article in enumerate(articles, 1):
        title = article.get("Title", "Untitled")
        keyword = article.get("Keyword", "")
        content_type = article.get("Type", "blog post")
        log.info("IMAGE %d/%d: %s", i, len(articles), title)

        # Step 1: Generate prompts
        prompts = generate_image_prompts(title, keyword, content_type)

        # Step 2: Generate images
        urls = generate_all_images(prompts, output_dir)

        # Step 3: Save to ImageLibrary sheet
        sheets = SheetsClient()
        sheets.append_rows("ImageLibrary", [{
            "Article Title": title, "Image URL": urls["featured_url"],
            "Alt Text": prompts["alt_text"], "File Name": prompts["file_name"],
            "Date": datetime.now().strftime("%Y-%m-%d"),
        }], headers=IMAGE_LIBRARY_HEADERS)

        results.append({"title": title, "featured_url": urls["featured_url"],
                        "social_url": urls["social_url"], "alt_text": prompts["alt_text"]})

    elapsed = round(time.time() - start, 1)
    send_notification(subject=f"Images Generated -- {len(results)} articles",
                      body=f"Generated images for {len(results)} articles in {elapsed}s")
    summary = {"images_generated": len(results), "elapsed_seconds": elapsed,
               "timestamp": datetime.now().isoformat()}
    log.info("WORKFLOW 04 COMPLETE: %d images in %ss", len(results), elapsed)
    _save_snapshot(summary, results)
    return summary

def _save_snapshot(summary, results):
    out = Path(__file__).resolve().parent / "output"
    out.mkdir(exist_ok=True)
    (out / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, default=str))

def _read_articles_needing_images(limit=5):
    if settings.dry_run:
        return [{"Title": "Lead Generation Guide", "Keyword": "lead generation", "Type": "guide"},
                {"Title": "Best CRM Tools 2026", "Keyword": "best crm tools", "Type": "listicle"}][:limit]
    sheets = SheetsClient()
    rows = sheets.read_rows("PublishQueue")
    return [r for r in rows if r.get("Image Needed", "").lower() == "yes"
            and not r.get("Featured Image URL")][:limit]

def main():
    parser = argparse.ArgumentParser(description="Workflow 04: Image Generation")
    parser.add_argument("--dry-run", "-d", action="store_true")
    parser.add_argument("--limit", "-l", type=int, default=5)
    args = parser.parse_args()
    if args.dry_run and not settings.dry_run:
        object.__setattr__(settings, "dry_run", True)
    articles = _read_articles_needing_images(args.limit)
    if not articles:
        print("No articles need images."); return
    summary = run_pipeline(articles)
    print(f"\n[OK] Workflow 04 complete! {summary['images_generated']} images generated.")

if __name__ == "__main__":
    main()
