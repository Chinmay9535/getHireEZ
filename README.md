# 🤖 OpportunityBot
### AI-Powered Daily Job Alert System | 100% Free | Gemini AI | Multi-Resume

Searches 10+ job boards every morning, scores each job against your resume using Gemini AI, 
and emails you a color-coded Excel report — all automatically, completely free.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🔍 10+ Job Sources | LinkedIn, Indeed, Glassdoor, Naukri, Wellfound, Internshala, Unstop, YC Jobs, HackerNews, Cutshort |
| 🧠 AI Matching | Gemini 1.5 Flash scores every job against your resume (0–100%) |
| 📄 Multi-Resume | Upload different resumes for different roles (SDE, ML, etc.) |
| 📊 Excel Report | 4-sheet workbook: Jobs, Skills Gap, Watchlist, Summary |
| 📧 Daily Email | Automated Gmail delivery at your chosen time |
| 🖥️ Web App | Self-configurable Streamlit dashboard — no code editing |
| 🆓 100% Free | GitHub Actions + Streamlit Cloud + Gemini Free Tier |

---

## 🚀 Setup Guide (30 minutes, one-time)

### Step 1 — Fork & clone this repo
```bash
# Fork on GitHub, then:
git clone https://github.com/YOURUSERNAME/opportunitybot
cd opportunitybot
```

### Step 2 — Add GitHub Secrets
Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret Name | Value | Where to get |
|-------------|-------|-------------|
| `GEMINI_API_KEY` | Your API key | [aistudio.google.com](https://aistudio.google.com) (free) |
| `GMAIL_APP_PASSWORD` | 16-char app password | Google Account → Security → App Passwords |
| `GH_PAT` | Personal Access Token | GitHub → Settings → Developer Settings → PAT (repo + workflow scopes) |

### Step 3 — Deploy the Config App (Streamlit)
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **"Create app"** → Connect your GitHub repo
3. Set **Main file path** to: `streamlit_app/app.py`
4. Click **Deploy**

5. After deploy → app **⋮ menu** → **Settings** → **Secrets**, paste:
```toml
GEMINI_API_KEY = "your-key"
GMAIL_APP_PASSWORD = "your-16-char-password"
GH_PAT = "ghp_yourtoken"
GITHUB_REPO = "yourusername/opportunitybot"
```

### Step 4 — Configure via the Web App
1. Open your Streamlit app URL
2. Go to **⚙️ Settings** → fill in your email, preferences, watchlist
3. Go to **📄 Resume Manager** → upload your PDF resume(s) and set target roles
4. Go to **🧪 Test Run** → click **Run Now** to verify everything works

### Step 5 — Go live!
- GitHub Actions runs automatically every morning at your configured time
- You'll receive an Excel in your inbox daily 🎉

---

## 📁 Project Structure

```
opportunitybot/
├── streamlit_app/              ← Web config app
│   ├── app.py                  ← Home dashboard
│   ├── pages/
│   │   ├── 1_⚙️_Settings.py   ← All preferences
│   │   ├── 2_📄_Resume_Manager.py
│   │   ├── 3_📊_History.py
│   │   └── 4_🧪_Test_Run.py
│   └── utils/
│       ├── github_sync.py      ← GitHub API integration
│       └── gemini_preview.py   ← Real-time skill extraction
│
├── job_hunter/                 ← Core engine (GitHub Actions)
│   ├── main.py                 ← Orchestrator
│   ├── config_loader.py
│   ├── gemini_engine.py        ← AI matching
│   ├── excel_builder.py
│   ├── emailer.py
│   ├── deduplicator.py
│   └── scrapers/               ← 10+ job source scrapers
│
├── .github/workflows/
│   └── daily_job_hunt.yml      ← Cron schedule
│
├── config.json                 ← Your preferences (written by app)
├── resumes/                    ← Your PDF resumes
├── data/
│   ├── seen_jobs.db            ← Deduplication database
│   └── reports/                ← Past Excel reports
└── requirements.txt
```

---

## 📊 Excel Report Format

The daily Excel has **4 sheets**:
1. **📋 Today's Jobs** — All matched jobs, color-coded by match %
2. **📉 Skills Gap** — Most common missing skills with a bar chart
3. **🏆 Watchlist** — Jobs from your tracked companies
4. **📊 Summary** — Daily stats + resume improvement tips

**Color coding:**
- 🟢 Green = 80–100% match
- 🟡 Yellow = 60–79% match
- 🟠 Orange = 40–59% match

---

## 🔐 Security

- API keys are stored in **GitHub Encrypted Secrets** and **Streamlit Secrets** only
- Your resume PDFs are in your **private GitHub repo** — only you can access them
- No data is sent to any third-party service except Google's Gemini API

---

## 💡 Tips

- **Add more job sources** in Settings → Sources for broader coverage
- **Lower the min match %** to 30% during off-season to see more jobs
- **Update your resume** regularly — re-upload when you complete a new project
- Check **📉 Skills Gap** tab weekly to know what to learn next

---

## 🆓 Cost Breakdown

| Service | Free Tier | Your Usage |
|---------|-----------|-----------|
| GitHub Actions | 2000 min/month | ~150 min/month ✅ |
| Gemini Flash API | 1500 req/day | ~100–150 req/day ✅ |
| Streamlit Cloud | Unlimited public apps | 1 app ✅ |
| Gmail SMTP | 500 emails/day | 1 email/day ✅ |
| **Total** | — | **₹0/month** 🎉 |

---

*Built with ❤️ for 2027 batch students in Bengaluru*
