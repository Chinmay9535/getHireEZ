"""
app.py — OpportunityBot Configuration Web App (Main Entry)
Hosted FREE on Streamlit Community Cloud
"""
import streamlit as st

st.set_page_config(
    page_title="OpportunityBot — Control Panel",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .main-header {
    background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
    padding: 2rem; border-radius: 16px; text-align: center;
    margin-bottom: 1.5rem;
  }
  .main-header h1 { color: white; font-size: 2.2rem; margin: 0; }
  .main-header p  { color: #bbdefb; margin: 0.4rem 0 0; font-size: 1rem; }

  .stat-card {
    background: white; border-radius: 12px; padding: 1.2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-left: 4px solid #1565c0; text-align: center;
  }
  .stat-card .number { font-size: 2rem; font-weight: 700; color: #1565c0; }
  .stat-card .label  { color: #666; font-size: 0.85rem; }

  .stButton > button {
    background: linear-gradient(135deg, #1565c0, #0d47a1);
    color: white; border: none; border-radius: 8px;
    padding: 0.5rem 2rem; font-weight: 600;
    transition: all 0.2s;
  }
  .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(21,101,192,0.4); }

  .nav-card {
    background: white; border-radius: 12px; padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08); cursor: pointer;
    transition: all 0.2s; text-align: center; text-decoration: none;
    border: 2px solid transparent;
  }
  .nav-card:hover { border-color: #1565c0; transform: translateY(-2px); }
  .nav-card .icon { font-size: 2.5rem; }
  .nav-card .title { font-weight: 600; margin-top: 0.5rem; }
  .nav-card .desc  { color: #666; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🤖 OpportunityBot</h1>
  <p>AI-Powered Daily Job Alert System &nbsp;|&nbsp; Powered by Gemini &nbsp;|&nbsp; 100% Free</p>
</div>
""", unsafe_allow_html=True)

# ── Quick stats ──────────────────────────────────────────────
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

def load_config_raw():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}

cfg = load_config_raw()
profiles_count  = len(cfg.get("resume_profiles", []))
watchlist_count = len(cfg.get("watchlist_companies", []))
is_configured   = bool(cfg.get("email", {}).get("recipient_email"))

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="stat-card">
      <div class="number">{profiles_count}</div>
      <div class="label">Resume Profiles</div>
    </div>""", unsafe_allow_html=True)
with c2:
    sources = cfg.get("enabled_sources", {})
    active_sources = sum(1 for v in sources.values() if v)
    st.markdown(f"""<div class="stat-card">
      <div class="number">{active_sources}</div>
      <div class="label">Job Sources Active</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="stat-card">
      <div class="number">{watchlist_count}</div>
      <div class="label">Watchlist Companies</div>
    </div>""", unsafe_allow_html=True)
with c4:
    status_text  = "✅ Configured" if is_configured else "⚙️ Setup Required"
    status_color = "#2e7d32" if is_configured else "#c62828"
    st.markdown(f"""<div class="stat-card">
      <div class="number" style="color:{status_color};font-size:1.2rem;">{status_text}</div>
      <div class="label">Bot Status</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Navigation cards ─────────────────────────────────────────
st.subheader("📂 Quick Navigation")
nc1, nc2, nc3, nc4 = st.columns(4)

with nc1:
    st.markdown("""<div class="nav-card">
      <div class="icon">⚙️</div>
      <div class="title">Settings</div>
      <div class="desc">Configure email, preferences, watchlist & sources</div>
    </div>""", unsafe_allow_html=True)

with nc2:
    st.markdown("""<div class="nav-card">
      <div class="icon">📄</div>
      <div class="title">Resume Manager</div>
      <div class="desc">Upload resumes & set target roles per profile</div>
    </div>""", unsafe_allow_html=True)

with nc3:
    st.markdown("""<div class="nav-card">
      <div class="icon">📊</div>
      <div class="title">History</div>
      <div class="desc">View & download past daily reports</div>
    </div>""", unsafe_allow_html=True)

with nc4:
    st.markdown("""<div class="nav-card">
      <div class="icon">🧪</div>
      <div class="title">Test Run</div>
      <div class="desc">Trigger a manual search right now</div>
    </div>""", unsafe_allow_html=True)

st.caption("👈 Use the sidebar to navigate between pages")

# ── Setup checklist ──────────────────────────────────────────
st.markdown("---")
st.subheader("🚀 Setup Checklist")

checks = [
    ("Gemini API Key set",           bool(st.secrets.get("GEMINI_API_KEY", "")) if hasattr(st, "secrets") else False),
    ("Gmail App Password set",       bool(st.secrets.get("GMAIL_APP_PASSWORD", "")) if hasattr(st, "secrets") else False),
    ("Recipient email configured",   is_configured),
    ("At least 1 resume uploaded",   profiles_count > 0),
    ("Target roles set",             any(len(p.get("target_roles",[])) > 0 for p in cfg.get("resume_profiles",[]))),
]

for label, done in checks:
    icon = "✅" if done else "⬜"
    color = "#2e7d32" if done else "#888"
    st.markdown(f"<span style='color:{color};font-size:1rem;'>{icon} {label}</span>", unsafe_allow_html=True)

if all(done for _, done in checks):
    st.success("🎉 All set! The bot will run automatically every morning at your configured time.")
else:
    st.info("👆 Complete the checklist above to activate the bot. Start with **⚙️ Settings**.")
