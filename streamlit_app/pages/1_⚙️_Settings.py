"""
1_⚙️_Settings.py
All user preferences — configured once, used daily.
"""
import json
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Settings — OpportunityBot", page_icon="⚙️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.section-header{background:linear-gradient(135deg,#1565c0,#0d47a1);color:white;padding:1rem 1.5rem;
  border-radius:10px;margin:1.5rem 0 1rem;font-weight:600;font-size:1.05rem;}
</style>""", unsafe_allow_html=True)

st.title("⚙️ Settings")
st.caption("Configure everything here. Click **Save Settings** at the bottom to apply.")

# ── Load current config ──────────────────────────────────────
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.json"

def load():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"profile": {}, "email": {}, "preferences": {}, "watchlist_companies": [],
            "enabled_sources": {}, "resume_profiles": []}

cfg = load()

# ── SECTION 1: PROFILE ───────────────────────────────────────
st.markdown('<div class="section-header">👤 Your Profile</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Full Name", value=cfg.get("profile", {}).get("name", ""))
    branch = st.selectbox("Branch / Major", 
        ["CSE", "ECE", "IT", "EEE", "Mechanical", "Civil", "Chemical", "Biotechnology", "Data Science", "Other"],
        index=["CSE","ECE","IT","EEE","Mechanical","Civil","Chemical","Biotechnology","Data Science","Other"]
              .index(cfg.get("profile", {}).get("branch", "CSE")) 
              if cfg.get("profile", {}).get("branch") in ["CSE","ECE","IT","EEE","Mechanical","Civil","Chemical","Biotechnology","Data Science","Other"] else 0
    )
with col2:
    grad_year = st.number_input("Graduation Year", min_value=2025, max_value=2030, 
                                value=cfg.get("profile", {}).get("graduation_year", 2027))
    college = st.text_input("College Name", value=cfg.get("profile", {}).get("college", ""))

# ── SECTION 2: EMAIL ─────────────────────────────────────────
st.markdown('<div class="section-header">📧 Email Settings</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    sender_email = st.text_input("Your Gmail (sender)", 
                                  value=cfg.get("email", {}).get("sender_email", ""),
                                  placeholder="yourname@gmail.com")
    st.caption("This Gmail account will send the daily email.")
with col2:
    recipient_email = st.text_input("Recipient Email (you receive here)", 
                                     value=cfg.get("email", {}).get("recipient_email", ""),
                                     placeholder="yourname@gmail.com")

st.info("🔑 Your **Gmail App Password** is stored securely in Streamlit Secrets — not here. "
        "Set it once in your Streamlit Cloud dashboard under **Secrets**.")

# Time picker
times = [f"{h:02d}:{m:02d}" for h in range(4, 10) for m in [0, 30]]
current_time = cfg.get("email", {}).get("send_time_ist", "07:00")
time_idx = times.index(current_time) if current_time in times else times.index("07:00")
send_time = st.select_slider("📅 Daily Email Time (IST)", options=times, value=times[time_idx])
st.caption(f"Bot will run every day at **{send_time} IST** automatically via GitHub Actions.")

# ── SECTION 3: JOB PREFERENCES ──────────────────────────────
st.markdown('<div class="section-header">📍 Job Preferences</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    location_opts = ["Bengaluru", "Remote", "Hyderabad", "Mumbai", "Pune", "Chennai", "Delhi NCR"]
    current_locs  = cfg.get("preferences", {}).get("locations", ["Bengaluru"])
    locations = st.multiselect("Preferred Locations", location_opts, default=current_locs)

    job_type_opts = ["Internship", "Full-time"]
    current_types = cfg.get("preferences", {}).get("job_types", ["Internship", "Full-time"])
    job_types = st.multiselect("Job Types", job_type_opts, default=current_types)

with col2:
    min_salary = st.number_input(
        "Minimum Salary for Full-time (LPA)",
        min_value=0, max_value=50, step=1,
        value=int(cfg.get("preferences", {}).get("min_salary_lpa", 0)),
        help="Set to 0 to show all jobs regardless of salary."
    )
    min_match = st.slider(
        "Minimum Match % to include in report",
        min_value=20, max_value=80, step=5,
        value=cfg.get("preferences", {}).get("min_match_percent", 40),
        help="Jobs below this threshold are filtered out."
    )
    st.caption(f"Only jobs with ≥ **{min_match}%** alignment will appear in your Excel.")

# ── SECTION 4: COMPANY WATCHLIST ────────────────────────────
st.markdown('<div class="section-header">🏆 Company Watchlist</div>', unsafe_allow_html=True)
st.caption("Jobs from these companies always appear — even if match % is low.")

current_watchlist = cfg.get("watchlist_companies", [])

# Tag-style input
new_company = st.text_input("Add company to watchlist", placeholder="e.g. Google, Flipkart, Zepto")
col_add, _ = st.columns([1, 4])
with col_add:
    if st.button("➕ Add") and new_company.strip():
        if new_company.strip() not in current_watchlist:
            current_watchlist.append(new_company.strip())
            st.rerun()

if current_watchlist:
    st.write("**Current watchlist:**")
    cols = st.columns(min(len(current_watchlist), 5))
    to_remove = []
    for i, company in enumerate(current_watchlist):
        with cols[i % 5]:
            if st.button(f"✕ {company}", key=f"rm_{i}"):
                to_remove.append(company)
    for c in to_remove:
        current_watchlist.remove(c)
else:
    st.info("No companies in watchlist. Add them above.")

# ── SECTION 5: JOB SOURCES ──────────────────────────────────
st.markdown('<div class="section-header">📡 Job Sources</div>', unsafe_allow_html=True)
st.caption("Toggle sources on or off.")

sources_cfg = cfg.get("enabled_sources", {})
source_info = {
    "linkedin":    ("LinkedIn",    "MNCs + Startups",     "🔵"),
    "indeed":      ("Indeed",      "MNCs + Startups",     "🔴"),
    "glassdoor":   ("Glassdoor",   "MNCs + Reviews",      "🟢"),
    "naukri":      ("Naukri",      "IT Mass Hiring",      "🟠"),
    "wellfound":   ("Wellfound",   "Startups (India)",    "🟣"),
    "internshala": ("Internshala", "Internships",         "🔷"),
    "unstop":      ("Unstop",      "Campus & Hackathons", "⭐"),
    "cutshort":    ("Cutshort",    "Startups & GCCs",     "🔶"),
    "yc_jobs":     ("YC Jobs",     "Top Global Startups", "🏆"),
    "hackernews":  ("HackerNews",  "Tech Startups",       "🟡"),
}

cols = st.columns(2)
enabled_sources = {}
for i, (key, (label, desc, icon)) in enumerate(source_info.items()):
    with cols[i % 2]:
        enabled_sources[key] = st.checkbox(
            f"{icon} **{label}** — {desc}",
            value=sources_cfg.get(key, True),
            key=f"src_{key}"
        )

# ── SECTION 6: API KEYS (Info only) ─────────────────────────
st.markdown('<div class="section-header">🔑 API Keys & Secrets</div>', unsafe_allow_html=True)

with st.expander("ℹ️ How to set your API keys securely"):
    st.markdown("""
**Your secrets are NEVER stored in config.json or the code.** They are stored in:

1. **GitHub Repository Secrets** (used by GitHub Actions):
   - Go to your repo → **Settings** → **Secrets and variables** → **Actions**
   - Add: `GEMINI_API_KEY`, `GMAIL_APP_PASSWORD`, `GH_PAT`

2. **Streamlit Cloud Secrets** (used by this web app):
   - Go to [share.streamlit.io](https://share.streamlit.io) → Your app → **⋮ menu** → **Settings** → **Secrets**
   - Add in TOML format:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   GMAIL_APP_PASSWORD = "your-16-char-password"
   GH_PAT = "ghp_yourpersonalaccesstoken"
   GITHUB_REPO = "yourusername/opportunitybot"
   ```

**Where to get them:**
- Gemini API Key → [aistudio.google.com](https://aistudio.google.com) (free)
- Gmail App Password → Google Account → Security → 2-Step Verification → App Passwords
- GitHub PAT → GitHub → Settings → Developer Settings → Personal Access Tokens → Fine-grained
    """)

# ── SAVE BUTTON ──────────────────────────────────────────────
st.markdown("---")
col_save, col_reset, _ = st.columns([1, 1, 4])

with col_save:
    save_clicked = st.button("💾 Save Settings", type="primary", use_container_width=True)

with col_reset:
    if st.button("↩️ Reset to Saved", use_container_width=True):
        st.rerun()

if save_clicked:
    # Build updated config
    updated_cfg = {
        **cfg,  # Keep resume_profiles intact
        "profile": {
            "name": name, "branch": branch,
            "graduation_year": grad_year, "college": college
        },
        "email": {
            "sender_email": sender_email,
            "recipient_email": recipient_email,
            "send_time_ist": send_time,
        },
        "preferences": {
            "locations": locations,
            "job_types": job_types,
            "min_salary_lpa": min_salary,
            "min_match_percent": min_match,
            "batch_year": grad_year,
        },
        "watchlist_companies": current_watchlist,
        "enabled_sources": enabled_sources,
    }

    # Save locally
    with open(CONFIG_PATH, "w") as f:
        json.dump(updated_cfg, f, indent=2)

    # Push to GitHub if PAT available
    try:
        pat = st.secrets.get("GH_PAT", "")
        repo_name = st.secrets.get("GITHUB_REPO", "")
        if pat and repo_name:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from utils.github_sync import push_config
            success = push_config(updated_cfg, pat, repo_name)
            if success:
                st.success("✅ Settings saved and synced to GitHub!")
            else:
                st.warning("Settings saved locally. Could not sync to GitHub — check your GH_PAT secret.")
        else:
            st.success("✅ Settings saved! (Set GH_PAT and GITHUB_REPO in Streamlit Secrets to auto-sync)")
    except Exception as e:
        st.success("✅ Settings saved locally!")
        st.info(f"GitHub sync skipped: {e}")
