# Hospital Management System (HMS)

A mini hospital management system built for doctor availability management and patient appointment booking, with a separate serverless email notification service.

---

## Setup and Run

### Prerequisites
- Python 3.11+
- PostgreSQL installed and running locally
- Node.js 18+ (for serverless-offline)

### 1. Clone and set up the Django app

```bash
git clone <your-repo-url>
cd hms-project

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `DB_NAME`, `DB_USER`, `DB_PASSWORD` — your local PostgreSQL credentials
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — from Google Cloud Console (see Google Calendar setup below)
- `SMTP_USER`, `SMTP_PASSWORD` — Gmail address + App Password (Settings → Security → App Passwords)

### 3. Create the PostgreSQL database

```bash
psql -U postgres -c "CREATE DATABASE hms_db;"
```

### 4. Run migrations and create superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Start the Django server

```bash
python manage.py runserver
```

App runs at: http://localhost:8000

### 6. Start the serverless email service (separate terminal)

```bash
cd email-service
npm install
npx serverless offline
```

Email service runs at: http://localhost:3000

### Google Calendar Setup (optional for local demo)

1. Go to https://console.cloud.google.com
2. Create a project → Enable Google Calendar API
3. Create OAuth 2.0 credentials (Web Application type)
4. Add `http://localhost:8000/accounts/google/callback/` as an authorized redirect URI
5. Copy Client ID and Secret into `.env`

If Google credentials are not configured, the system still works fully — calendar events are skipped and the failure is logged in `CalendarEventLog`.

---

## System Architecture

### How the two services connect

```
Browser
  │
  ├── Django (port 8000)
  │     ├── accounts/     ← auth, Google OAuth2
  │     ├── doctors/      ← availability slots
  │     ├── patients/     ← browse doctors
  │     ├── bookings/     ← book/cancel, race condition handling
  │     └── notifications/← calls email service via HTTP POST
  │
  └── Serverless Email (port 3000)
        └── handler.py    ← receives event_type + payload, sends SMTP email
```

Django never imports from the email service. It makes an HTTP POST to `http://localhost:3000/dev/send-email` with a JSON payload. This keeps the two services fully decoupled — the email service could be replaced or redeployed without touching Django.

### Data model decisions

**Custom User model with role field** — Django's AbstractUser is extended with a `role` field (DOCTOR | PATIENT). Separate `DoctorProfile` and `PatientProfile` models extend it via OneToOne. This keeps authentication in one place while allowing role-specific data in dedicated tables. Role-based access is enforced via decorators (`@doctor_required`, `@patient_required`) at the view level — not just in templates.

**OneToOne between Booking and AvailabilitySlot** — enforced at the database level. Even if the application logic fails, the database constraint prevents two bookings for the same slot from existing simultaneously.

**CalendarEventLog** — every booking has a corresponding `CalendarEventLog` row tracking whether the doctor and patient calendar events were successfully created. When Google tokens expire or the Calendar API is down, the booking still succeeds but the log row shows `doctor_event_created=False`. This makes silent failures visible and queryable, rather than invisible.

**NotificationLog** — every email attempt (success or failure) is recorded with `status`, `retry_count`, and `error_message`. If the serverless function is down when a booking is confirmed, the failure appears here rather than disappearing silently.

### How role-based access is enforced

Two decorators in `accounts/decorators.py`:

```python
@doctor_required   # applied to all doctor views
@patient_required  # applied to all patient views
```

These check `request.user.role` on every request. A patient cannot reach any doctor URL — they receive a redirect with an error message. This is enforced in Python, not in templates, so it cannot be bypassed by a user who guesses a URL.

### Google Calendar integration

On booking confirmation, `bookings/calendar_service.py` creates two events:
- Doctor's calendar: `Appointment with <PatientName>`
- Patient's calendar: `Appointment with Dr. <DoctorName>`

Tokens are stored per user in the `User` model. If a token is expired, it is refreshed automatically before the API call using the stored `refresh_token`. If the user has not connected Google Calendar, the event creation is skipped and logged — the booking is not affected.

---

## The Design Decision

### Race condition in slot booking: pessimistic vs optimistic locking

**The problem:** Two patients open the booking page for the same slot at the same time. Both see it as available. Both click "Book". Without a locking strategy, both requests pass the availability check and two bookings are created for the same slot. The doctor now has two patients at 10:00 AM.

**Option 1 — Optimistic locking:** Add a `version` field to `AvailabilitySlot`. When booking, read the version, proceed with the booking, and update only if the version hasn't changed since you read it. If it has changed, return an error and ask the patient to retry.

**Option 2 — Pessimistic locking:** Use `select_for_update()` inside a `transaction.atomic()` block. The database locks the row when Patient A's request reads it. Patient B's request waits at the database level. When Patient A commits, Patient B reads the updated row, sees `is_available=False`, and returns a clean error.

**Why I chose pessimistic locking:**

In a booking system, contention is highest exactly when it matters most — a popular doctor's first available morning slot. That is precisely when optimistic locking fails most often, forcing patients to retry at peak frustration points.

The cost of a failed optimistic lock is a confusing user experience: the patient sees a booking form, submits it, and gets an error asking them to try again. For a medical appointment, that is poor UX. The cost of a pessimistic lock is holding a database row lock for the duration of the booking transaction — typically under 50 milliseconds. That tradeoff is straightforward: accept a trivial performance cost to give users a clean, unambiguous result.

The `version` field is retained in the schema even though it is not used for locking — it makes the concurrency intent visible to anyone reading the models, and it enables optimistic locking on specific operations in the future if needed.

---

## Limitations

**No transaction guarantee across booking, calendar, and email**

The current flow confirms the booking in the database, then calls Google Calendar and the email service as separate steps outside the transaction. If Django crashes after the booking is saved but before the email sends, the patient has a confirmed booking with no confirmation email. In production this needs an event-driven approach: save the booking, publish a `booking_confirmed` event to a queue (Celery + Redis), and let a background worker handle calendar and email with retry logic. The `NotificationLog` and `CalendarEventLog` tables were built to make this upgrade path straightforward.

**Google OAuth2 token revocation is not handled**

If a doctor or patient revokes Google Calendar access from their Google Account settings, the stored token becomes invalid. The next booking attempt will fail to create a calendar event, log the error, and continue. There is no mechanism to detect revocation proactively or notify the user that their calendar connection has been broken. In production, the system should detect 401 responses from the Calendar API and prompt the user to reconnect.

**No doctor-side cancellation**

Doctors cannot cancel their own slots once published. In practice, doctors call in sick, go on leave, or have emergencies. Without a doctor-side cancellation flow that releases all affected slots and notifies booked patients, those slots remain permanently blocked. The `Booking.status` field supports a `CANCELLED` state and the slot release logic exists in the patient cancellation flow — extending this to doctor-initiated cancellation is the first thing I would build after this MVP.

**No-show rate permanently degrades slot availability**

Patient cancellation releases a slot. But if a patient simply does not show up (no-show rate in outpatient settings is typically 15–30%), the slot remains `is_available=False` permanently. Over weeks, this would cause a significant portion of the doctor's theoretical capacity to be phantom-blocked. A production system needs a scheduled job that marks past unconfirmed slots as expired and frees them.

**Gmail SMTP rate limits**

The email service uses Gmail SMTP, which has a 500-email-per-day limit on free accounts. At any meaningful patient volume this would fail silently. Production deployment should use a transactional email provider (SendGrid, AWS SES) with proper SPF/DKIM records — without these, emails from a local SMTP server go to spam and patients never see their confirmations.
