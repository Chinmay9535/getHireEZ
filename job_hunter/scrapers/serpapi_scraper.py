"""
serpapi_scraper.py
Scrapes Google Jobs using SerpAPI to bypass anti-bot protections.
"""
import time
import logging
import requests
from typing import List, Dict

logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


def _parse_job(job: Dict) -> Dict:
    """Parse SerpAPI job format into our standard OpportunityBot format."""
    apply_url = ""
    # Try to find the apply link
    related_links = job.get("related_links", [])
    if related_links:
        apply_url = related_links[0].get("link", "")
    
    # Fallback apply url if related_links is empty
    if not apply_url:
        apply_url = job.get("share_link", "")

    return {
        "company":      job.get("company_name", ""),
        "title":        job.get("title", ""),
        "location":     job.get("location", ""),
        "description":  (job.get("description", "") or "")[:3000],
        "apply_url":    apply_url,
        "posted_date":  job.get("detected_extensions", {}).get("posted_at", ""),
        "salary":       job.get("detected_extensions", {}).get("salary", ""),
        "company_type": "MNC/Startup",
        "company_size": "",
        "source":       f"Google Jobs ({job.get('via', 'Web')})",
        "job_type":     job.get("detected_extensions", {}).get("schedule_type", ""),
    }


def scrape_serpapi(roles: List[str], locations: List[str], api_key: str) -> List[Dict]:
    """Scrape jobs via SerpAPI's Google Jobs engine."""
    all_jobs: List[Dict] = []
    
    if not api_key:
        logger.warning("[SerpAPI] No API key found. Skipping.")
        return all_jobs

    for role in roles:
        for location in locations:
            query = f"{role} in {location}"
            
            params = {
                "engine": "google_jobs",
                "q": query,
                "hl": "en",
                "api_key": api_key,
                "start": 0
            }
            
            # Fetch up to 2 pages (10 jobs per page on Google Jobs SerpAPI)
            for page in range(2):
                params["start"] = page * 10
                try:
                    resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=45)
                    if resp.status_code != 200:
                        logger.warning(f"[SerpAPI] HTTP {resp.status_code}: {resp.text}")
                        break
                        
                    data = resp.json()
                    jobs_results = data.get("jobs_results", [])
                    
                    if not jobs_results:
                        break
                        
                    for job in jobs_results:
                        all_jobs.append(_parse_job(job))
                        
                    logger.info(f"[SerpAPI] Found {len(jobs_results)} jobs for '{query}' (Page {page+1})")
                    time.sleep(1)  # small delay
                except Exception as e:
                    logger.warning(f"[SerpAPI] Error scraping '{query}': {e}")
                    break
                    
    return all_jobs
