"""
internshala_scraper.py
Scrapes Internshala for internship listings in India.
"""
import time
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

BASE_URL = "https://internshala.com/internships"


def _slug(role: str) -> str:
    return role.lower().replace(" ", "-").replace("/", "-")


def _parse_card(card) -> Dict:
    try:
        title = card.select_one(".job-internship-name a") or card.select_one(".profile")
        company = card.select_one(".company-name") or card.select_one(".company_name")
        location = card.select_one(".row-1-item.locations span a") or card.select_one(".location_link")
        stipend = card.select_one(".stipend") or card.select_one(".row-1-item span.stipend")
        duration = card.select_one(".item_body.duration")
        link = card.select_one(".job-title-href") or card.select_one("a.view_detail_button")
        posted = card.select_one(".status-success") or card.select_one(".status")

        url = ""
        if link and link.get("href"):
            href = link["href"]
            url = href if href.startswith("http") else f"https://internshala.com{href}"

        return {
            "company":      company.get_text(strip=True) if company else "",
            "title":        title.get_text(strip=True) if title else "",
            "location":     location.get_text(strip=True) if location else "India",
            "description":  f"Stipend: {stipend.get_text(strip=True) if stipend else 'N/A'} | Duration: {duration.get_text(strip=True) if duration else 'N/A'}",
            "apply_url":    url,
            "posted_date":  posted.get_text(strip=True) if posted else "",
            "salary":       stipend.get_text(strip=True) if stipend else "",
            "company_type": "Startup/MNC",
            "company_size": "",
            "source":       "Internshala",
            "job_type":     "Internship",
        }
    except Exception as e:
        logger.debug(f"[Internshala] Card parse error: {e}")
        return {}


def scrape_internshala(roles: List[str], locations: List[str]) -> List[Dict]:
    """Scrape Internshala listings for given roles."""
    all_jobs: List[Dict] = []
    session = requests.Session()
    session.headers.update(HEADERS)

    loc_filter = "bangalore" if any("Bengaluru" in l or "Bangalore" in l for l in locations) else ""
    include_remote = any("Remote" in l for l in locations)

    for role in roles:
        urls_to_try = []
        if loc_filter:
            urls_to_try.append(f"{BASE_URL}/{_slug(role)}-internship-in-{loc_filter}")
        if include_remote:
            urls_to_try.append(f"{BASE_URL}/work-from-home-{_slug(role)}-internship")
        if not urls_to_try:
            urls_to_try.append(f"{BASE_URL}/{_slug(role)}-internship")

        for url in urls_to_try:
            try:
                resp = session.get(url, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"[Internshala] HTTP {resp.status_code} for {url}")
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select(".internship_meta") or soup.select(".individual_internship")

                for card in cards:
                    job = _parse_card(card)
                    if job.get("title"):
                        all_jobs.append(job)

                logger.info(f"[Internshala] {len(cards)} internships found at {url}")
                time.sleep(2)
            except Exception as e:
                logger.warning(f"[Internshala] Error: {e}")

    return all_jobs
