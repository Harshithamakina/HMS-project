"""
Serverless email function.
Handles two event types:
  - SIGNUP_WELCOME: sent when doctor or patient creates an account
  - BOOKING_CONFIRMATION: sent when a booking is confirmed
  - BOOKING_CANCELLATION: sent when a booking is cancelled

Design decision: single endpoint with event_type routing, not
separate endpoints per event. Easier to extend, single failure
point to monitor, consistent logging.
"""
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(event, context):
    """Main Lambda/serverless-offline handler."""
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        return _response(400, {'error': 'Invalid JSON body'})

    event_type = body.get('event_type')
    email = body.get('email')
    payload = body.get('payload', {})

    if not event_type or not email:
        return _response(400, {'error': 'event_type and email are required'})

    # Route to correct email template
    handlers = {
        'SIGNUP_WELCOME': _signup_welcome,
        'BOOKING_CONFIRMATION': _booking_confirmation,
        'BOOKING_CANCELLATION': _booking_cancellation,
    }

    handler_fn = handlers.get(event_type)
    if not handler_fn:
        return _response(400, {'error': f'Unknown event_type: {event_type}'})

    subject, html_body = handler_fn(payload)

    success = _send_smtp(to_email=email, subject=subject, html_body=html_body)

    if success:
        return _response(200, {'message': f'{event_type} email sent to {email}'})
    else:
        return _response(500, {'error': 'SMTP delivery failed'})


def _signup_welcome(payload):
    name = payload.get('name', 'there')
    role = payload.get('role', 'User')
    subject = 'Welcome to MediBook — Your account is ready'
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a5276;">Welcome to MediBook, {name}!</h2>
        <p>Your <strong>{role}</strong> account has been created successfully.</p>
        <p>You can now log in and {'manage your availability slots' if role == 'Doctor' else 'book appointments with doctors'}.</p>
        <hr style="border: 1px solid #eee;">
        <p style="color: #888; font-size: 12px;">Hospital Management System</p>
    </div>
    """
    return subject, html


def _booking_confirmation(payload):
    patient_name = payload.get('patient_name', 'Patient')
    doctor_name = payload.get('doctor_name', 'Doctor')
    date = payload.get('date', '')
    start_time = payload.get('start_time', '')
    end_time = payload.get('end_time', '')
    subject = f'Appointment Confirmed — {date} at {start_time}'
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a5276;">Appointment Confirmed</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr><td style="padding: 8px; font-weight: bold;">Patient</td><td style="padding: 8px;">{patient_name}</td></tr>
            <tr style="background: #f8f9fa;"><td style="padding: 8px; font-weight: bold;">Doctor</td><td style="padding: 8px;">{doctor_name}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold;">Date</td><td style="padding: 8px;">{date}</td></tr>
            <tr style="background: #f8f9fa;"><td style="padding: 8px; font-weight: bold;">Time</td><td style="padding: 8px;">{start_time} – {end_time}</td></tr>
        </table>
        <p style="color: #27ae60; font-weight: bold;">A calendar event has been added to your Google Calendar.</p>
        <hr style="border: 1px solid #eee;">
        <p style="color: #888; font-size: 12px;">Hospital Management System</p>
    </div>
    """
    return subject, html


def _booking_cancellation(payload):
    patient_name = payload.get('patient_name', 'Patient')
    doctor_name = payload.get('doctor_name', 'Doctor')
    date = payload.get('date', '')
    subject = f'Appointment Cancelled — {date}'
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #c0392b;">Appointment Cancelled</h2>
        <p>The appointment for <strong>{patient_name}</strong> with <strong>{doctor_name}</strong> on <strong>{date}</strong> has been cancelled.</p>
        <p>The slot is now available for other patients.</p>
        <hr style="border: 1px solid #eee;">
        <p style="color: #888; font-size: 12px;">Hospital Management System</p>
    </div>
    """
    return subject, html


def _send_smtp(to_email, subject, html_body):
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    from_email = os.environ.get('FROM_EMAIL', smtp_user)

    if not smtp_user or not smtp_password:
        # In local dev without SMTP config, just log and return success
        print(f'[EMAIL MOCK] To: {to_email} | Subject: {subject}')
        return True

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f'[EMAIL ERROR] {str(e)}')
        return False


def _response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
        },
        'body': json.dumps(body),
    }
