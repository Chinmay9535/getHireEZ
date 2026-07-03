"""
wellfound_scraper.py
Scrapes Wellfound (AngelList) for startup jobs in India.

Strategy (most reliable first):
  1. Wellfound public Algolia search API — used by their own site, no auth needed
  2. Fallback: scrape public job listings page with BeautifulSoup
"""
import time
import logging
import requests
from typing import List, Dict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://wellfound.com/",
}

# Wellfound uses Algolia search internally — publicly accessible
ALGOLIA_APP_ID  = "U7PKVKF0VB"  # Wellfound's public Algolia app
ALGOLIA_API_KEY = "5f4fc0b4c89b7e552e10b4a4a0571754"  # Public search-only key
ALGOLIA_INDEX   = "Job_production"
ALGOLIA_URL     = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

ALGOLIA_HEADERS = {
    **HEADERS,
    "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    "X-Algolia-API-Key":        ALGOLIA_API_KEY,
}


def _algolia_search(role: str, page: int = 0) -> List[Dict]:
    """Query Wellfound via Algolia. Returns raw hit list."""
    payload = {
        "query":              role,
        "page":               page,
        "hitsPerPage":        20,
        "filters":            "country:India OR remote:true",
        "attributesToRetrieve": [
            "title", "startup_name", "locations", "description",
            "slug", "remote", "salary_range", "created_at",
            "startup_id", "startup_size",
        ],
    }
    try:
        resp = requests.post(ALGOLIA_URL, json=payload, headers=ALGOLIA_HEADERS, timeout=12)
        if resp.status_code == 200:
            return resp.json().get("hits", [])
        logger.warning(f"[Wellfound/Algolia] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[Wellfound/Algolia] Error: {e}")
    return []


def _parse_hit(hit: Dict) -> Dict:
    """Convert an Algolia hit to our standard job dict."""
    slug = hit.get("slug", "")
    apply_url = f"https://wellfound.com/jobs/{slug}" if slug else "https://wellfound.com/jobs"
    locs = hit.get("locations", [])
    return {
        "company":      hit.get("startup_name", ""),
        "title":        hit.get("title", ""),
        "location":     "Remote" if hit.get("remote") else (", ".join(locs) if locs else "India"),
        "description":  (hit.get("description", "") or "")[:3000],
        "apply_url":    apply_url,
        "posted_date":  str(hit.get("created_at", ""))[:10],
        "salary":       hit.get("salary_range", "") or "",
        "company_type": "Startup",
        "company_size": str(hit.get("startup_size", "") or ""),
        "source":       "Wellfound",
        "job_type":     "Remote" if hit.get("remote") else "On-site",
    }


def _fallback_html_scrape(role: str) -> List[Dict]:
    """Fallback: scrape Wellfound's public jobs page."""
    jobs = []
    url = f"https://wellfound.com/role/l/{role.lower().replace(' ', '-')}/india"
    try:
        resp = requests.get(url, headers={**HEADERS, "Accept": "text/html"}, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("[data-test='StartupResult']") or soup.select(".job-listing")
        for card in cards[:15]:
            title_el   = card.select_one("a[data-test='job-title']") or card.select_one("h2 a")
            company_el = card.select_one("[data-test='company-name']") or card.select_one("h3")
            href = title_el["href"] if title_el and title_el.get("href") else ""
            jobs.append({
                "company":      company_el.get_text(strip=True) if company_el else "",
                "title":        title_el.get_text(strip=True) if title_el else role,
                "location":     "India",
                "description":  "",
                "apply_url":    f"https://wellfound.com{href}" if href else "https://wellfound.com/jobs",
                "posted_date":  "",
                "salary":       "",
                "company_type": "Startup",
                "company_size": "",
                "source":       "Wellfound",
                "job_type":     "",
            })
    except Exception as e:
        logger.warning(f"[Wellfound/HTML] Fallback error: {e}")
    return jobs


def scrape_wellfound(roles: List[str], max_pages: int = 3) -> List[Dict]:
    """
    Scrape Wellfound for startup jobs matching given roles.
    Uses Algolia (primary) → HTML fallback.
    """
    all_jobs: List[Dict] = []

    for role in roles:
        # Try Algolia first
        algolia_success = False
        for page in range(max_pages):
            hits = _algolia_search(role, page)
            if not hits:
                break
            algolia_success = True
            for hit in hits:
                all_jobs.append(_parse_hit(hit))
            logger.info(f"[Wellfound/Algolia] Page {page}: {len(hits)} jobs for '{role}'")
            time.sleep(1.5)

        # Fallback if Algolia returned nothing
        if not algolia_success:
            logger.info(f"[Wellfound] Algolia empty, trying HTML fallback for '{role}'")
            fallback = _fallback_html_scrape(role)
            all_jobs.extend(fallback)
            time.sleep(2)

    return all_jobs
