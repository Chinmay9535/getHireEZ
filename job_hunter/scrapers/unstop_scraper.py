"""
unstop_scraper.py
Scrapes Unstop (formerly Dare2Compete) for competitions, hackathons,
and fresher job drives relevant to 2027 batch in India.
"""
import time
import logging
import requests
from typing import List, Dict

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://unstop.com/",
    "Origin":  "https://unstop.com",
    "Content-Type": "application/json",  # Required by Unstop API
}

# Unstop public opportunities API
UNSTOP_API = "https://unstop.com/api/public/opportunity/search-result"


def _build_payload(role: str, page: int = 1) -> Dict:
    return {
        "filters": {
            "opportunity": ["jobs", "internships"],
            "eligible_year": [2027],
            "search": role,
        },
        "page": page,
        "size": 20,
    }


def _parse_opportunity(opp: Dict) -> Dict:
    org = opp.get("organisation", {}) or {}
    return {
        "company":      org.get("name", "") or opp.get("organisation_name", ""),
        "title":        opp.get("title", ""),
        "location":     opp.get("city", "") or "India",
        "description":  (opp.get("description", "") or "")[:3000],
        "apply_url":    f"https://unstop.com/o/{opp.get('public_url', '')}",
        "posted_date":  str(opp.get("start", ""))[:10],
        "salary":       opp.get("stipend", "") or "",
        "company_type": "Startup/MNC",
        "company_size": "",
        "source":       "Unstop",
        "job_type":     opp.get("type", ""),
    }


def scrape_unstop(roles: List[str]) -> List[Dict]:
    """Scrape Unstop jobs and internships for 2027 batch."""
    all_jobs: List[Dict] = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for role in roles:
        for page in range(1, 3):
            try:
                resp = session.post(
                    UNSTOP_API,
                    json=_build_payload(role, page),
                    timeout=15,
                )
                if resp.status_code != 200:
                    logger.warning(f"[Unstop] HTTP {resp.status_code}")
                    break

                data = resp.json().get("data", {})
                opps = data.get("data", [])
                if not opps:
                    break

                for opp in opps:
                    all_jobs.append(_parse_opportunity(opp))

                logger.info(f"[Unstop] Page {page}: {len(opps)} opportunities for '{role}'")
                time.sleep(1.5)
            except Exception as e:
                logger.warning(f"[Unstop] Error: {e}")
                break

    return all_jobs


def scrape_cutshort(roles: List[str]) -> List[Dict]:
    """
    Scrape Cutshort.io for Indian startup + GCC jobs.
    Uses their public jobs search page (their API requires auth cookies).
    """
    from bs4 import BeautifulSoup

    all_jobs: List[Dict] = []
    cs_headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://cutshort.io/",
    }

    for role in roles:
        slug = role.lower().replace(" ", "-")
        url  = f"https://cutshort.io/jobs/{slug}-jobs-in-bangalore"
        try:
            resp = requests.get(url, headers=cs_headers, timeout=15)
            if resp.status_code not in (200, 301, 302):
                logger.warning(f"[Cutshort] HTTP {resp.status_code} for '{role}'")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            # Cutshort renders job cards with schema.org markup — very reliable
            import json as _json
            ld_tags = soup.find_all("script", type="application/ld+json")
            found = 0
            for tag in ld_tags:
                try:
                    data = _json.loads(tag.string or "")
                    # Can be a list or a single object
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") != "JobPosting":
                            continue
                        org = item.get("hiringOrganization", {}) or {}
                        loc = item.get("jobLocation", {}) or {}
                        addr = loc.get("address", {}) or {}
                        salary_obj = item.get("baseSalary", {}) or {}
                        salary_val = salary_obj.get("value", {}) or {}
                        salary = f"{salary_val.get('minValue','')}-{salary_val.get('maxValue','')} LPA"
                        apply_href = item.get("url", "") or url
                        all_jobs.append({
                            "company":      org.get("name", ""),
                            "title":        item.get("title", role),
                            "location":     addr.get("addressLocality", "Bengaluru"),
                            "description":  (item.get("description", "") or "")[:3000],
                            "apply_url":    apply_href,
                            "posted_date":  str(item.get("datePosted", ""))[:10],
                            "salary":       salary,
                            "company_type": "Startup/GCC",
                            "company_size": "",
                            "source":       "Cutshort",
                            "job_type":     item.get("employmentType", ""),
                        })
                        found += 1
                except Exception:
                    continue

            logger.info(f"[Cutshort] {found} jobs for '{role}' via schema.org")
            time.sleep(2)

        except Exception as e:
            logger.warning(f"[Cutshort] Error for '{role}': {e}")

    return all_jobs
