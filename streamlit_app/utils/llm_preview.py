"""
llm_preview.py
Used by the Streamlit app to extract skills from a resume PDF 
in real-time as the user uploads it, giving instant feedback.
"""
import json
import re
import logging
from io import BytesIO
from typing import Dict, List

logger = logging.getLogger(__name__)


def extract_skills_preview(pdf_bytes: bytes, openrouter_api_key: str) -> Dict:
    """
    Extract key info from a resume PDF for preview in the app.
    Returns structured data without saving to disk.
    """
    # ── Extract text from PDF bytes ──────────────────────────
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
    except Exception as e:
        return {"error": f"Could not read PDF: {e}"}

    if not text.strip():
        return {"error": "PDF appears to be empty or image-only (no extractable text)"}

    # ── Call OpenRouter ──────────────────────────────────────────
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key
        )

        prompt = f"""
Analyse this resume and return ONLY a valid JSON object (no markdown, no explanation):
{{
  "name": "string",
  "branch": "string",
  "graduation_year": "number",
  "college": "string",
  "technical_skills": ["top 15 tech skills"],
  "languages": ["programming languages"],
  "frameworks": ["frameworks/libraries"],
  "tools": ["tools/platforms"],
  "domains": ["AI/ML", "Web Dev", etc],
  "projects_count": "number",
  "cgpa": "string or null",
  "summary": "2-sentence professional summary"
}}

Resume:
{text[:5000]}
"""
        response = client.chat.completions.create(
            model='nvidia/nemotron-3-super-120b-a12b:free',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        raw = response.choices[0].message.content or ""

        # Parse JSON
        parsed = {}
        try:
            # Strip markdown json blocks if returned
            if raw.startswith("```json"):
                raw = raw.replace("```json", "", 1)
                if raw.endswith("```"):
                    raw = raw[:-3]
            parsed = json.loads(raw.strip())
        except Exception:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except Exception:
                    pass

        return parsed if parsed else {"error": "OpenRouter returned no structured data"}

    except Exception as e:
        return {"error": f"OpenRouter API error: {e}"}
