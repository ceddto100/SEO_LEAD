"""
03_AI_Blog_Writing_SEO/article_writer.py

Step 3 from workflow.txt -- AI Article Writing.
Takes a blog outline and writes a full-length, SEO-optimized HTML article.
"""

from __future__ import annotations

from typing import Any

from shared.config import settings
from shared.ai_client import ask_ai
from shared.logger import get_logger

log = get_logger("article_writer")

# ---------------------------------------------------------------------------
# Writing prompt
# ---------------------------------------------------------------------------

WRITER_SYSTEM_PROMPT = """\
You are an expert SEO blog writer with 10 years of experience.
Write a complete, high-quality blog article following the outline provided.

WRITING RULES:
1. Use the primary keyword in: H1 title, first 100 words, 2-3 H2s,
   meta description, last paragraph
2. Keyword density: 1-2% (natural, never forced)
3. Use related LSI keywords throughout (synonyms, related terms)
4. Write in a conversational, authoritative tone
5. Short paragraphs (2-3 sentences max)
6. Use bullet points and numbered lists where appropriate
7. Include a compelling introduction with a hook
8. Include a "Key Takeaways" box at the top
9. Include a FAQ section with schema-ready Q&A format
10. Include CTA placements: one mid-article, one at the end
11. Add placeholder markers for internal links: [INTERNAL_LINK: anchor text -> slug]
12. Add placeholder markers for images: [IMAGE: description of image needed]
13. End with a strong conclusion and call to action

FORMAT: Return as HTML with proper heading tags (h1, h2, h3), paragraph tags,
list tags, and bold/italic for emphasis. Do NOT include <html>, <head>, or
<body> tags. Just the article content HTML.
"""


def write_article(
    title: str,
    keyword: str,
    word_count: int,
    content_type: str,
    outline_text: str,
    audit_feedback: str | None = None,
) -> str:
    """
    Generate a full HTML blog article from an outline.

    If audit_feedback is provided, it means a previous draft scored below
    threshold and needs improvement based on the feedback.
    """
    log.info("Writing article: '%s' (~%d words)", title, word_count)

    if settings.dry_run:
        log.info("[DRY-RUN] Generating mock article for '%s'", title)
        return _mock_article(title, keyword, word_count)

    user_prompt = (
        f"TITLE: {title}\n"
        f"PRIMARY KEYWORD: {keyword}\n"
        f"TARGET WORD COUNT: {word_count}\n"
        f"CONTENT TYPE: {content_type}\n\n"
        f"OUTLINE:\n{outline_text}\n"
    )

    if audit_feedback:
        user_prompt += (
            f"\n\nPREVIOUS AUDIT FEEDBACK (improve these areas):\n"
            f"{audit_feedback}\n"
        )

    article_html = ask_ai(WRITER_SYSTEM_PROMPT, user_prompt)

    # Basic word count check
    word_count_actual = len(article_html.split())
    log.info(
        "Article generated: %d words (target: %d)",
        word_count_actual, word_count,
    )

    return article_html


# ---------------------------------------------------------------------------
# Mock article for dry-run
# ---------------------------------------------------------------------------

def _mock_article(title: str, keyword: str, word_count: int) -> str:
    """Return a realistic mock HTML article for dry-run testing."""
    return f"""<article>

<h1>{title}</h1>

<div class="key-takeaways">
<h2>Key Takeaways</h2>
<ul>
<li>Understanding {keyword} is essential for modern businesses</li>
<li>Implementing the right strategy can increase leads by 300%</li>
<li>The best tools and practices are covered in this guide</li>
</ul>
</div>

<p>In today's competitive digital landscape, <strong>{keyword}</strong> has become
one of the most critical strategies for business growth. Whether you're a startup
or an established enterprise, mastering {keyword} can transform your results.</p>

[IMAGE: Hero image showing {keyword} concept visualization]

<h2>What is {keyword.title()}?</h2>
<p>{keyword.title()} refers to the systematic process of attracting and converting
prospects into potential customers. It forms the foundation of any successful
marketing strategy.</p>

<h2>Why {keyword.title()} Matters in 2026</h2>
<p>The landscape has evolved dramatically. Here's why it matters now more than ever:</p>
<ul>
<li><strong>Increased competition</strong> -- standing out requires a strategic approach</li>
<li><strong>Changing buyer behavior</strong> -- customers research extensively before purchasing</li>
<li><strong>Technology advances</strong> -- AI and automation have changed the game</li>
</ul>

[INTERNAL_LINK: learn more about digital marketing strategies -> digital-marketing-strategies]

<h2>Best Practices for {keyword.title()}</h2>
<p>Here are the proven strategies that deliver results:</p>
<ol>
<li><strong>Content Marketing</strong> -- Create valuable content that attracts your target audience</li>
<li><strong>SEO Optimization</strong> -- Ensure your content ranks for relevant search terms</li>
<li><strong>Social Proof</strong> -- Leverage testimonials and case studies</li>
</ol>

<div class="cta-box">
<h3>Ready to Get Started?</h3>
<p>Download our free {keyword} toolkit and start generating results today.</p>
</div>

[IMAGE: Infographic showing {keyword} best practices]

<h2>Tools and Resources</h2>
<p>The right tools make all the difference. Here are our top recommendations:</p>
<ul>
<li><strong>Tool A</strong> -- Best for small businesses</li>
<li><strong>Tool B</strong> -- Best for enterprise teams</li>
<li><strong>Tool C</strong> -- Best free option</li>
</ul>

<h2>Case Studies</h2>
<p>Real businesses achieving real results with {keyword}:</p>
<p><strong>Company X</strong> increased their conversion rate by 250% after implementing
a comprehensive {keyword} strategy over 6 months.</p>

<h2>Frequently Asked Questions</h2>

<div class="faq-item" itemscope itemtype="https://schema.org/Question">
<h3 itemprop="name">What is {keyword}?</h3>
<div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">
<p itemprop="text">{keyword.title()} is the process of identifying and cultivating
potential customers for your business products or services.</p>
</div>
</div>

<div class="faq-item" itemscope itemtype="https://schema.org/Question">
<h3 itemprop="name">How much does {keyword} cost?</h3>
<div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">
<p itemprop="text">Costs vary widely depending on your approach. Organic strategies
can start free, while paid approaches range from $500-$10,000/month.</p>
</div>
</div>

<div class="faq-item" itemscope itemtype="https://schema.org/Question">
<h3 itemprop="name">What are the best {keyword} tools?</h3>
<div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">
<p itemprop="text">Popular tools include HubSpot, Salesforce, and various
marketing automation platforms designed for {keyword}.</p>
</div>
</div>

<h2>Conclusion</h2>
<p><strong>{keyword.title()}</strong> remains one of the most effective ways to grow
your business in 2026. By implementing the strategies outlined in this guide,
you can build a sustainable pipeline of qualified prospects.</p>

<div class="cta-box">
<h3>Take the Next Step</h3>
<p>Ready to transform your {keyword} results? Contact our team for a free
consultation and personalized strategy session.</p>
</div>

</article>"""
