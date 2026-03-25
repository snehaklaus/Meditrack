from celery import shared_task
import requests
from django.conf import settings

@shared_task
def send_email_task(to_email, subject, html_content):
    url = "https://api.brevo.com/v3/smtp/email"

    payload = {
        "sender": {"email": settings.DEFAULT_FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code >= 300:
        print("❌ Brevo error:", response.text)