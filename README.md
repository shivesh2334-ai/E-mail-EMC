# Bulk Email Sender (Streamlit)

This repository contains a simple Streamlit application to send emails (including attachments) in bulk via SMTP.

Features
- Provide recipients via CSV or paste a list (comma / newline / semicolon separated).
- Upload one or more attachments.
- Use SMTP (defaults to Gmail `smtp.gmail.com:465`).
- Progress bar and send report (downloadable CSV).

Security notes
- Do NOT hardcode passwords in source files or push them to a repo.
- For Gmail accounts with 2FA enabled: create an App Password for SMTP and use it here.
- You can set environment variables SENDER_EMAIL and SENDER_PASSWORD to avoid typing them into the UI.
- Gmail and other providers enforce rate limits (per minute / per day). Sending large batches may require a transactional provider (SendGrid, Mailgun, Amazon SES) or throttling.

Quick start (local)
1. Clone this repo:
   - git clone <this-repo-url>
2. Create a virtual environment and install dependencies:
   - python -m venv .venv
   - source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   - pip install -r requirements.txt
3. (Optional) Set environment variables:
   - export SENDER_EMAIL="you@example.com"
   - export SENDER_PASSWORD="app-password-or-password"
4. Run the Streamlit app:
   - streamlit run app.py
5. In the app:
   - Enter SMTP settings (defaults are for Gmail).
   - Fill sender email and password (or rely on env vars).
   - Upload CSV or paste recipients.
   - Add subject, body, and attachments.
   - Click "Send emails". Download the report when done.

CSV format
- The app will attempt to parse a CSV. It looks for a column named `email` (case-insensitive).
- If no `email` column exists, it will use the first column in the CSV as the recipient list.

Limitations & improvements
- This app sends sequentially and is intended for small-to-medium batches. For high volume sending, use a transactional email service or implement batching + retries.
- No advanced validation is performed on email addresses (can be added).
- Consider adding OAuth2 for Gmail (no password required) for production use.

License
- MIT (or choose your preferred license)

If you want, I can:
- Add Gmail OAuth2 support (recommended over passwords for production).
- Add batching/throttling, retry logic, and exponential backoff.
- Integrate with SendGrid / Mailgun / SES APIs to avoid SMTP limits.
