"""
Streamlit app for sending emails in bulk with optional attachments.

Features:
- Provide recipients via CSV upload (first column or column named 'email') OR paste comma/newline-separated list.
- Upload multiple attachments.
- Use SMTP (default: Gmail smtp.gmail.com:465). Supply sender email and password (use App Password for Gmail with 2FA).
- Progress bar, success/failure reporting, download send report.

Security:
- Do NOT hardcode passwords. Use environment variables (SENDER_PASSWORD) or enter password into the app.
- For Gmail with 2FA: create an App Password and use that here.
"""

import os
import ssl
import smtplib
import mimetypes
import pandas as pd
import streamlit as st
from email.message import EmailMessage
from typing import List, Tuple
from io import StringIO, BytesIO

st.set_page_config(page_title="Bulk Email Sender", layout="centered")

def parse_recipients_from_csv(uploaded_file) -> List[str]:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=';')
        except Exception:
            # Try reading as plain text with one address per line
            uploaded_file.seek(0)
            text = uploaded_file.read().decode('utf-8')
            return [e.strip() for e in text.replace(',', '\n').splitlines() if e.strip()]

    # Try to find an 'email' column (case-insensitive)
    cols = {c.lower(): c for c in df.columns}
    if 'email' in cols:
        emails = df[cols['email']].dropna().astype(str).str.strip().tolist()
    else:
        # Use first column
        first_col = df.columns[0]
        emails = df[first_col].dropna().astype(str).str.strip().tolist()

    return emails

def parse_recipients_from_text(text: str) -> List[str]:
    # Accept comma, semicolon, newline separated
    sep_text = text.replace(';', ',').replace('\n', ',')
    emails = [e.strip() for e in sep_text.split(',') if e.strip()]
    return emails

def build_message(sender: str, recipient: str, subject: str, body_text: str, body_html: str, attachments: List[Tuple[str, bytes]]) -> EmailMessage:
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject

    if body_html:
        msg.set_content(body_text or "This message contains HTML content. Please view in an HTML-capable client.")
        msg.add_alternative(body_html, subtype='html')
    else:
        msg.set_content(body_text or "")

    # Attach files (attachments: list of (filename, bytes_data))
    for filename, data in attachments:
        ctype, encoding = mimetypes.guess_type(filename)
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=filename)
    return msg

def send_bulk_emails(smtp_host: str, smtp_port: int, sender: str, password: str, recipients: List[str], subject: str, body_text: str, body_html: str, attachments: List[Tuple[str, bytes]], use_ssl=True, timeout=60):
    results = []
    context = ssl.create_default_context()
    # Build recipient iteration, connect once and send messages in a loop
    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=timeout)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout)
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
        server.login(sender, password)
    except Exception as e:
        st.error(f"Failed to connect/login to SMTP server: {e}")
        return [{'recipient': None, 'status': 'error', 'error': str(e)}]

    try:
        for i, recipient in enumerate(recipients, start=1):
            try:
                msg = build_message(sender, recipient, subject, body_text, body_html, attachments)
                server.send_message(msg, from_addr=sender, to_addrs=[recipient])
                results.append({'recipient': recipient, 'status': 'sent', 'error': ''})
            except Exception as e:
                results.append({'recipient': recipient, 'status': 'failed', 'error': str(e)})
    finally:
        try:
            server.quit()
        except Exception:
            server.close()
    return results

# UI
st.title("Bulk Email Sender")

with st.expander("Instructions"):
    st.markdown("""
    - Provide recipients either by uploading a CSV (first column or a column named `email`) or paste addresses.
    - Upload one or more attachments (optional).
    - For Gmail with 2FA enabled: create an App Password and use it as the password here.
    - Be mindful of provider sending limits (Gmail typically limits daily and per-minute sends).
    """)
st.sidebar.header("SMTP settings")
smtp_host = st.sidebar.text_input("SMTP host", value=os.getenv("SMTP_HOST", "smtp.gmail.com"))
smtp_port = st.sidebar.number_input("SMTP port", value=int(os.getenv("SMTP_PORT", 465)), step=1)
use_ssl = st.sidebar.checkbox("Use SSL (recommended)", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("Environment variables (optional): SENDER_EMAIL, SENDER_PASSWORD")

st.markdown("### Sender")
sender_email = st.text_input("Sender email", value=os.getenv("SENDER_EMAIL", ""))
sender_password = st.text_input("Sender password (or App Password)", value=os.getenv("SENDER_PASSWORD", ""), type="password")
if not sender_password:
    st.info("Tip: set SENDER_PASSWORD in your environment, or paste App Password here when ready.")

st.markdown("### Recipients")
col1, col2 = st.columns(2)
with col1:
    recipients_text = st.text_area("Paste recipients (comma, semicolon or newline separated)", height=120)
with col2:
    uploaded_csv = st.file_uploader("Or upload CSV with recipient emails (first column or 'email' column)", type=['csv'], accept_multiple_files=False)

recipients = []
if uploaded_csv:
    try:
        uploaded_csv.seek(0)
        recipients = parse_recipients_from_csv(uploaded_csv)
        st.success(f"Parsed {len(recipients)} recipients from CSV.")
    except Exception as e:
        st.error(f"Failed to parse CSV: {e}")

if recipients_text and not uploaded_csv:
    recipients = parse_recipients_from_text(recipients_text)
    st.success(f"Parsed {len(recipients)} recipients from text input.")

if not recipients:
    st.warning("No recipients provided yet.")

st.markdown("### Message")
subject = st.text_input("Subject", value="Welcome to AI4HEALTH club meeting")
body_text = st.text_area("Plain text body", height=200, value="We are pleased to have you as our founding members...")
use_html = st.checkbox("Use HTML body", value=False)
body_html = ""
if use_html:
    body_html = st.text_area("HTML body", height=200, value="<p>We are pleased to have you as our founding members...</p>")

st.markdown("### Attachments")
uploaded_files = st.file_uploader("Upload attachments (multiple)", accept_multiple_files=True)

# Prepare attachments as list of (filename, bytes)
attachments = []
for f in uploaded_files:
    try:
        file_bytes = f.read()
        attachments.append((f.name, file_bytes))
    except Exception as e:
        st.warning(f"Failed to read attachment {f.name}: {e}")

st.markdown("---")

col_send1, col_send2 = st.columns([1, 3])
with col_send1:
    send_button = st.button("Send emails")
with col_send2:
    st.caption("Click to start sending. Progress and report will appear below.")

if send_button:
    if not sender_email or not sender_password:
        st.error("Sender email and password are required to send emails.")
    elif not recipients:
        st.error("Provide at least one recipient.")
    else:
        st.info(f"Starting to send {len(recipients)} messages...")
        progress = st.progress(0)
        status_text = st.empty()
        results = []
        # Send in batches if desired: this simple app sends sequentially
        for i in range(0, len(recipients)):
            # Send one-by-one using the bulk function but for better progress we call per-chunk
            # Here we call send_bulk_emails with the remaining single recipient to reuse code
            single_result = send_bulk_emails(
                smtp_host=smtp_host,
                smtp_port=int(smtp_port),
                sender=sender_email,
                password=sender_password,
                recipients=[recipients[i]],
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                use_ssl=use_ssl,
            )
            results.extend(single_result)
            progress.progress(int((i + 1) / len(recipients) * 100))
            status_text.text(f"Sent {i + 1}/{len(recipients)}")
        # Summarize
        sent = [r for r in results if r['status'] == 'sent']
        failed = [r for r in results if r['status'] != 'sent']
        st.success(f"Finished. Sent: {len(sent)}. Failed: {len(failed)}.")
        if failed:
            st.error("Some messages failed. See report below.")

        # Show table and offer CSV download
        report_df = pd.DataFrame(results)
        st.dataframe(report_df)

        csv_buf = StringIO()
        report_df.to_csv(csv_buf, index=False)
        st.download_button("Download report as CSV", data=csv_buf.getvalue(), file_name="send_report.csv", mime="text/csv")
