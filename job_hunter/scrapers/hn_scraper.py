"""
hn_scraper.py
Fetches HackerNews "Who is Hiring?" monthly thread jobs via the official HN API.
No scraping — uses the free, official Algolia HN Search API.
"""
import re
import time
import logging
import requests
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

HN_SEARCH_API = "https://hn.algolia.com/api/v1/search"
HN_ITEM_API   = "https://hacker-news.firebaseio.com/v0/item/{}.json"


def _get_hiring_thread_id() -> int:
    """Find the latest 'Ask HN: Who is hiring?' thread ID."""
    params = {
        "query":       "Ask HN: Who is hiring?",
        "tags":        "story,ask_hn",
        "hitsPerPage": 1,
    }
    resp = requests.get(HN_SEARCH_API, params=params, timeout=10)
    hits = resp.json().get("hits", [])
    if hits:
        return int(hits[0]["objectID"])
    return 0


def _extract_company_and_location(text: str) -> tuple:
    """Try to parse 'Company | Role | Location' style HN comments."""
    parts = [p.strip() for p in text.split("|")]
    company = parts[0] if parts else ""
    location = next((p for p in parts if any(k in p.lower() for k in ["india", "bangalore", "remote", "bengaluru"])), "")
    return company, location


def _matches_role_and_location(text: str, roles: List[str], locations: List[str]) -> bool:
    text_lower = text.lower()
    role_match = any(r.lower() in text_lower for r in roles)
    loc_match = False
    for loc in locations:
        if loc.lower() in ("bengaluru", "bangalore") and ("india" in text_lower or "bangalore" in text_lower):
            loc_match = True
        if loc.lower() == "remote" and "remote" in text_lower:
            loc_match = True
    return role_match and loc_match


def scrape_hn_hiring(roles: List[str], locations: List[str]) -> List[Dict]:
    """Fetch and parse this month's HN 'Who is Hiring?' thread."""
    thread_id = _get_hiring_thread_id()
    if not thread_id:
        logger.warning("[HN] Could not find 'Who is Hiring?' thread")
        return []

    try:
        thread = requests.get(HN_ITEM_API.format(thread_id), timeout=10).json()
    except Exception as e:
        logger.warning(f"[HN] Thread fetch error: {e}")
        return []

    kids = thread.get("kids", [])[:200]  # Top 200 comments
    all_jobs: List[Dict] = []

    for kid_id in kids:
        try:
            comment = requests.get(HN_ITEM_API.format(kid_id), timeout=8).json()
            text = comment.get("text", "") or ""
            # Strip HTML tags
            text_clean = re.sub(r"<[^>]+>", " ", text).strip()

            if not _matches_role_and_location(text_clean, roles, locations):
                continue

            company, location = _extract_company_and_location(text_clean)
            # First line usually has company | role | location
            first_line = text_clean.split("\n")[0][:200]

            all_jobs.append({
                "company":      company or "HN Company",
                "title":        first_line,
                "location":     location or "See description",
                "description":  text_clean[:3000],
                "apply_url":    f"https://news.ycombinator.com/item?id={kid_id}",
                "posted_date":  str(datetime.now())[:10],
                "salary":       "",
                "company_type": "Startup",
                "company_size": "",
                "source":       "HackerNews",
                "job_type":     "",
            })
            time.sleep(0.3)
        except Exception:
            continue

    logger.info(f"[HN] {len(all_jobs)} matching jobs in 'Who is Hiring?' thread")
    return all_jobs
