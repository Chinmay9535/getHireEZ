"""
emailer.py
Sends the daily job report Excel as a Gmail email attachment.
Uses Gmail SMTP with App Password — completely free.
"""
import os
import smtplib
import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


def _build_html_body(jobs: List[Dict], report_date: str) -> str:
    """Build an HTML email body with summary + top matches."""
    total = len(jobs)
    high_match  = [j for j in jobs if j.get("match_percentage", 0) >= 80]
    good_match  = [j for j in jobs if 60 <= j.get("match_percentage", 0) < 80]
    urgent_jobs = [j for j in jobs if j.get("urgency") == "HIGH"]
    best_job    = max(jobs, key=lambda x: x.get("match_percentage", 0)) if jobs else {}

    # Top 5 urgent jobs for quick preview
    top5 = sorted(jobs, key=lambda x: -x.get("match_percentage", 0))[:5]

    top5_rows = ""
    for j in top5:
        pct = j.get("match_percentage", 0)
        color = "#2e7d32" if pct >= 80 else "#f57c00" if pct >= 60 else "#757575"
        apply = j.get("apply_url", "#")
        top5_rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;"><b>{j.get('company','')}</b></td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{j.get('title','')}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:{color};font-weight:bold;">{pct}%</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">{j.get('location','')}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">
            <a href="{apply}" style="background:#1565c0;color:white;padding:4px 10px;border-radius:4px;text-decoration:none;">Apply →</a>
          </td>
        </tr>"""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;background:#f5f5f5;">

  <div style="background:linear-gradient(135deg,#1565c0,#0d47a1);padding:28px;border-radius:12px 12px 0 0;text-align:center;">
    <h1 style="color:white;margin:0;font-size:24px;">🤖 OpportunityBot</h1>
    <p style="color:#bbdefb;margin:6px 0 0;">Daily Job Report — {report_date}</p>
  </div>

  <div style="background:white;padding:24px;border-radius:0 0 12px 12px;">

    <!-- Stats row -->
    <div style="display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap;">
      <div style="flex:1;background:#e8f5e9;padding:16px;border-radius:8px;text-align:center;min-width:130px;">
        <div style="font-size:28px;font-weight:bold;color:#2e7d32;">{total}</div>
        <div style="color:#555;font-size:13px;">Jobs Found</div>
      </div>
      <div style="flex:1;background:#fff8e1;padding:16px;border-radius:8px;text-align:center;min-width:130px;">
        <div style="font-size:28px;font-weight:bold;color:#f57f17;">{len(high_match)}</div>
        <div style="color:#555;font-size:13px;">80%+ Match 🟢</div>
      </div>
      <div style="flex:1;background:#fce4ec;padding:16px;border-radius:8px;text-align:center;min-width:130px;">
        <div style="font-size:28px;font-weight:bold;color:#c62828;">{len(urgent_jobs)}</div>
        <div style="color:#555;font-size:13px;">Apply Today 🔴</div>
      </div>
      <div style="flex:1;background:#e3f2fd;padding:16px;border-radius:8px;text-align:center;min-width:130px;">
        <div style="font-size:28px;font-weight:bold;color:#1565c0;">{best_job.get('match_percentage',0)}%</div>
        <div style="color:#555;font-size:13px;">Best Match</div>
      </div>
    </div>

    <!-- Best match callout -->
    {"" if not best_job else f'''
    <div style="background:#e3f2fd;border-left:4px solid #1565c0;padding:14px;border-radius:0 8px 8px 0;margin-bottom:20px;">
      <b>🏆 Top Match Today:</b> {best_job.get("title","")} at <b>{best_job.get("company","")}</b>
      — <span style="color:#1565c0;font-weight:bold;">{best_job.get("match_percentage",0)}% match</span>
      <br><a href="{best_job.get("apply_url","#")}" style="color:#1565c0;">Apply Now →</a>
    </div>'''}

    <!-- Top 5 jobs table -->
    <h3 style="color:#333;border-bottom:2px solid #1565c0;padding-bottom:8px;">⭐ Top Matches Today</h3>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="background:#1565c0;color:white;">
          <th style="padding:10px;text-align:left;">Company</th>
          <th style="padding:10px;text-align:left;">Role</th>
          <th style="padding:10px;text-align:left;">Match</th>
          <th style="padding:10px;text-align:left;">Location</th>
          <th style="padding:10px;text-align:left;"></th>
        </tr>
      </thead>
      <tbody>{top5_rows}</tbody>
    </table>

    <p style="color:#888;font-size:12px;margin-top:20px;">
      📎 Full list attached as Excel file with {total} jobs, skills gap analysis, and resume tips.<br>
      🟢 Green = 80%+ | 🟡 Yellow = 60-79% | 🟠 Orange = 40-59%
    </p>

  </div>

  <p style="text-align:center;color:#aaa;font-size:11px;margin-top:12px;">
    OpportunityBot | Powered by Gemini AI & GitHub Actions
  </p>
</body>
</html>"""


def send_report_email(
    sender_email: str,
    app_password: str,
    recipient_email: str,
    excel_path: Path,
    jobs: List[Dict],
    report_date: str = None,
):
    """Send the daily report email with Excel attachment."""
    if report_date is None:
        report_date = datetime.now().strftime("%B %d, %Y")

    total = len(jobs)
    best_pct = max((j.get("match_percentage", 0) for j in jobs), default=0)
    best_company = max(jobs, key=lambda x: x.get("match_percentage", 0)).get("company", "") if jobs else ""
    urgent_count = sum(1 for j in jobs if j.get("urgency") == "HIGH")

    subject = (
        f"🎯 [{datetime.now().strftime('%b %d')}] {total} New Jobs | "
        f"Top: {best_company} ({best_pct}%) | "
        f"🔴 {urgent_count} Urgent"
    )

    msg = MIMEMultipart("alternative")
    msg["From"]    = sender_email
    msg["To"]      = recipient_email
    msg["Subject"] = subject

    html_body = _build_html_body(jobs, report_date)
    msg.attach(MIMEText(html_body, "html"))

    # Attach Excel
    if excel_path.exists():
        with open(excel_path, "rb") as f:
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f"attachment; filename={excel_path.name}",
        )
        msg.attach(attachment)
    else:
        logger.warning(f"[Email] Excel file not found: {excel_path}")

    try:
        with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        logger.info(f"[Email] ✅ Report sent to {recipient_email}")
    except smtplib.SMTPAuthenticationError:
        logger.error("[Email] ❌ Authentication failed. Check Gmail App Password.")
        raise
    except Exception as e:
        logger.error(f"[Email] ❌ Failed to send: {e}")
        raise


def send_error_alert(
    sender_email: str,
    app_password: str,
    recipient_email: str,
    error_message: str,
):
    """Send a simple alert if the bot run fails."""
    msg = MIMEMultipart()
    msg["From"]    = sender_email
    msg["To"]      = recipient_email
    msg["Subject"] = "⚠️ OpportunityBot — Run Failed Today"

    body = f"""
    OpportunityBot encountered an error and could not complete today's run.

    Error: {error_message}

    Please check your GitHub Actions logs for details.
    Go to: https://github.com → Your Repo → Actions tab
    """
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
    except Exception as e:
        logger.error(f"[Email] Could not send error alert: {e}")
