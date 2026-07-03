"""
3_📊_History.py
View and download past daily Excel reports.
"""
import sys
import streamlit as st
import requests
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="History — OpportunityBot", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.report-card{background:white;border:1px solid #e3e8f0;border-radius:12px;
  padding:1rem 1.5rem;margin-bottom:0.8rem;display:flex;align-items:center;
  justify-content:space-between;}
</style>""", unsafe_allow_html=True)

st.title("📊 Report History")
st.caption("All past daily job reports. Download any as Excel.")

# ── Local reports first ──────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = ROOT / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

local_reports = sorted(REPORTS_DIR.glob("*.xlsx"), reverse=True)

# ── GitHub reports (if PAT available) ────────────────────────
gh_reports = []
try:
    pat  = st.secrets.get("GH_PAT", "")
    repo = st.secrets.get("GITHUB_REPO", "")
    if pat and repo:
        from utils.github_sync import list_reports
        gh_reports = list_reports(pat, repo)
except Exception:
    pass

# ── Merge & display ──────────────────────────────────────────
if not local_reports and not gh_reports:
    st.info("📭 No reports yet. Once the bot runs for the first time, your reports will appear here.")
    st.markdown("""
    **How to trigger the first run:**
    1. Make sure all settings and at least 1 resume are configured.
    2. Go to the **🧪 Test Run** page and click **Run Now**.
    3. Or wait for the automatic run tomorrow morning!
    """)
else:
    # Stats row
    total_reports = len(local_reports) or len(gh_reports)
    st.metric("Total Reports", total_reports, help="Number of daily reports generated so far")

    st.markdown("---")
    st.subheader("📁 Available Reports")

    # Local reports (prefer these when running locally)
    if local_reports:
        for report_path in local_reports[:30]:  # Cap at 30
            date_str = report_path.stem.replace("jobs_", "")
            try:
                display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y (%A)")
            except Exception:
                display_date = date_str

            size_kb = round(report_path.stat().st_size / 1024, 1)

            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.markdown(f"📅 **{display_date}**")
                st.caption(f"Size: {size_kb} KB")
            with col2:
                with open(report_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download",
                        data=f.read(),
                        file_name=report_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{report_path.name}",
                        use_container_width=True,
                    )
            with col3:
                st.caption(f"Local")
            st.divider()

    # GitHub reports (cloud)
    elif gh_reports:
        for report in gh_reports[:30]:
            date_str = report["name"].replace("jobs_", "").replace(".xlsx", "")
            try:
                display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y (%A)")
            except Exception:
                display_date = date_str

            size_kb = round(report.get("size", 0) / 1024, 1)
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"📅 **{display_date}**")
                st.caption(f"Size: {size_kb} KB | Source: GitHub")
            with col2:
                dl_url = report.get("download_url", "")
                if dl_url:
                    try:
                        resp = requests.get(dl_url, timeout=10)
                        if resp.status_code == 200:
                            st.download_button(
                                label="⬇️ Download",
                                data=resp.content,
                                file_name=report["name"],
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"gh_dl_{report['name']}",
                                use_container_width=True,
                            )
                    except Exception:
                        st.link_button("Open", dl_url)
            st.divider()
