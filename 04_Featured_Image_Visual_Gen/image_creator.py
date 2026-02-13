"""
04_Featured_Image_Visual_Gen/image_creator.py

Steps 3-4 -- Generate images via DALL-E 3 API and download them.
"""
from __future__ import annotations
import requests
from pathlib import Path
from typing import Any
from shared.config import settings
from shared.logger import get_logger

log = get_logger("image_creator")

DALLE_URL = "https://api.openai.com/v1/images/generations"

def generate_image(prompt: str, size: str = "1792x1024") -> str:
    """Call DALL-E 3 API. Returns the image URL."""
    log.info("Generating image (%s): %.80s...", size, prompt)
    if settings.dry_run:
        log.info("[DRY-RUN] Skipping DALL-E API call")
        return f"https://placeholder.example.com/image_{size.replace('x','_')}.png"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {"model": "dall-e-3", "prompt": prompt, "n": 1, "size": size,
            "quality": "standard", "response_format": "url"}
    resp = requests.post(DALLE_URL, json=body, headers=headers, timeout=120)
    resp.raise_for_status()
    return resp.json()["data"][0]["url"]

def download_image(url: str, dest_path: Path) -> Path:
    """Download an image from URL to local path."""
    if settings.dry_run:
        log.info("[DRY-RUN] Would download %s -> %s", url, dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text("(dry-run placeholder)")
        return dest_path
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(resp.content)
    log.info("Downloaded image to %s (%d bytes)", dest_path, len(resp.content))
    return dest_path

def generate_all_images(prompts: dict[str, Any], output_dir: Path) -> dict[str, str]:
    """Generate featured + social images, return URLs."""
    urls = {}
    urls["featured_url"] = generate_image(prompts["featured_prompt"], "1792x1024")
    urls["social_url"] = generate_image(prompts["social_prompt"], "1024x1024")

    # Download locally
    slug = prompts.get("file_name", "image").replace(".png", "")
    download_image(urls["featured_url"], output_dir / f"{slug}-featured.png")
    download_image(urls["social_url"], output_dir / f"{slug}-social.png")
    return urls
