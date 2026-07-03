"""
yc_scraper.py
Scrapes Y Combinator's Work at a Startup job board.
Uses their official jobs JSON endpoint.
"""
import time
import logging
import requests
from typing import List, Dict

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OpportunityBot/1.0)",
    "Accept": "application/json",
}

YC_JOBS_API = "https://www.workatastartup.com/jobs.json"


def _matches_role(job: Dict, roles: List[str]) -> bool:
    title = (job.get("title", "") or "").lower()
    return any(r.lower() in title or any(word in title for word in r.lower().split()) for r in roles)


def _matches_location(job: Dict, locations: List[str]) -> bool:
    job_locs = " ".join(job.get("locations", [])).lower()
    loc_tags = " ".join(job.get("location_tag", [])).lower()
    combined = job_locs + " " + loc_tags

    for loc in locations:
        if loc.lower() in ("bengaluru", "bangalore") and (
            "india" in combined or "bangalore" in combined or "bengaluru" in combined
        ):
            return True
        if loc.lower() == "remote" and ("remote" in combined or "anywhere" in combined):
            return True
    return False


def _parse_job(job: Dict, company: Dict) -> Dict:
    locations = job.get("locations", [])
    return {
        "company":      company.get("name", ""),
        "title":        job.get("title", ""),
        "location":     ", ".join(locations) if locations else "Remote/India",
        "description":  (job.get("description", "") or "")[:3000],
        "apply_url":    job.get("url", "") or f"https://www.workatastartup.com/jobs/{job.get('id','')}",
        "posted_date":  str(job.get("created_at", ""))[:10],
        "salary":       f"${job.get('min_experience',0)}-{job.get('equity_min','')} equity" if job.get("equity_min") else "",
        "company_type": "YC Startup",
        "company_size": str(company.get("team_size", "") or ""),
        "source":       "YC Jobs",
        "job_type":     job.get("employment_type", ""),
    }


def scrape_yc_jobs(roles: List[str], locations: List[str]) -> List[Dict]:
    """Fetch all YC startup jobs and filter by role + location."""
    try:
        resp = requests.get(YC_JOBS_API, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            logger.warning(f"[YC Jobs] HTTP {resp.status_code}")
            return []

        data = resp.json()
    except Exception as e:
        logger.warning(f"[YC Jobs] Fetch error: {e}")
        return []

    all_jobs: List[Dict] = []
    companies_by_id: Dict[int, Dict] = {c["id"]: c for c in data.get("companies", [])}

    for job in data.get("jobs", []):
        if not _matches_role(job, roles):
            continue
        company = companies_by_id.get(job.get("company_id", -1), {})
        parsed = _parse_job(job, company)
        all_jobs.append(parsed)

    logger.info(f"[YC Jobs] {len(all_jobs)} matching jobs found")
    return all_jobs
