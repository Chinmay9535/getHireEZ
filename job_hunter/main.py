"""
main.py
OpportunityBot — Daily Job Hunter Orchestrator
Runs every morning via GitHub Actions cron.
"""
import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from collections import Counter

# ── Setup logging ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("OpportunityBot")

# ── Path setup ───────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from job_hunter.config_loader import load_config, get_openrouter_api_key, get_gmail_app_password, get_serpapi_key, ensure_dirs
from job_hunter.deduplicator import filter_new_jobs, mark_jobs_seen, clear_old_entries
from job_hunter.ai_engine import (
    parse_resume, batch_match_jobs_against_all_profiles,
    generate_resume_tips, extract_text_from_pdf,
)
from job_hunter.excel_builder import build_excel
from job_hunter.emailer import send_report_email, send_error_alert


def gather_all_roles(config) -> list:
    """Collect all unique target roles across all resume profiles."""
    roles = set()
    for profile in config.resume_profiles:
        roles.update(profile.target_roles)
    # Fallback generic roles if none configured
    if not roles:
        roles = {"Software Engineer", "SDE", "Intern", "Graduate Engineer"}
    return list(roles)


def run_scrapers(config, roles: list, serpapi_key: str = "") -> list:
    """Run all enabled scrapers and merge results."""
    all_jobs = []
    sources  = config.enabled_sources
    locs     = config.preferences if hasattr(config, "preferences") else ["Bengaluru"]
    locations = config.locations

    # ── JobSpy (LinkedIn + Indeed + Glassdoor) ───────────────
    if any(sources.get(s) for s in ["linkedin", "indeed", "glassdoor"]):
        try:
            from job_hunter.scrapers.jobspy_scraper import scrape_jobspy
            jobs = scrape_jobspy(roles, locations, sources)
            all_jobs.extend(jobs)
            logger.info(f"[Main] JobSpy: {len(jobs)} jobs")
        except Exception as e:
            logger.warning(f"[Main] JobSpy failed: {e}")

    # ── Naukri ───────────────────────────────────────────────
    if sources.get("naukri"):
        try:
            from job_hunter.scrapers.naukri_scraper import scrape_naukri
            jobs = scrape_naukri(roles, locations)
            all_jobs.extend(jobs)
            logger.info(f"[Main] Naukri: {len(jobs)} jobs")
        except Exception as e:
            logger.warning(f"[Main] Naukri failed: {e}")

    # ── Wellfound ────────────────────────────────────────────
    if sources.get("wellfound"):
        try:
            from job_hunter.scrapers.wellfound_scraper import scrape_wellfound
            jobs = scrape_wellfound(roles)
            all_jobs.extend(jobs)
            logger.info(f"[Main] Wellfound: {len(jobs)} jobs")
        except Exception as e:
            logger.warning(f"[Main] Wellfound failed: {e}")

    # ── Internshala ──────────────────────────────────────────
    if sources.get("internshala"):
        try:
            from job_hunter.scrapers.internshala_scraper import scrape_internshala
            jobs = scrape_internshala(roles, locations)
            all_jobs.extend(jobs)
            logger.info(f"[Main] Internshala: {len(jobs)} jobs")
        except Exception as e:
            logger.warning(f"[Main] Internshala failed: {e}")

    # ── Unstop + Cutshort ────────────────────────────────────
    if sources.get("unstop"):
        try:
            from job_hunter.scrapers.unstop_scraper import scrape_unstop, scrape_cutshort
            jobs_u = scrape_unstop(roles)
            all_jobs.extend(jobs_u)
            logger.info(f"[Main] Unstop: {len(jobs_u)} jobs")
        except Exception as e:
            logger.warning(f"[Main] Unstop failed: {e}")

    if sources.get("cutshort"):
        try:
            from job_hunter.scrapers.unstop_scraper import scrape_cutshort
            jobs_c = scrape_cutshort(roles)
            all_jobs.extend(jobs_c)
            logger.info(f"[Main] Cutshort: {len(jobs_c)} jobs")
        except Exception as e:
            logger.warning(f"[Main] Cutshort failed: {e}")

    # ── YC Jobs ──────────────────────────────────────────────
    if sources.get("yc_jobs"):
        try:
            from job_hunter.scrapers.yc_scraper import scrape_yc_jobs
            jobs = scrape_yc_jobs(roles, locations)
            all_jobs.extend(jobs)
            logger.info(f"[Main] YC Jobs: {len(jobs)} jobs")
        except Exception as e:
            logger.warning(f"[Main] YC Jobs failed: {e}")

    # ── HackerNews ───────────────────────────────────────────
    if sources.get("hackernews"):
        try:
            from job_hunter.scrapers.hn_scraper import scrape_hn_hiring
            jobs = scrape_hn_hiring(roles, locations)
            all_jobs.extend(jobs)
            logger.info(f"[Main] HackerNews: {len(jobs)} jobs")
        except Exception as e:
            logger.warning(f"[Main] HackerNews failed: {e}")

    # ── SerpAPI (Google Jobs) ─────────────────────────────────
    if sources.get("serpapi"):
        try:
            from job_hunter.scrapers.serpapi_scraper import scrape_serpapi
            jobs = scrape_serpapi(roles, locations, serpapi_key)
            all_jobs.extend(jobs)
            logger.info(f"[Main] SerpAPI: {len(jobs)} jobs")
        except Exception as e:
            logger.warning(f"[Main] SerpAPI failed: {e}")

    logger.info(f"[Main] Total scraped: {len(all_jobs)} jobs")
    return all_jobs


def load_resume_profiles(config, openrouter_key: str):
    """Load and parse all resume profiles."""
    parsed_profiles = []
    for profile_cfg in config.resume_profiles:
        pdf_path = profile_cfg.pdf_path
        if not pdf_path.exists():
            logger.warning(f"[Main] Resume not found: {pdf_path}")
            continue

        logger.info(f"[Main] Parsing resume: {profile_cfg.name}")
        parsed = parse_resume(pdf_path, openrouter_key)
        if not parsed.get("error"):
            parsed_profiles.append((profile_cfg.id, profile_cfg.name, parsed))
        else:
            logger.warning(f"[Main] Could not parse resume for {profile_cfg.name}")

    return parsed_profiles


def run():
    """Main orchestration function."""
    start_time = datetime.now()
    today = start_time.strftime("%Y-%m-%d")
    today_display = start_time.strftime("%B %d, %Y")

    logger.info("=" * 60)
    logger.info("🤖 OpportunityBot starting…")
    logger.info(f"📅 Date: {today_display}")
    logger.info("=" * 60)

    # ── Load config & secrets ────────────────────────────────
    ensure_dirs()
    clear_old_entries(days=60)  # Keep DB lean

    try:
        config = load_config()
    except FileNotFoundError as e:
        logger.error(f"Config not found: {e}")
        sys.exit(1)

    try:
        openrouter_key = get_openrouter_api_key()
        gmail_pwd  = get_gmail_app_password()
        serpapi_key = get_serpapi_key()
    except EnvironmentError as e:
        logger.error(str(e))
        sys.exit(1)

    if not config.resume_profiles:
        logger.error("No resume profiles configured. Please set up in the web app first.")
        sys.exit(1)

    # ── Load resume profiles ─────────────────────────────────
    resume_profiles_data = load_resume_profiles(config, openrouter_key)
    if not resume_profiles_data:
        logger.error("No valid resumes found. Check files in resumes/ folder.")
        sys.exit(1)

    # ── Scrape ───────────────────────────────────────────────
    all_roles = gather_all_roles(config)
    logger.info(f"[Main] Target roles: {all_roles}")
    all_jobs = run_scrapers(config, all_roles, serpapi_key)

    if not all_jobs:
        logger.warning("[Main] No jobs found from any source.")
        send_error_alert(
            config.sender_email, gmail_pwd, config.recipient_email,
            "No jobs were found from any source today. Scraper may need maintenance."
        )
        return

    # ── Deduplicate ──────────────────────────────────────────
    new_jobs = filter_new_jobs(all_jobs)
    logger.info(f"[Main] After dedup: {len(new_jobs)} new jobs (of {len(all_jobs)} scraped)")

    if not new_jobs:
        logger.info("[Main] No new jobs today — all already seen. Skipping email.")
        return

    # ── AI Matching ──────────────────────────────────────────
    logger.info(f"[Main] Running AI batch matching for {len(new_jobs)} jobs…")
    
    try:
        batch_match_jobs_against_all_profiles(new_jobs, resume_profiles_data, openrouter_key)
    except Exception as e:
        logger.error(f"[Main] Batch matching failed: {e}")

    matched_jobs = []
    all_missing_skills = []

    for job in new_jobs:
        if job.get("match_percentage", 0) >= config.min_match_percent:
            matched_jobs.append(job)
            all_missing_skills.extend(job.get("missing_skills", []))

    logger.info(f"[Main] {len(matched_jobs)} jobs passed {config.min_match_percent}% threshold")

    # ── Watchlist override ───────────────────────────────────
    # Always include watchlist companies regardless of match %
    watchlist_lower = [w.lower() for w in config.watchlist_companies]
    for job in new_jobs:
        if job.get("company", "").lower() in watchlist_lower and job not in matched_jobs:
            job.setdefault("match_percentage", 0)
            job.setdefault("urgency", "LOW")
            matched_jobs.append(job)

    if not matched_jobs:
        logger.info("[Main] No jobs passed the match threshold today.")
        return

    # ── Resume tips ──────────────────────────────────────────
    tips = []
    if all_missing_skills and resume_profiles_data:
        _, _, first_resume = resume_profiles_data[0]
        tips = generate_resume_tips(all_missing_skills, first_resume, openrouter_key)

    # ── Build Excel ──────────────────────────────────────────
    report_path = PROJECT_ROOT / "data" / "reports" / f"jobs_{today}.xlsx"
    try:
        build_excel(
            jobs=matched_jobs,
            watchlist=config.watchlist_companies,
            profile_name=config.user_name or "Student",
            tips=tips,
            output_path=report_path,
        )
    except Exception as e:
        logger.error(f"[Main] Excel build failed: {e}")
        raise

    # ── Send Email ───────────────────────────────────────────
    try:
        send_report_email(
            sender_email=config.sender_email,
            app_password=gmail_pwd,
            recipient_email=config.recipient_email,
            excel_path=report_path,
            jobs=matched_jobs,
            report_date=today_display,
        )
    except Exception as e:
        logger.error(f"[Main] Email failed: {e}")
        raise

    # ── Mark jobs as seen ────────────────────────────────────
    mark_jobs_seen(matched_jobs)

    elapsed = (datetime.now() - start_time).seconds
    logger.info("=" * 60)
    logger.info(f"✅ Done! {len(matched_jobs)} jobs sent. Took {elapsed}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        # Attempt error email
        try:
            cfg = load_config()
            pwd = get_gmail_app_password()
            send_error_alert(cfg.sender_email, pwd, cfg.recipient_email, str(e))
        except Exception:
            pass
        sys.exit(1)
