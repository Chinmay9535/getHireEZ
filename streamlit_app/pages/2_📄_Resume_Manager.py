"""
2_📄_Resume_Manager.py
Upload multiple resumes, set target roles per profile,
see AI-extracted skills in real time.
"""
import json
import uuid
import sys
import streamlit as st
from datetime import date
from pathlib import Path

st.set_page_config(page_title="Resume Manager — OpportunityBot", page_icon="📄", layout="wide")

sys.path.insert(0, str(Path(__file__).parent.parent))

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.resume-card{background:white;border:2px solid #e3e8f0;border-radius:14px;padding:1.5rem;
  margin-bottom:1rem;transition:border-color 0.2s;}
.resume-card:hover{border-color:#1565c0;}
.skill-tag{display:inline-block;background:#e3f2fd;color:#1565c0;padding:3px 10px;
  border-radius:20px;font-size:0.8rem;margin:2px;font-weight:500;}
.section-header{background:linear-gradient(135deg,#1565c0,#0d47a1);color:white;
  padding:1rem 1.5rem;border-radius:10px;margin:1.5rem 0 1rem;font-weight:600;}
</style>""", unsafe_allow_html=True)

st.title("📄 Resume Manager")
st.caption("Upload different resumes for different roles. Each gets matched separately — the best score wins.")

# ── Paths & config ───────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH  = ROOT / "config.json"
RESUMES_DIR  = ROOT / "resumes"
RESUMES_DIR.mkdir(exist_ok=True)

def load_cfg():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"resume_profiles": []}

def save_cfg(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

def _push_config(cfg_data):
    """Helper to push config to GitHub."""
    try:
        pat  = st.secrets.get("GH_PAT", "")
        repo = st.secrets.get("GITHUB_REPO", "")
        if pat and repo:
            from utils.github_sync import push_config
            push_config(cfg_data, pat, repo)
    except Exception:
        pass

cfg = load_cfg()

# ── EXISTING PROFILES ────────────────────────────────────────
profiles = cfg.get("resume_profiles", [])

if profiles:
    st.markdown('<div class="section-header">📁 Your Resume Profiles</div>', unsafe_allow_html=True)

    to_delete = []
    for idx, profile in enumerate(profiles):
        with st.container():
            st.markdown(f"<div class='resume-card'>", unsafe_allow_html=True)
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.markdown(f"### 📄 {profile['name']}")
                st.caption(f"File: `{profile['filename']}` | Updated: {profile.get('last_updated','N/A')}")

                # Skills tags
                skills = profile.get("extracted_skills", [])
                if skills:
                    tags_html = " ".join(f"<span class='skill-tag'>{s}</span>" for s in skills[:20])
                    st.markdown(f"**Skills:** {tags_html}", unsafe_allow_html=True)

                # Target roles
                roles = profile.get("target_roles", [])
                st.markdown(f"**Target Roles:** {', '.join(roles) if roles else '*(not set)*'}")

            with col_actions:
                # Edit roles
                new_roles_raw = st.text_area(
                    "Edit target roles (one per line):",
                    value="\n".join(roles),
                    key=f"roles_{idx}",
                    height=100,
                )
                if st.button("💾 Update Roles", key=f"save_roles_{idx}"):
                    profiles[idx]["target_roles"] = [r.strip() for r in new_roles_raw.split("\n") if r.strip()]
                    cfg["resume_profiles"] = profiles
                    save_cfg(cfg)
                    # Push to GitHub
                    _push_config(cfg)
                    st.success("Roles updated!")

                if st.button(f"🗑️ Delete Profile", key=f"del_{idx}", type="secondary"):
                    to_delete.append(idx)

            st.markdown("</div>", unsafe_allow_html=True)

    # Handle deletions
    if to_delete:
        for i in sorted(to_delete, reverse=True):
            fname = profiles[i].get("filename", "")
            # Delete local file
            fpath = RESUMES_DIR / fname
            if fpath.exists():
                fpath.unlink()
            # Push delete to GitHub
            try:
                pat = st.secrets.get("GH_PAT","")
                repo = st.secrets.get("GITHUB_REPO","")
                if pat and repo:
                    from utils.github_sync import delete_resume
                    delete_resume(fname, pat, repo)
            except Exception:
                pass
            profiles.pop(i)
        cfg["resume_profiles"] = profiles
        save_cfg(cfg)
        st.rerun()

# ── UPLOAD NEW RESUME ────────────────────────────────────────
st.markdown('<div class="section-header">➕ Add New Resume Profile</div>', unsafe_allow_html=True)

with st.form("upload_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        profile_name = st.text_input(
            "Profile Name *",
            placeholder="e.g. SDE Profile, ML Profile, Backend Profile"
        )
        target_roles_input = st.text_area(
            "Target Roles * (one per line)",
            placeholder="Software Engineer\nSDE\nBackend Engineer\nFull Stack Developer",
            height=120,
        )

    with col2:
        uploaded_file = st.file_uploader(
            "Upload Resume PDF *",
            type=["pdf"],
            help="Upload your resume as a PDF file."
        )
        st.caption("Gemini AI will automatically extract your skills after upload.")

    submitted = st.form_submit_button("📤 Upload & Extract Skills", type="primary", use_container_width=True)

    if submitted:
        if not profile_name:
            st.error("Please enter a profile name.")
        elif not target_roles_input.strip():
            st.error("Please enter at least one target role.")
        elif uploaded_file is None:
            st.error("Please upload a PDF resume.")
        else:
            pdf_bytes = uploaded_file.read()

            # Try to get OpenRouter key
            openrouter_key = st.secrets.get("OPENROUTER_API_KEY", "")
            extracted = {}

            if openrouter_key:
                with st.spinner("✨ OpenRouter is analyzing your resume..."):
                    try:
                        from utils.llm_preview import extract_skills_preview
                        extracted = extract_skills_preview(pdf_bytes, openrouter_key)
                        if extracted.get("error"):
                            st.warning(f"Skill extraction issue: {extracted['error']}")
                            extracted = {}
                    except Exception as e:
                        st.warning(f"Could not extract skills automatically: {e}")
            else:
                st.info("Set OPENROUTER_API_KEY in Streamlit Secrets for automatic skill extraction.")

            # Save PDF locally
            safe_name = profile_name.lower().replace(" ", "_")
            filename  = f"{safe_name}_{uuid.uuid4().hex[:6]}.pdf"
            local_path = RESUMES_DIR / filename
            with open(local_path, "wb") as f:
                f.write(pdf_bytes)

            # Build skills list
            skills = (
                extracted.get("technical_skills", []) +
                extracted.get("languages", []) +
                extracted.get("frameworks", [])
            )[:25]

            roles = [r.strip() for r in target_roles_input.split("\n") if r.strip()]

            new_profile = {
                "id":               str(uuid.uuid4()),
                "name":             profile_name,
                "filename":         filename,
                "target_roles":     roles,
                "extracted_skills": skills,
                "extracted_full":   extracted,
                "last_updated":     str(date.today()),
            }

            cfg["resume_profiles"] = profiles + [new_profile]
            save_cfg(cfg)

            # Push to GitHub
            pat  = st.secrets.get("GH_PAT", "")
            repo = st.secrets.get("GITHUB_REPO", "")
            if pat and repo:
                try:
                    from utils.github_sync import push_resume, push_config
                    push_resume(pdf_bytes, filename, pat, repo)
                    push_config(cfg["resume_profiles"] and cfg, pat, repo)
                    st.success(f"✅ **{profile_name}** uploaded and synced to GitHub!")
                except Exception as e:
                    st.success(f"✅ **{profile_name}** saved locally! (GitHub sync error: {e})")
            else:
                st.success(f"✅ **{profile_name}** saved! Set GH_PAT in Streamlit Secrets to auto-sync.")

            # Show extracted skills
            if skills:
                st.markdown("**🧠 Auto-extracted skills:**")
                tags = " ".join(f"<span class='skill-tag'>{s}</span>" for s in skills)
                st.markdown(tags, unsafe_allow_html=True)

            st.rerun()

# ── TIPS ─────────────────────────────────────────────────────
with st.expander("💡 Tips for best results"):
    st.markdown("""
- **Multiple profiles** = better coverage. Example: one for SDE roles, one for ML roles.
- Keep resumes **ATS-friendly** (avoid tables/images, use clean text).
- **Update your resume** regularly — re-upload whenever you add a new project or skill.
- Target roles should match exact job titles you search for (e.g., "SDE Intern", not just "Software").
- Gemini extracts skills automatically — but you can always **edit target roles** manually above.
    """)
