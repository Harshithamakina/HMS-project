"""
Notification service — Django side.
Calls the serverless email function via HTTP.
Logs every attempt in NotificationLog so failures are visible,
not silent. This solves the real-world problem where email
delivery fails and nobody knows.
"""
import requests
import json
from django.conf import settings


def send_notification(user_email: str, event_type: str, payload: dict):
    """
    Sends email via serverless function.
    Never raises — always logs success or failure.
    Booking should succeed even if email fails.
    """
    from bookings.models import NotificationLog

    log = NotificationLog.objects.create(
        user_email=user_email,
        event_type=event_type,
        payload=payload,
        status='PENDING',
    )

    try:
        response = requests.post(
            settings.EMAIL_SERVICE_URL,
            json={
                'event_type': event_type,
                'email': user_email,
                'payload': payload,
            },
            timeout=5,  # Don't block the user request for more than 5s
        )

        if response.status_code == 200:
            log.status = 'SENT'
        else:
            log.status = 'FAILED'
            log.error_message = f'HTTP {response.status_code}: {response.text[:200]}'

    except requests.exceptions.ConnectionError:
        log.status = 'FAILED'
        log.error_message = 'Email service unreachable. Is serverless-offline running?'
    except requests.exceptions.Timeout:
        log.status = 'FAILED'
        log.error_message = 'Email service timed out after 5s.'
    except Exception as e:
        log.status = 'FAILED'
        log.error_message = str(e)[:500]
    finally:
        log.save()

    return log
