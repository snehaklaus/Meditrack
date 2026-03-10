# MediTrack API

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Redis](https://img.shields.io/badge/Redis-Queue-red)
![Celery](https://img.shields.io/badge/Celery-Async%20Tasks-brightgreen)
![AI](https://img.shields.io/badge/AI-Gemini-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)
[![Live Demo](https://img.shields.io/badge/Live-Demo-success)](https://meditrack7.vercel.app)
[![API Docs](https://img.shields.io/badge/API-Docs-blue)](https://meditrack.up.railway.app/api/docs/)

A production-ready REST API for managing medications, tracking symptoms, and getting AI-powered health insights with automated smart reminders and weekly health digest emails.

**API Docs:** [meditrack.up.railway.app/api/docs/ ](https://meditrack.up.railway.app/api/docs/) 
<img width="1363" height="716" alt="image" src="https://github.com/user-attachments/assets/f2e25f81-18cf-4be5-adb9-e1f2c4cb4902" />

**Frontend:** [meditrack7.vercel.app](https://meditrack7.vercel.app/)
<img width="1282" height="717" alt="image" src="https://github.com/user-attachments/assets/1e323bb0-ffb2-44e5-98f5-3d6e74d818fc" />

---

## 🚀 Features

**Authentication & Access**
- JWT Authentication — Secure token-based auth with access & refresh tokens
- Google OAuth 2.0 Integration — One-click sign-in/sign-up with Google accounts
- **Editable User Profiles** — Users can update username, email, phone, and date of birth with validation
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
- **Profile Update Validation** — Username/email uniqueness checks, phone format validation, date of birth logic
- OAuth Token Verification — Server-side Google token validation with clock skew tolerance
- Auto-Generated API Docs — Swagger UI powered by drf-spectacular

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 4.2 + Django REST Framework |
| Authentication | djangorestframework-simplejwt + Google OAuth 2.0 |
| OAuth Library | google-auth + google-auth-httplib2 |
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

# Google OAuth 2.0
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret

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
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

> **Note:** For local development, `EMAIL_BACKEND` defaults to `console` — emails print to terminal instead of sending. No SMTP setup needed locally.

> **Gmail App Password:** Go to myaccount.google.com → Security → App Passwords → create one named "MediTrack". Use this 16-character password, not your regular Gmail password.

---

## 🔐 Google OAuth Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable **Google+ API**

### 2. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client ID**
3. Configure consent screen if prompted (External, add app name)
4. Application type: **Web application**
5. Add **Authorized JavaScript origins:**
   - `http://localhost:5173` (development)
   - `https://meditrack7.vercel.app` (production)
6. Add **Authorized redirect URIs:**
   - `http://localhost:5173`
   - `https://meditrack7.vercel.app`
7. Copy **Client ID** and **Client Secret**
8. Add to `.env` file

### 3. OAuth Flow

**New User Registration:**
1. Frontend sends Google credential token to `/api/auth/google/`
2. Backend verifies token with Google's API
3. Returns `is_new_user: true` with email and name
4. Frontend collects username and role
5. Frontend sends to `/api/auth/google/complete/`
6. Backend creates user account (no password)
7. Returns JWT tokens → user logged in

**Existing User Login:**
1. Frontend sends Google credential token to `/api/auth/google/`
2. Backend verifies token and finds existing user by email
3. Returns JWT tokens → user logged in directly

---

## 📡 API Endpoints

### Authentication (`/api/auth/`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/auth/register/` | Register a new user | No |
| POST | `/api/auth/login/` | Get JWT access + refresh tokens | No |
| POST | `/api/auth/google/` | **Google OAuth login/signup** | No |
| POST | `/api/auth/google/complete/` | **Complete Google OAuth registration** | No |
| POST | `/api/auth/token/refresh/` | Refresh access token | No |
| GET/PUT/PATCH | `/api/auth/profile/` | **View or update your profile** (includes email_digest_enabled) | Yes |
| GET | `/api/auth/patients/` | List assigned patients (doctors only) | Yes |
| PUT | `/api/auth/assign-doctor/` | Assign a doctor to your account (patients only) | Yes |

**Google OAuth Endpoints:**

**`POST /api/auth/google/`**
- Validates Google credential token
- Returns JWT tokens for existing users
- Returns user data for new users (requires username selection)

Request body:
```json
{
  "token": "google_credential_token"
}
```

Response (existing user):
```json
{
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token",
  "is_new_user": false
}
```

Response (new user):
```json
{
  "is_new_user": true,
  "email": "user@gmail.com",
  "name": "John Doe",
  "google_id": "google_user_id"
}
```

**`POST /api/auth/google/complete/`**
- Completes registration for new Google users
- Creates account without password

Request body:
```json
{
  "email": "user@gmail.com",
  "username": "john_doe",
  "google_id": "google_user_id",
  "name": "John Doe",
  "role": "patient"
}
```

Response:
```json
{
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token",
  "is_new_user": false
}
```

---

## ⚙️ Editable User Profile

The `/api/auth/profile/` endpoint now supports full profile updates with comprehensive validation.

### PATCH `/api/auth/profile/`

**Request Body:**
```json
{
  "username": "new_username",
  "email": "new@email.com",
  "phone": "+1 555-123-4567",
  "date_of_birth": "1990-01-15",
  "email_digest_enabled": true
}
```

**Success Response (200):**
```json
{
  "id": 1,
  "username": "new_username",
  "email": "new@email.com",
  "role": "patient",
  "phone": "+1 555-123-4567",
  "date_of_birth": "1990-01-15",
  "email_digest_enabled": true
}
```

**Validation Error Response (400):**
```json
{
  "username": ["Username already taken"],
  "email": ["Email already taken"],
  "phone": ["Phone number should contain only digits, spaces, and +()-"],
  "date_of_birth": ["Date of birth cannot be in the future"]
}
```

### Validation Rules

The `UserSerializer` implements the following validations:

| Field | Validation |
|-------|-----------|
| **username** | Required, must be unique (excluding current user) |
| **email** | Required, valid email format, must be unique (excluding current user) |
| **phone** | Optional, 7-15 digits, allows spaces and +()- characters |
| **date_of_birth** | Optional, must be in the past, maximum 150 years ago |
| **role** | Read-only field (cannot be changed after registration) |
| **email_digest_enabled** | Boolean toggle for weekly email digest |

### Serializer Implementation

```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone', 'date_of_birth', 'email_digest_enabled']
        read_only_fields = ['id', 'role']
    
    def validate_username(self, value):
        """Ensure username is unique when updating"""
        user = self.instance
        if user and User.objects.filter(username=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('Username already taken')
        return value
    
    def validate_email(self, value):
        """Ensure email is unique when updating"""
        user = self.instance
        if user and User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('Email already taken')
        return value
    
    def validate_phone(self, value):
        """Basic phone validation"""
        if value and len(value.strip()) > 0:
            cleaned = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
            if not cleaned.isdigit():
                raise serializers.ValidationError('Phone number should contain only digits, spaces, and +()-')
            if len(cleaned) < 7 or len(cleaned) > 15:
                raise serializers.ValidationError('Phone number should be between 7 and 15 digits')
        return value
    
    def validate_date_of_birth(self, value):
        """Ensure date of birth is valid"""
        if value:
            from datetime import date
            today = date.today()
            if value > today:
                raise serializers.ValidationError('Date of birth cannot be in the future')
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age > 150:
                raise serializers.ValidationError('Invalid date of birth')
        return value
```

### Security Features

- **Object-Level Permissions:** Users can only edit their own profile (enforced by `get_object()` in view)
- **Role Protection:** User role is read-only and cannot be changed after registration
- **Unique Constraints:** Username and email uniqueness checked at database level
- **Input Validation:** Both serializer-level and database-level validation
- **SQL Injection Prevention:** Django ORM protects against SQL injection
- **XSS Prevention:** HTML tags stripped from text inputs

---

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
- **Google OAuth 2.0** with server-side token verification and clock skew tolerance
- **OAuth users** have unusable passwords (cannot login with traditional credentials)
- **Profile update security:**
  - Users can only edit their own profile
  - Role field is read-only
  - Username/email uniqueness enforced
  - Input validation on all fields
- Role-based permissions — patients and doctors only access appropriate data
- Object-level permissions — users can only access their own records
- Rate limiting — registration capped at 5/hour, login at 10/hour per IP
- Input sanitization — HTML tags blocked on all text fields to prevent XSS
- CSRF trusted origins configured for production domain
- HTTPS enforced in production with HSTS headers
- Cross-Origin-Opener-Policy configured for OAuth popup flows
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
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
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

Interactive Swagger UI is available at `/api/docs/`. Authenticate using a JWT token from `/api/auth/login/` or `/api/auth/google/`.

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
├── accounts/             # Custom user model, auth, Google OAuth, profile updates, doctor-patient permissions
├── medications/          # Medication CRUD, reminders, adherence tracking
├── symptoms/             # Symptom logging, AI insights, dashboard, mood tracking, PDF reports
├── core/                 # Shared validators and middleware
├── requirements.txt
├── Procfile
├── runtime.txt
└── .env.example
```

---

## 🔧 Troubleshooting

**Google OAuth Errors:**

**"Invalid Google token"**
- Verify `GOOGLE_CLIENT_ID` in Railway environment variables
- Check that Google+ API is enabled in Google Cloud Console
- Ensure authorized origins include your frontend URL

**"Token used too early" (clock skew error)**
- Already handled with 10-second clock skew tolerance in token verification
- If persists, check server time is synchronized

**"Origin not allowed"**
- Verify frontend URL is in Google Console authorized JavaScript origins
- Wait 5-10 minutes for Google's changes to propagate
- Check CORS settings include frontend URL

**Profile Update Errors:**

**"Username already taken"**
- Username uniqueness is checked excluding the current user
- Another user has this username
- Try a different username

**"Email already taken"**
- Email uniqueness is checked excluding the current user
- This email is already registered to another account
- Use a different email address

**"Phone number validation error"**
- Phone should be 7-15 digits
- Allowed characters: digits, spaces, +, (, ), -
- Example valid format: `+1 555-123-4567`

**"Date of birth cannot be in the future"**
- Ensure the date is in the past
- Check date format is correct (YYYY-MM-DD)

**Email not working:**
- For Gmail, use an **App Password**, not your regular password
- In Railway, ensure all email env vars are set correctly
- Check Gmail hasn't blocked sign-in attempts

---

## 🔮 Roadmap

- [ ] WebSocket support for real-time push notifications (Django Channels)
- [ ] Medication interaction checker via Gemini AI
- [ ] Predictive analytics and trend forecasting
- [ ] Unit tests and CI/CD pipeline
- [ ] Doctor dashboard with patient management UI
- [ ] OAuth support for additional providers (Apple, Facebook)
- [ ] Two-factor authentication
- [ ] Audit logging for profile changes
- [x] **Editable user profiles with validation**
- [x] **Dark mode support in frontend**
- [x] Google OAuth 2.0 integration
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

---

## 📋 Changelog

### Version 2.2 (Latest)
- **Editable User Profiles**
  - Users can update username, email, phone, date of birth
  - Comprehensive validation with specific error messages
  - Username uniqueness check (excluding current user)
  - Email uniqueness check (excluding current user)
  - Phone format validation (7-15 digits, +()- allowed)
  - Date of birth validation (must be in past, max 150 years old)
  - Role field protected as read-only
  - Email digest toggle support
- **Enhanced Security**
  - Object-level permissions for profile updates
  - Input validation on all editable fields
  - SQL injection and XSS protection

### Version 2.1
- Google OAuth 2.0 integration with server-side token verification
- Clock skew tolerance for OAuth tokens
- Separate registration completion endpoint for new Google users

### Version 2.0
- Weekly email digest with toggle preference
- PDF health report export
- Medication adherence tracking
- Interactive dashboard charts

### Version 1.0
- Initial release with medications, symptoms, AI insights

---

## 🎯 Google OAuth Implementation Details

**Technical Flow:**
1. Frontend receives Google credential token from OAuth popup
2. Token sent to `/api/auth/google/` endpoint
3. Backend verifies token using `google.oauth2.id_token.verify_oauth2_token()`
4. Token validation includes clock skew tolerance (10 seconds)
5. User lookup by email from verified token
6. New users complete registration via `/api/auth/google/complete/`
7. OAuth users have `set_unusable_password()` - cannot use traditional login

**Security Features:**
- Server-side token verification (never trust client-side validation)
- Google's public key infrastructure used for verification
- Email uniqueness enforced at database level
- CORS properly configured for OAuth popup flow
- Cross-Origin-Opener-Policy set to allow popup communication

---

## 🔐 Profile Update Implementation Details

**Validation Flow:**
1. Frontend sends PATCH request to `/api/auth/profile/`
2. DRF validates request data format
3. `UserSerializer` runs field-level validators
4. Uniqueness checks exclude current user's ID
5. All validations pass → database update
6. Updated user object returned to frontend

**Database Level:**
- `username` and `email` have unique constraints
- Database will reject duplicates even if validation is bypassed
- Foreign key constraint on `assigned_doctor`

**Frontend Integration:**
- Real-time validation feedback
- Inline error messages
- Success toast on update
- Automatic form reset on cancel
