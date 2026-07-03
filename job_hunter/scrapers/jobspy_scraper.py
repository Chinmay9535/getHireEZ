"""
jobspy_scraper.py
Scrapes LinkedIn, Indeed, and Glassdoor using the python-jobspy library.
Returns a normalized list of job dicts.
"""
import time
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Normalize location strings to search terms
LOCATION_MAP = {
    "Bengaluru": "Bangalore, Karnataka, India",
    "Remote":    "India",
    "Hyderabad": "Hyderabad, Telangana, India",
    "Mumbai":    "Mumbai, Maharashtra, India",
    "Pune":      "Pune, Maharashtra, India",
}


def _normalize_job(row, source: str) -> Dict:
    """Convert a JobSpy DataFrame row to our standard job dict."""
    return {
        "company":      str(row.get("company", "") or ""),
        "title":        str(row.get("title", "") or ""),
        "location":     str(row.get("location", "") or ""),
        "description":  str(row.get("description", "") or "")[:3000],  # Cap tokens
        "apply_url":    str(row.get("job_url", "") or ""),
        "posted_date":  str(row.get("date_posted", "") or ""),
        "salary":       str(row.get("min_amount", "") or "") + " - " + str(row.get("max_amount", "") or ""),
        "company_type": "MNC/Product",
        "company_size": str(row.get("company_num_employees", "") or ""),
        "source":       source,
        "job_type":     str(row.get("job_type", "") or ""),
    }


def scrape_jobspy(
    roles: List[str],
    locations: List[str],
    enabled_sources: Dict[str, bool],
    results_per_role: int = 20,
) -> List[Dict]:
    """
    Scrape LinkedIn, Indeed, Glassdoor via python-jobspy.
    roles: list of job title search terms
    locations: list of location strings from config
    """
    try:
        from jobspy import scrape_jobs
        import pandas as pd
    except ImportError:
        logger.error("python-jobspy not installed. Run: pip install python-jobspy")
        return []

    # Determine which sites to query
    site_map = {
        "linkedin":  "linkedin",
        "indeed":    "indeed",
        "glassdoor": "glassdoor",
    }
    sites = [v for k, v in site_map.items() if enabled_sources.get(k, True)]
    if not sites:
        return []

    all_jobs: List[Dict] = []

    for role in roles:
        for loc_key in locations:
            search_loc = LOCATION_MAP.get(loc_key, loc_key)
            logger.info(f"[JobSpy] Searching: '{role}' in '{search_loc}'")
            try:
                df = scrape_jobs(
                    site_name=sites,
                    search_term=role,
                    location=search_loc,
                    results_wanted=results_per_role,
                    hours_old=48,        # Only last 48 hours
                    country_indeed="India",
                )
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        job = _normalize_job(row.to_dict(), source=",".join(sites))
                        # Tag each job with its matching source
                        for site in sites:
                            if site in str(row.get("job_url", "")):
                                job["source"] = site.capitalize()
                                break
                        all_jobs.append(job)
                    logger.info(f"[JobSpy] Found {len(df)} jobs for '{role}' in '{search_loc}'")
                time.sleep(2)  # Be polite
            except Exception as e:
                logger.warning(f"[JobSpy] Failed for '{role}' in '{search_loc}': {e}")
                time.sleep(5)

    # Deduplicate within this batch
    seen_urls = set()
    unique_jobs = []
    for j in all_jobs:
        if j["apply_url"] not in seen_urls:
            seen_urls.add(j["apply_url"])
            unique_jobs.append(j)

    return unique_jobs
