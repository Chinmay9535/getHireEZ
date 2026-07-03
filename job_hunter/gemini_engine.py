"""
gemini_engine.py
Core AI engine powering resume parsing and job-resume alignment scoring.
Uses Google Gemini 1.5 Flash 8B (super lite, fast, free tier).
"""
import json
import time
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Client initialisation (lazy, to avoid import-time errors)
# ─────────────────────────────────────────────────────────────────

_client = None

def _get_client(api_key: str):
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=api_key)
    return _client


def _safe_generate(client, prompt: str, retries: int = 5) -> str:
    """Call Gemini with exponential backoff on rate-limit errors."""
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt
            )
            # Free tier allows 15 RPM (1 request every 4 seconds)
            time.sleep(4.1) 
            return response.text or ""
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                wait = (2 ** attempt) * 10  # 10s, 20s, 40s, 80s
                logger.warning(f"[Gemini] Rate limit (15 RPM). Waiting {wait}s…")
                time.sleep(wait)
            else:
                logger.error(f"[Gemini] Error: {e}")
                return ""
    return ""


def _extract_json(text: str) -> Dict:
    """Extract the first JSON object found in Gemini's response."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find JSON block inside markdown code fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find any {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


# ─────────────────────────────────────────────────────────────────
# PDF → Text
# ─────────────────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract plain text from a PDF resume using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        pages = [page.get_text("text") for page in doc]
        doc.close()
        return "\n".join(pages)
    except ImportError:
        logger.error("PyMuPDF not installed. Run: pip install PyMuPDF")
        return ""
    except Exception as e:
        logger.error(f"PDF read error for {pdf_path}: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────
# Resume Parsing
# ─────────────────────────────────────────────────────────────────

RESUME_PARSE_PROMPT = """
You are an expert resume parser. Analyse the resume text below and return ONLY a valid JSON object 
(no markdown, no explanation) with this exact schema:

{{
  "name": "string",
  "branch": "string (e.g. CSE, ECE, IT, Mechanical)",
  "graduation_year": "number (e.g. 2027)",
  "college": "string",
  "technical_skills": ["list", "of", "skills"],
  "soft_skills": ["list"],
  "languages": ["Python", "Java", ...],
  "frameworks": ["React", "TensorFlow", ...],
  "tools": ["Git", "Docker", ...],
  "domains": ["Machine Learning", "Web Dev", ...],
  "certifications": ["list"],
  "projects": ["brief project descriptions"],
  "internships": ["brief internship descriptions"],
  "cgpa": "string or null",
  "summary": "3-line professional summary of this candidate"
}}

Resume text:
{resume_text}
"""


def parse_resume(pdf_path: Path, api_key: str) -> Dict:
    """
    Parse a PDF resume and return structured JSON profile.
    Also returns the raw text for later use in matching.
    """
    resume_text = extract_text_from_pdf(pdf_path)
    if not resume_text.strip():
        return {"error": "Could not extract text from PDF"}

    client = _get_client(api_key)
    prompt = RESUME_PARSE_PROMPT.format(resume_text=resume_text[:6000])  # Cap to 6k chars

    raw = _safe_generate(client, prompt)
    parsed = _extract_json(raw)

    if not parsed:
        logger.warning("[Gemini] Resume parse returned no JSON, using fallback")
        parsed = {"technical_skills": [], "summary": ""}

    parsed["_raw_text"] = resume_text  # Store raw text for matching
    return parsed


# ─────────────────────────────────────────────────────────────────
# Job–Resume Matching
# ─────────────────────────────────────────────────────────────────

JOB_MATCH_PROMPT = """
You are a professional talent acquisition expert. Evaluate how well this candidate's resume 
matches the job description and return ONLY a valid JSON object (no markdown, no extra text).

JSON schema:
{{
  "match_percentage": <integer 0-100>,
  "matched_skills": ["skills from resume that match the job"],
  "missing_skills": ["important skills from job not found in resume"],
  "why_good_fit": "1-2 sentence explanation of why this is/isn't a good fit",
  "urgency": "HIGH | MEDIUM | LOW",
  "recommended_action": "Apply immediately | Apply this week | Optional | Skip",
  "job_tags": ["MNC" | "Startup" | "Product" | "BFSI" | "Remote" | "Internship"]
}}

Scoring guide:
- 80-100: Strong match, apply immediately
- 60-79:  Good match, definitely apply
- 40-59:  Partial match, worth applying
- 20-39:  Weak match, skill gap exists
- 0-19:   Poor match

Candidate profile:
- Skills: {skills}
- Branch: {branch}
- Projects/Experience: {projects}
- Summary: {summary}

Job:
- Title: {title}
- Company: {company}
- Description: {description}
"""


def calculate_match(
    job: Dict,
    resume_profile: Dict,
    api_key: str,
) -> Dict:
    """
    Score a single job against a single resume profile.
    Returns match result dict.
    """
    client = _get_client(api_key)

    all_skills = (
        resume_profile.get("technical_skills", []) +
        resume_profile.get("languages", []) +
        resume_profile.get("frameworks", []) +
        resume_profile.get("tools", [])
    )

    prompt = JOB_MATCH_PROMPT.format(
        skills=", ".join(all_skills[:40]),
        branch=resume_profile.get("branch", ""),
        projects="; ".join((resume_profile.get("projects", []) + resume_profile.get("internships", []))[:5]),
        summary=resume_profile.get("summary", "")[:400],
        title=job.get("title", ""),
        company=job.get("company", ""),
        description=job.get("description", "")[:2000],
    )

    raw = _safe_generate(client, prompt)
    result = _extract_json(raw)

    if not result or "match_percentage" not in result:
        # Fallback: simple keyword scoring
        result = _fallback_keyword_score(job, resume_profile)

    return result


def _fallback_keyword_score(job: Dict, resume_profile: Dict) -> Dict:
    """Simple keyword overlap score when Gemini fails."""
    all_skills = set(s.lower() for s in (
        resume_profile.get("technical_skills", []) +
        resume_profile.get("languages", []) +
        resume_profile.get("frameworks", []) +
        resume_profile.get("tools", [])
    ))
    desc_lower = (job.get("description", "") + " " + job.get("title", "")).lower()
    matched = [s for s in all_skills if s in desc_lower]
    pct = min(int((len(matched) / max(len(all_skills), 1)) * 100), 100)
    return {
        "match_percentage": pct,
        "matched_skills": matched[:10],
        "missing_skills": [],
        "why_good_fit": "Keyword-based match (AI scoring unavailable)",
        "urgency": "MEDIUM" if pct >= 60 else "LOW",
        "recommended_action": "Apply this week" if pct >= 60 else "Optional",
        "job_tags": [],
    }


# ─────────────────────────────────────────────────────────────────
# Multi-Resume Matching
# ─────────────────────────────────────────────────────────────────

def match_job_against_all_profiles(
    job: Dict,
    resume_profiles_data: List[Tuple[str, str, Dict]],  # (profile_id, profile_name, parsed_resume)
    api_key: str,
) -> Dict:
    """
    Score a job against all resume profiles, return best match.
    resume_profiles_data: list of (id, name, parsed_resume_dict)
    """
    best_result = None
    best_score = -1
    best_profile_name = ""

    for profile_id, profile_name, resume_data in resume_profiles_data:
        result = calculate_match(job, resume_data, api_key)
        score = result.get("match_percentage", 0)

        if score > best_score:
            best_score = score
            best_result = result
            best_profile_name = profile_name

        time.sleep(0.5)  # Small pause between API calls

    if best_result is None:
        best_result = {"match_percentage": 0, "matched_skills": [], "missing_skills": [],
                       "why_good_fit": "", "urgency": "LOW", "recommended_action": "Skip", "job_tags": []}

    best_result["matched_profile"] = best_profile_name
    return best_result


# ─────────────────────────────────────────────────────────────────
# Resume Improvement Tips
# ─────────────────────────────────────────────────────────────────

TIPS_PROMPT = """
Based on the top job requirements this week, suggest 5 specific improvements 
this candidate should make to their resume to increase match rates.

Top missing skills across all jobs this week: {missing_skills}
Candidate's current skills: {current_skills}

Return ONLY a JSON array of 5 improvement tips (strings), no explanation:
["tip 1", "tip 2", "tip 3", "tip 4", "tip 5"]
"""


def generate_resume_tips(
    missing_skills_list: List[str],
    resume_profile: Dict,
    api_key: str,
) -> List[str]:
    """Generate actionable resume improvement suggestions."""
    client = _get_client(api_key)
    from collections import Counter
    top_missing = [s for s, _ in Counter(missing_skills_list).most_common(15)]

    current = (
        resume_profile.get("technical_skills", []) +
        resume_profile.get("languages", []) +
        resume_profile.get("frameworks", [])
    )

    prompt = TIPS_PROMPT.format(
        missing_skills=", ".join(top_missing),
        current_skills=", ".join(current[:20]),
    )

    raw = _safe_generate(client, prompt)
    try:
        tips = json.loads(raw.strip())
        if isinstance(tips, list):
            return tips[:5]
    except Exception:
        pass

    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))[:5]
        except Exception:
            pass

    return ["Improve your resume based on job market demands."]
