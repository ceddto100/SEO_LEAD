"""
02_Content_Strategy_Blog_Planning/outline_generator.py

Step 4 from workflow.txt -- AI Blog Outline Generation.
For each content plan item, generates a detailed blog outline with:
  - H2/H3 heading structure
  - CTA placements
  - FAQ section for featured snippets
  - Internal link placement notes
"""

from __future__ import annotations

from typing import Any

from shared.ai_client import ask_ai_json
from shared.logger import get_logger

log = get_logger("outline_generator")

# ---------------------------------------------------------------------------
# Outline prompt
# ---------------------------------------------------------------------------

OUTLINE_SYSTEM_PROMPT = """\
You are an expert blog content architect.

Create a detailed blog outline for the given article.

Requirements:
- H1: The title
- H2s: 5-8 main sections
- H3s: 2-3 subsections under each H2
- Include a "Key Takeaways" section
- Include an FAQ section with 5 questions (optimised for featured snippets)
- Specify where to place internal links
- Specify where to place CTAs (lead magnets, email signup)
- Note any statistics or data points to research and include

Return ONLY valid JSON:
{
  "title": "...",
  "slug": "...",
  "outline": [
    {
      "h2": "Section Title",
      "h3s": ["Sub 1", "Sub 2"],
      "notes": "Include stat about X",
      "cta_placement": false,
      "internal_link_note": ""
    }
  ],
  "faq": [
    {"question": "...", "answer_brief": "2-3 sentence answer"}
  ]
}
"""


def generate_outline(plan_item: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a detailed blog outline for a single content plan item.
    """
    from shared.config import settings

    keyword = plan_item.get("keyword", "unknown")
    title = plan_item.get("title", keyword)
    content_type = plan_item.get("content_type", "blog post")
    word_count = plan_item.get("word_count", 2000)

    log.info("Generating outline for: '%s'", title)

    # In dry-run mode, return a deterministic mock
    if settings.dry_run:
        log.info("[DRY-RUN] Generating mock outline for '%s'", title)
        slug = keyword.lower().replace(" ", "-")
        return {
            "title": title,
            "slug": slug,
            "outline": [
                {"h2": "Introduction", "h3s": ["What You'll Learn", "Why It Matters"],
                 "notes": "Hook the reader with a compelling stat", "cta_placement": False,
                 "internal_link_note": ""},
                {"h2": f"Understanding {keyword.title()}", "h3s": ["Definition", "Key Concepts"],
                 "notes": "Define core terms", "cta_placement": False,
                 "internal_link_note": "Link to related pillar content"},
                {"h2": "Best Practices", "h3s": ["Strategy 1", "Strategy 2", "Strategy 3"],
                 "notes": "Include actionable tips", "cta_placement": True,
                 "internal_link_note": ""},
                {"h2": "Tools and Resources", "h3s": ["Top Tools", "Free Resources"],
                 "notes": "Comparison table", "cta_placement": False,
                 "internal_link_note": ""},
                {"h2": "Case Studies", "h3s": ["Example 1", "Example 2"],
                 "notes": "Real-world examples with metrics", "cta_placement": False,
                 "internal_link_note": ""},
                {"h2": "Key Takeaways", "h3s": [],
                 "notes": "Bullet-point summary", "cta_placement": True,
                 "internal_link_note": ""},
            ],
            "faq": [
                {"question": f"What is {keyword}?", "answer_brief": f"A brief explanation of {keyword}."},
                {"question": f"How do I get started with {keyword}?", "answer_brief": "Start by..."},
                {"question": f"What are the best tools for {keyword}?", "answer_brief": "Top tools include..."},
                {"question": f"How much does {keyword} cost?", "answer_brief": "Costs vary depending on..."},
                {"question": f"Is {keyword} worth it in 2026?", "answer_brief": "Yes, because..."},
            ],
        }

    user_prompt = (
        f"Title: {title}\n"
        f"Primary Keyword: {keyword}\n"
        f"Content Type: {content_type}\n"
        f"Word Count Target: {word_count}\n"
    )

    result = ask_ai_json(OUTLINE_SYSTEM_PROMPT, user_prompt)

    # Ensure slug exists
    if isinstance(result, dict):
        if "slug" not in result:
            result["slug"] = keyword.lower().replace(" ", "-")
        if "title" not in result:
            result["title"] = title
    else:
        result = {"title": title, "slug": keyword.lower().replace(" ", "-"),
                  "outline": result if isinstance(result, list) else [],
                  "faq": []}

    sections = result.get("outline", [])
    faqs = result.get("faq", [])
    log.info(
        "Outline for '%s': %d sections, %d FAQs",
        title, len(sections), len(faqs),
    )

    return result


def generate_all_outlines(
    content_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Generate outlines for every item in the content plan.
    """
    log.info("Generating outlines for %d content items", len(content_plan))
    outlines = []
    for item in content_plan:
        outline = generate_outline(item)
        outlines.append(outline)
    log.info("Completed %d outlines", len(outlines))
    return outlines


def format_outline_text(outline: dict[str, Any]) -> str:
    """
    Convert a structured outline dict into readable markdown text
    (for saving to Google Docs or Sheets).
    """
    lines = []
    title = outline.get("title", "Untitled")
    lines.append(f"# {title}\n")

    for section in outline.get("outline", []):
        h2 = section.get("h2", "Section")
        lines.append(f"\n## {h2}\n")

        for h3 in section.get("h3s", []):
            lines.append(f"### {h3}\n")

        notes = section.get("notes", "")
        if notes:
            lines.append(f"_Notes: {notes}_\n")

        if section.get("cta_placement"):
            lines.append("[CTA PLACEMENT]\n")

        link_note = section.get("internal_link_note", "")
        if link_note:
            lines.append(f"_Internal Link: {link_note}_\n")

    # FAQ section
    faqs = outline.get("faq", [])
    if faqs:
        lines.append("\n## Frequently Asked Questions\n")
        for faq in faqs:
            q = faq.get("question", "")
            a = faq.get("answer_brief", "")
            lines.append(f"**Q: {q}**\n{a}\n")

    return "\n".join(lines)
