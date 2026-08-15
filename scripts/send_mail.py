import smtplib
from email.message import EmailMessage
import sys
import os

if len(sys.argv) < 2:
    print("Usage: python send_mail.py <cloudflare_link>")
    sys.exit(1)

link = sys.argv[1]

# You must set your Gmail address and App Password in your environment or hardcode them here.
# To get an App Password, go to Google Account -> Security -> 2-Step Verification -> App Passwords.
EMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "sharn.ss123@gmail.com")
EMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

if not EMAIL_PASSWORD:
    print("Error: GMAIL_APP_PASSWORD is not set. Please set it in your environment or script.")
    sys.exit(1)

msg = EmailMessage()
msg.set_content(f"Your GNDEC AI Assistant is running!\n\nAccess it from anywhere using this Cloudflare link:\n{link}")

msg['Subject'] = 'GNDEC AI RAG System is Online'
msg['From'] = EMAIL_ADDRESS
msg['To'] = 'sharn.ss123@gmail.com'

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
    print("✅ Email sent successfully to sharn.ss123@gmail.com")
except Exception as e:
    print(f"❌ Failed to send email: {e}")
