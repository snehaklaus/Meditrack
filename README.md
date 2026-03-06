# MediTrack API

A production-ready REST API for managing medications, tracking symptoms, and getting AI-powered health insights with automated smart reminders and weekly health digest emails.

**Live Demo:** meditrack.up.railway.app  
**API Docs:** meditrack.up.railway.app/api/docs/  
**Frontend:** meditrack7.vercel.app

---

## 🚀 Features

**Authentication & Access**
- JWT Authentication — Secure token-based auth with access & refresh tokens
- Role-Based Access Control — Separate Patient and Doctor roles with distinct permissions
- Doctor-Patient Relationships — Doctors can be assigned to patients and view their data

**Health Tracking**
- Medication Management — Full CRUD with frequency scheduling, custom schedules, and active/upcoming filters
- Symptom Logging — Track daily symptoms with 1-10 severity ratings and medication correlations
- Mood Tracking — Daily mood logs (1-5 scale) with trend analysis
- Medication Adherence — Track reminder history and calculate adherence rates

**AI & Insights**
- AI Health Insights — Google Gemini-powered analysis of symptom patterns and trends
- Data Visualization — Chart.js-ready dashboard endpoints for symptom trends and mood tracking

**Emails & Reports**
- PDF Health Reports — Export a full health report as a downloadable PDF including medications, symptoms, mood summary and AI insights
- Weekly Email Digest — Automated HTML email every Sunday with health summary, mood trends, adherence rate and AI insights
- HTML Medication Reminders — Styled branded reminder emails sent automatically based on medication frequency
- Email Preferences — Patients can toggle weekly digest on/off from their profile

**Security & Quality**
- Rate Limiting — Brute-force protection on auth endpoints
- Input Sanitization — XSS prevention via HTML tag validation on all user inputs
- Auto-Generated API Docs — Swagger UI powered by drf-spectacular

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 4.2 + Django REST Framework |
| Authentication | djangorestframework-simplejwt |
| Database | PostgreSQL (Railway) |
| Task Queue | Celery 5.3 + Redis |
| AI | Google Gemini API (gemini-pro) |
| PDF Generation | ReportLab |
| Deployment | Railway |
| Static Files | WhiteNoise |
| API Docs | drf-spectacular (Swagger UI) |
| Rate Limiting | django-ratelimit |

---

## 📦 Local Installation

```bash
# Clone the repository
git clone https://github.com/sneh1117/MediTrack.git
cd meditrack

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
python manage.py migrate

# Create an admin superuser
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

To run Celery (required for reminders and digest emails), open two additional terminals:

```bash
# Terminal 2 — Celery worker
celery -A config worker --loglevel=info --concurrency=1

# Terminal 3 — Celery beat scheduler
celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
DEBUG=True
SECRET_KEY=your-strong-secret-key

# PostgreSQL Database
DB_NAME=meditrack
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=5432

# Google Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Redis (Celery)
REDIS_URL=redis://localhost:6379/0

# Email (production — uses Gmail SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
DEFAULT_FROM_EMAIL=MediTrack <your_email@gmail.com>

# CORS
CORS_ORIGINS=http://localhost:3000
```

> **Note:** For local development, `EMAIL_BACKEND` defaults to `console` — emails print to terminal instead of sending. No SMTP setup needed locally.

> **Gmail App Password:** Go to myaccount.google.com → Security → App Passwords → create one named "MediTrack". Use this 16-character password, not your regular Gmail password.

---

## 📡 API Endpoints

### Authentication (`/api/auth/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register/` | Register a new user | No |
| POST | `/api/auth/login/` | Get JWT access + refresh tokens | No |
| POST | `/api/auth/token/refresh/` | Refresh access token | No |
| GET/PUT/PATCH | `/api/auth/profile/` | View or update your profile (includes email_digest_enabled) | Yes |
| GET | `/api/auth/patients/` | List assigned patients (doctors only) | Yes |
| PUT | `/api/auth/assign-doctor/` | Assign a doctor to your account (patients only) | Yes |

### Medications (`/api/medications/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/medications/` | List all or create a medication |
| GET/PUT/DELETE | `/api/medications/{id}/` | Retrieve, update, or delete a medication |
| GET | `/api/medications/current/` | Currently active medications |
| GET | `/api/medications/upcoming/` | Medications starting in the future |
| GET | `/api/medications/adherence/` | Adherence rate and reminder history |

Frequency options: `once_daily`, `twice_daily`, `three_times_daily`, `as_needed`, `custom`

### Symptoms (`/api/symptoms/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/symptoms/` | List all or log a new symptom |
| GET/PUT/DELETE | `/api/symptoms/{id}/` | Retrieve, update, or delete a symptom |
| GET | `/api/symptoms/last_seven_days/` | Symptoms from the last 7 days |
| GET | `/api/symptoms/summary/` | Aggregated summary (avg severity, count, last occurrence) |
| GET | `/api/symptoms/by_medication/?medication_id={id}` | Symptoms linked to a specific medication |
| GET | `/api/symptoms/ai_insights/?days=7` | AI-powered health insight analysis |

### Dashboard, Moods & Reports (`/api/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/?days=30` | Chart.js-ready symptom trends, common symptoms, and stats |
| GET/POST | `/api/moods/` | List all or create a daily mood log |
| GET/PUT/DELETE | `/api/moods/{id}/` | Retrieve, update, or delete a mood log |
| GET | `/api/moods/trends/?days=30` | Mood trend data formatted for Chart.js |
| GET | `/api/reports/export/?days=30` | Download PDF health report | 

---

## 📄 PDF Health Reports

The `/api/reports/export/` endpoint generates a downloadable PDF containing:

- Branded header with username and date range
- Summary stats — active medications, total symptoms, symptoms this period
- Active medications table
- Symptom log with green/yellow/red severity color coding
- Mood summary — average, best day, worst day
- Last cached AI insight snapshot

Supports `?days=7`, `?days=30`, or `?days=90` query parameter. Available to patients only.

---

## 🤖 AI Insights

The `/api/symptoms/ai_insights/` endpoint uses Google Gemini to analyze your symptom history and return:

- Pattern identification — recurring symptoms and severity trends
- Medication correlations — links between symptoms and medications you're taking
- Gentle recommendations — when to seek medical advice and lifestyle tips

Responses are cached per user to avoid repeated API calls.

> ⚠️ MediTrack AI provides observations only — it does not diagnose medical conditions.

---

## ⏰ Automated Emails

### Medication Reminders
Celery Beat checks for due medication reminders every hour. Styled HTML emails are sent based on frequency:

| Frequency | Reminder Times (UTC) |
|-----------|---------------------|
| Once Daily | 08:00 |
| Twice Daily | 08:00, 20:00 |
| Three Times Daily | 08:00, 14:00, 20:00 |
| Custom | Based on your custom schedule |

### Weekly Health Digest
Every Sunday at 09:00 UTC, patients with `email_digest_enabled=True` receive an HTML digest email containing:
- Symptoms logged that week
- Top symptom and average severity
- Average mood score
- Active medication count
- Medication adherence rate
- Latest AI health insight

Patients can toggle this on/off from their profile settings.

---

## 🔒 Security

- JWT authentication with configurable token lifetimes (1hr access, 7 day refresh)
- Role-based permissions — patients and doctors only access appropriate data
- Object-level permissions — users can only access their own records
- Rate limiting — registration capped at 5/hour, login at 10/hour per IP
- Input sanitization — HTML tags blocked on all text fields to prevent XSS
- CSRF trusted origins configured for production domain
- HTTPS enforced in production with HSTS headers
- Environment-based configuration — no secrets in codebase

---

## 📊 Dashboard Response Format

The `/api/dashboard/` endpoint returns data pre-formatted for Chart.js:

```json
{
  "symptom_trends": {
    "labels": ["2026-02-20", "2026-02-21"],
    "datasets": [
      { "label": "Average Severity", "data": [4.5, 6.0] },
      { "label": "Symptom Count", "data": [2, 3] }
    ]
  },
  "common_symptoms": {
    "labels": ["Headache", "Nausea"],
    "datasets": [{ "label": "Frequency", "data": [12, 7] }]
  },
  "stats": {
    "active_medications": 3,
    "total_symptoms_logged": 47,
    "symptoms_last_7_days": 9
  }
}
```

---

## 🚀 Deployment (Railway)

This project is deployed on Railway with three separate services:

| Service | Start Command |
|---------|--------------|
| web | `python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT --log-file -` |
| worker | `celery -A config worker --loglevel=info --concurrency=1` |
| beat | `celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler` |

**Required Railway services:**
- Web service (this repo)
- PostgreSQL database
- Redis database

**Required environment variables in Railway dashboard:**

```
DEBUG=False
SECRET_KEY=
ALLOWED_HOSTS=your-app.up.railway.app
GEMINI_API_KEY=
CORS_ORIGINS=https://your-frontend.com
CSRF_TRUSTED_ORIGINS=https://your-app.up.railway.app
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_gmail_app_password
DEFAULT_FROM_EMAIL=MediTrack <your_email@gmail.com>
```

`DATABASE_URL` and `REDIS_URL` are injected automatically by Railway.

---

## 📚 API Documentation

Interactive Swagger UI is available at `/api/docs/`. Authenticate using a JWT token from `/api/auth/login/`.

To regenerate the OpenAPI schema locally:
```bash
python manage.py spectacular --color --file schema.yml
```

---

## 🧪 Running Tests

```bash
python manage.py test
```

---

## 📁 Project Structure

```
meditrack/
├── config/               # Django project settings, URLs, Celery config
├── accounts/             # Custom user model, auth, doctor-patient permissions
├── medications/          # Medication CRUD, reminders, adherence tracking
├── symptoms/             # Symptom logging, AI insights, dashboard, mood tracking, PDF reports
├── core/                 # Shared validators and middleware
├── requirements.txt
├── Procfile
├── runtime.txt
└── .env.example
```

---

## 🔮 Roadmap

- [ ] WebSocket support for real-time push notifications (Django Channels)
- [ ] Medication interaction checker via Gemini AI
- [ ] Predictive analytics and trend forecasting
- [ ] Unit tests and CI/CD pipeline
- [ ] Doctor dashboard with patient management UI
- [x] PDF export for health reports
- [x] HTML email templates for reminders and digests
- [x] Weekly health digest email
- [x] Email preferences per user
- [x] React/Next.js frontend dashboard

---

## 📝 License

MIT License — feel free to use, modify, and distribute.

---

## 👩‍💻 Author

**Sneha**  
GitHub: [sneh1117](https://github.com/sneh1117)
