"""
4_🧪_Test_Run.py
Manually trigger the GitHub Actions workflow for an immediate job search.
"""
import sys
import streamlit as st
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="Test Run — OpportunityBot", page_icon="🧪", layout="wide")

st.title("🧪 Test Run")
st.caption("Trigger an immediate job search without waiting for tomorrow's scheduled run.")

# ── Status check ─────────────────────────────────────────────
import json
ROOT        = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "config.json"

cfg = {}
if CONFIG_PATH.exists():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

profiles_count = len(cfg.get("resume_profiles", []))
email_set      = bool(cfg.get("email", {}).get("recipient_email"))

# ── Readiness check ──────────────────────────────────────────
st.subheader("✅ Pre-flight Check")

checks = {
    "At least 1 resume profile added":  profiles_count > 0,
    "Recipient email configured":        email_set,
    "GH_PAT secret available":          bool(st.secrets.get("GH_PAT", "")),
    "GITHUB_REPO secret set":            bool(st.secrets.get("GITHUB_REPO", "")),
    "GEMINI_API_KEY secret set":         bool(st.secrets.get("GEMINI_API_KEY", "")),
}

all_ready = True
for label, ok in checks.items():
    icon = "✅" if ok else "❌"
    if not ok:
        all_ready = False
    st.markdown(f"{icon} {label}")

st.markdown("---")

# ── Trigger button ───────────────────────────────────────────
if all_ready:
    st.success("🟢 Everything is ready! Click below to run the bot now.")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🚀 Run Bot Now", type="primary", use_container_width=True):
            with st.spinner("Triggering GitHub Actions workflow…"):
                try:
                    from utils.github_sync import trigger_workflow
                    pat  = st.secrets.get("GH_PAT", "")
                    repo = st.secrets.get("GITHUB_REPO", "")
                    success = trigger_workflow(pat, repo)

                    if success:
                        st.balloons()
                        st.success("""
                        ✅ **Workflow triggered successfully!**
                        
                        The bot is now running on GitHub Actions. It will:
                        1. Scrape jobs from all enabled sources
                        2. Match them against your resumes with Gemini AI
                        3. Build the Excel report
                        4. Email it to you
                        
                        This usually takes **5–15 minutes**. Check your email!
                        """)
                        st.info(f"📍 Track progress at: `https://github.com/{repo}/actions`")
                    else:
                        st.error("❌ Could not trigger workflow. Check your GH_PAT permissions (needs `workflow` scope).")
                except Exception as e:
                    st.error(f"Error: {e}")
else:
    st.warning("⚠️ Complete the pre-flight checks above before running.")
    if not profiles_count:
        st.info("👉 Go to **📄 Resume Manager** to upload your resume first.")
    if not email_set:
        st.info("👉 Go to **⚙️ Settings** to set your email address.")

# ── Alternative: run locally ─────────────────────────────────
st.markdown("---")
with st.expander("🖥️ Alternatively: Run locally on your machine"):
    st.markdown("""
    If you're running this app locally, you can run the bot directly in your terminal:
    
    ```bash
    # From the OpportunityBot project root:
    set GEMINI_API_KEY=your_key_here
    set GMAIL_APP_PASSWORD=your_app_password
    python job_hunter/main.py
    ```
    
    The Excel report will be saved to `data/reports/` and emailed to you.
    """)

# ── Schedule info ────────────────────────────────────────────
st.markdown("---")
st.subheader("⏰ Automatic Schedule")
send_time = cfg.get("email", {}).get("send_time_ist", "07:00")
st.info(f"""
The bot runs automatically every day at **{send_time} IST** via GitHub Actions.  
No action needed — it runs in the background even when this app is closed.

To change the time → **⚙️ Settings** → Daily Email Time
""")
