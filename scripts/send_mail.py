import smtplib
from email.message import EmailMessage
import sys
import os
import time
from pathlib import Path

# Auto-load .env if GMAIL_APP_PASSWORD not in environment
PROJECT_ROOT = Path(__file__).resolve().parent.parent
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file, override=False)
    except ImportError:
        # Fallback simple env parser
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v

if len(sys.argv) < 2:
    print("Usage: python send_mail.py <cloudflare_link>")
    sys.exit(1)

link = sys.argv[1].strip()

EMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "sharn.ss123@gmail.com")
EMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

if not EMAIL_PASSWORD:
    print("❌ Error: GMAIL_APP_PASSWORD is not set. Please check your .env file.")
    sys.exit(1)

RECIPIENTS = ['sharn.ss123@gmail.com', 'taranpreetkaur0605@gmail.com']

msg = EmailMessage()
msg['Subject'] = '🚀 GNDEC AI RAG System is Online'
msg['From'] = EMAIL_ADDRESS
msg['To'] = ', '.join(RECIPIENTS)

plain_content = f"""Hello,

Your GNDEC AI Assistant (RAG System) is running and accessible online!

Live Cloudflare Access URL:
{link}

• Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}
• Local Port: 5173 (Frontend) / 8000 (Backend API)
"""
msg.set_content(plain_content)

html_content = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
  <div style="max-width: 600px; margin: 20px auto; border: 1px solid #e0e0e0; border-radius: 8px; padding: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
    <h2 style="color: #0066b3; margin-top: 0;">🚀 GNDEC AI Assistant is Online</h2>
    <p>Your RAG system is running and accessible from anywhere via the link below:</p>
    <div style="margin: 25px 0;">
      <a href="{link}" style="background-color: #0066b3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
        Open GNDEC AI Assistant
      </a>
    </div>
    <p style="font-size: 13px; color: #666; word-break: break-all;">
      Direct link: <a href="{link}" style="color: #0066b3;">{link}</a>
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
    <p style="font-size: 12px; color: #888; margin-bottom: 0;">
      Started on: {time.strftime('%Y-%m-%d %H:%M:%S')}<br/>
      Local Frontend: Port 5173 | Backend API: Port 8000
    </p>
  </div>
</body>
</html>
"""
msg.add_alternative(html_content, subtype='html')

def try_send_mail(max_attempts=15, delay=5):
    """
    Robust mail sender with automatic fallback between:
    - Port 465 (SSL)
    - Port 587 (STARTTLS)
    Includes retry loop to survive temporary boot/network latency or connection resets.
    """
    for attempt in range(1, max_attempts + 1):
        # Alternate or try 587 then 465
        for port, use_ssl in [(587, False), (465, True)]:
            try:
                if use_ssl:
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as smtp:
                        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                        smtp.send_message(msg)
                else:
                    with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as smtp:
                        smtp.ehlo()
                        smtp.starttls()
                        smtp.ehlo()
                        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                        smtp.send_message(msg)

                print(f"✅ Email sent successfully to {', '.join(RECIPIENTS)} (attempt {attempt}, port {port})")
                return True
            except Exception as e:
                # Log attempt failure and continue
                print(f"[-] Attempt {attempt}/{max_attempts} on port {port} failed: {e}")

        if attempt < max_attempts:
            print(f"⏳ Waiting {delay}s before next email attempt...")
            time.sleep(delay)

    return False

success = try_send_mail()
if not success:
    print(f"❌ Failed to send email after multiple attempts.")
    sys.exit(1)
