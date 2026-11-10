import smtplib
from email.message import EmailMessage


def send_mail(settings, email, subject, body, pdf=None, message_id=None):
    if settings.provider_mode == "test":
        return "test-mail"
    if settings.provider_mode != "live":
        raise ValueError("메일 발송 연결 설정이 필요합니다")
    message = EmailMessage()
    message["From"], message["To"], message["Subject"] = settings.mail_from, email, subject
    if message_id:
        message["Message-ID"] = f"<{message_id}@meeting-agent.local>"
    message.set_content(body)
    if pdf and len(pdf) < 8 * 1024 * 1024:
        message.add_attachment(pdf, maintype="application", subtype="pdf", filename="회의록.pdf")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
    return str(message["Message-ID"] or "smtp-accepted")
