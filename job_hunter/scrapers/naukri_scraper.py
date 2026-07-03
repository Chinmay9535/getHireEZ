"""
naukri_scraper.py
Scrapes job listings from Naukri.com using their public search API.
Warm-up call fetches session cookies; required headers prevent 403.
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
    "Accept":           "application/json",
    "Accept-Language":  "en-US,en;q=0.9",
    "Referer":          "https://www.naukri.com/",
    # Required by Naukri API — without these headers it returns 403
    "appid":            "109",
    "systemid":         "Naukri",
    "x-http-method-override": "GET",
    "x-requested-with": "XMLHttpRequest",
}

NAUKRI_HOMEPAGE = "https://www.naukri.com/"
NAUKRI_API      = "https://www.naukri.com/jobapi/v3/search"


def _build_params(role: str, location: str, page: int = 1) -> Dict:
    return {
        "noOfResults": 20,
        "urlType":     "search_by_keyword",
        "searchType":  "adv",
        "keyword":     role,
        "location":    location,
        "experience":  0,
        "pageNo":      page,
        "k":           role,
        "l":           location,
        "seoKey":      f"{role.replace(' ','-').lower()}-jobs",
        "src":         "jobsearchDesk",
        "latLong":     "",
    }


def _parse_job(job: Dict) -> Dict:
    return {
        "company":      job.get("companyName", ""),
        "title":        job.get("title", ""),
        "location":     ", ".join(job.get("placeholders", [{}])[0].get("label", "").split(",")[:2]),
        "description":  job.get("jobDescription", "")[:3000],
        "apply_url":    job.get("jdURL", "") or f"https://www.naukri.com{job.get('staticUrl','')}",
        "posted_date":  str(job.get("footerPlaceholderLabel", "")),
        "salary":       job.get("placeholders", [{}])[-1].get("label", "") if len(job.get("placeholders", [])) > 1 else "",
        "company_type": "IT/MNC",
        "company_size": "",
        "source":       "Naukri",
        "job_type":     "",
    }


def scrape_naukri(
    roles: List[str],
    locations: List[str],
    max_pages: int = 2,
) -> List[Dict]:
    """Scrape Naukri.com for given roles and locations."""
    all_jobs: List[Dict] = []
    session = requests.Session()
    session.headers.update(HEADERS)

    # Warm-up: hit homepage to get session cookies (required for API)
    try:
        session.get(NAUKRI_HOMEPAGE, timeout=10)
        time.sleep(1)
    except Exception:
        pass  # Continue anyway
    for role in roles:
        for location in locations:
            loc_query = "Bangalore" if location == "Bengaluru" else location
            for page in range(1, max_pages + 1):
                try:
                    resp = session.get(
                        NAUKRI_API,
                        params=_build_params(role, loc_query, page),
                        timeout=15,
                    )
                    if resp.status_code != 200:
                        logger.warning(f"[Naukri] HTTP {resp.status_code} for '{role}'")
                        break
                    data = resp.json()
                    jobs_raw = data.get("jobDetails", [])
                    if not jobs_raw:
                        break
                    for j in jobs_raw:
                        all_jobs.append(_parse_job(j))
                    logger.info(f"[Naukri] Page {page}: {len(jobs_raw)} jobs for '{role}' in '{loc_query}'")
                    time.sleep(1.5)
                except Exception as e:
                    logger.warning(f"[Naukri] Error: {e}")
                    break

    return all_jobs
