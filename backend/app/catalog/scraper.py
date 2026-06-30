from __future__ import annotations

"""Offline catalog scraper for the SHL product catalog.

Usage:
    python -m app.catalog.scraper --out data/shl_catalog.json

Uses Playwright (headless Chromium) to render the JS-driven catalog pages,
then BeautifulSoup to extract structured fields. Never invoked at request
time — this is a one-shot build step.
"""

import argparse
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _parse_row(row) -> dict | None:
    name_el = row.select_one("a")
    if not name_el:
        return None
    name = name_el.get_text(strip=True)
    href = name_el.get("href", "")
    cells = [c.get_text(" ", strip=True) for c in row.select("td")]
    remote = any("remote" in c.lower() and "yes" in c.lower() for c in cells)
    adaptive = any("adaptive" in c.lower() and "yes" in c.lower() for c in cells)
    dur = 0
    for c in cells:
        m = re.search(r"(\d+)\s*min", c, flags=re.IGNORECASE)
        if m:
            dur = int(m.group(1))
            break
    return {
        "id": _slug(name),
        "name": name,
        "url": href if href.startswith("http") else f"https://www.shl.com{href}",
        "description": name,
        "category": cells[-1] if cells else "",
        "duration_minutes": dur,
        "remote": remote,
        "adaptive": adaptive,
        "job_levels": [],
        "languages": ["English"],
        "skills": [],
    }


def scrape(out: Path) -> int:
    from playwright.sync_api import sync_playwright

    items: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(CATALOG_URL, wait_until="networkidle", timeout=60_000)
        # Iterate through pagination if present.
        seen_pages = 0
        while True:
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            for row in soup.select("table tr"):
                rec = _parse_row(row)
                if rec and rec["name"]:
                    items.append(rec)
            seen_pages += 1
            next_btn = page.query_selector("a[rel='next'], a:has-text('Next')")
            if not next_btn or seen_pages > 50:
                break
            try:
                next_btn.click()
                page.wait_for_load_state("networkidle", timeout=30_000)
            except Exception:
                break
        browser.close()

    # De-dupe by id.
    by_id: dict[str, dict] = {}
    for it in items:
        by_id.setdefault(it["id"], it)
    final = list(by_id.values())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(final)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/shl_catalog.json")
    args = ap.parse_args()
    n = scrape(Path(args.out))
    print(f"Wrote {n} assessments to {args.out}")


if __name__ == "__main__":
    main()
