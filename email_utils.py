import os
import requests

def send_email(to_email, subject, content):
    """Send email via SendGrid API"""
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {os.getenv('SENDGRID_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = {
        "personalization":[{
            "to":[{"email": to_email}],
            "subject": subject
        }],
        "from":{"email": os.getenv("MAIL_DEFAULT_SENDER")},
        "content":[{"type": "text/plain", "value": content}]
    }

    r = requests.post(url, headers=headers, json=data)
    return r.status_code == 202