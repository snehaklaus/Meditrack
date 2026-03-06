from celery import shared_task
from django.utils import timezone
from django.db import models
from .models import Medication, MedicationReminder
from django.core.mail import send_mail
from django.conf import settings
from datetime import time,date,timedelta
from django.db.models import Avg,Count


@shared_task
def send_medication_reminders():
    now = timezone.now()
    current_hour = now.hour
    current_time = now.time().replace(second=0, microsecond=0)

    medications = Medication.objects.filter(
        is_active=True,
        start_date__lte=now.date()
    ).filter(
        models.Q(end_date__isnull=True) | models.Q(end_date__gte=now.date())
    ).select_related('user')

    reminders_sent = 0

    for med in medications:

        should_remind = False

        # Frequency rules
        if med.frequency == 'once_daily': # and current_hour == 8:
            should_remind = True

        elif med.frequency == 'twice_daily' and current_hour in [8, 20]:
            should_remind = True

        elif med.frequency == 'three_times_daily' and current_hour in [8, 14, 20]:
            should_remind = True

        elif med.frequency == 'custom' and med.custom_schedule:
            for time_str in med.custom_schedule:
                hour = int(time_str.split(':')[0])
                if current_hour == hour:
                    should_remind = True
                    break

        if not should_remind:
            continue

        # 🔥 Prevent duplicate reminders in same hour
        already_sent = MedicationReminder.objects.filter(
            medication=med,
            sent_at__date=now.date(),
            scheduled_time__hour=current_hour
        ).exists()

        if already_sent:
            continue

        # Send email
        send_reminder_notification.delay(med.id)

        # Save reminder log
        MedicationReminder.objects.create(
            medication=med,
            scheduled_time=current_time
        )

        reminders_sent += 1

    return f"Sent {reminders_sent} medication reminders"


@shared_task
def send_reminder_notification(medication_id):
    try:
        medication = Medication.objects.get(id=medication_id)
        user = medication.user

        if not user.email:
            return f"No email for {user.username}"

        subject = f"💊 Time to take {medication.name}"

        freq_display = medication.frequency.replace('_', ' ').title()

        plain_message = (
            f"Hi {user.username},\n\n"
            f"This is a reminder to take your medication:\n\n"
            f"Medication: {medication.name}\n"
            f"Dosage: {medication.dosage}\n"
            f"Frequency: {freq_display}\n\n"
            f"Stay healthy!\n— MediTrack"
        )

        html_message = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:32px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#2563EB,#0891B2);border-radius:12px 12px 0 0;padding:28px 36px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;">❤️ MediTrack</h1>
            <p style="margin:6px 0 0;color:#BFDBFE;font-size:13px;">Medication Reminder</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="background:#ffffff;padding:28px 36px;">
            <p style="margin:0 0 20px;color:#0F172A;font-size:15px;">
              Hi <strong>{user.username}</strong>, time to take your medication!
            </p>

            <!-- Medication Card -->
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#EFF6FF;border-radius:10px;border:1px solid #BFDBFE;">
              <tr>
                <td style="padding:20px 24px;">
                  <p style="margin:0 0 4px;font-size:11px;color:#2563EB;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">
                    Medication
                  </p>
                  <p style="margin:0 0 16px;font-size:22px;font-weight:700;color:#0F172A;">
                    💊 {medication.name}
                  </p>
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td width="48%" style="background:#ffffff;border-radius:8px;padding:12px;border:1px solid #DBEAFE;">
                        <p style="margin:0;font-size:11px;color:#94A3B8;">DOSAGE</p>
                        <p style="margin:4px 0 0;font-size:15px;font-weight:600;color:#0F172A;">{medication.dosage}</p>
                      </td>
                      <td width="4%"></td>
                      <td width="48%" style="background:#ffffff;border-radius:8px;padding:12px;border:1px solid #DBEAFE;">
                        <p style="margin:0;font-size:11px;color:#94A3B8;">FREQUENCY</p>
                        <p style="margin:4px 0 0;font-size:15px;font-weight:600;color:#0F172A;">{freq_display}</p>
                      </td>
                    </tr>
                  </table>
                  {f'<p style="margin:12px 0 0;font-size:13px;color:#475569;font-style:italic;">{medication.notes}</p>' if medication.notes else ''}
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- CTA -->
        <tr>
          <td style="background:#ffffff;padding:0 36px 28px;text-align:center;">
            <a href="https://meditrack7.vercel.app"
               style="display:inline-block;background:linear-gradient(135deg,#2563EB,#0891B2);
                      color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;
                      padding:12px 28px;border-radius:8px;">
              Open MediTrack →
            </a>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#F8FAFC;border-top:1px solid #E2E8F0;border-radius:0 0 12px 12px;
                     padding:16px 36px;text-align:center;">
            <p style="margin:0;font-size:11px;color:#94A3B8;">
              You're receiving this because you have an active medication reminder on MediTrack.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
        """

        from django.core.mail import EmailMultiAlternatives
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)

        return f"Reminder sent to {user.username}"

    except Medication.DoesNotExist:
        return f"Medication {medication_id} not found"
    
@shared_task
def send_weekly_digest():
    """
    Sends a weekly HTML health digest email to all patients
    who have email_digest_enabled=True.
    Scheduled every Sunday at 09:00 UTC via Celery Beat.
    """
    from django.contrib.auth import get_user_model
    from symptoms.models import Symptom, Moodlog

    User = get_user_model()
    today = date.today()
    week_ago = today - timedelta(days=7)

    patients = User.objects.filter(
        role='patient',
        email_digest_enabled=True,
        email__isnull=False,
    ).exclude(email='')

    emails_sent = 0

    for user in patients:
        # ── Gather this week's data ──────────────────────────────────────
        symptoms_this_week = Symptom.objects.filter(
            user=user,
            date__gte=week_ago,
            date__lte=today,
        )
        symptom_count = symptoms_this_week.count()

        top_symptom = (
            symptoms_this_week
            .values('name')
            .annotate(count=Count('id'))
            .order_by('-count')
            .first()
        )

        avg_severity = symptoms_this_week.aggregate(
            avg=Avg('severity')
        )['avg']

        moods_this_week = Moodlog.objects.filter(
            user=user,
            date__gte=week_ago,
            date__lte=today,
        )
        avg_mood = moods_this_week.aggregate(avg=Avg('mood'))['avg']

        active_meds = Medication.objects.filter(
            user=user,
            is_active=True,
        ).count()

        # Adherence — reminders sent vs taken this week
        reminders_this_week = MedicationReminder.objects.filter(
            medication__user=user,
            sent_at__date__gte=week_ago,
        )
        total_reminders = reminders_this_week.count()
        taken_reminders = reminders_this_week.filter(was_taken=True).count()
        adherence_pct = (
            round((taken_reminders / total_reminders) * 100)
            if total_reminders > 0 else None
        )

        # Pull latest cached AI insight
        from django.core.cache import cache
        ai_insight = None
        latest_symptom_obj = Symptom.objects.filter(user=user).order_by('-logged_at').first()
        latest_ts = latest_symptom_obj.logged_at.timestamp() if latest_symptom_obj else 0
        for window in [7, 14, 30]:
            cached = cache.get(f'ai_insights_{user.id}_{window}_{latest_ts}')
            if cached and 'insight' in cached:
                ai_insight = cached['insight'][:300] + '…'
                break

        # ── Build HTML email ─────────────────────────────────────────────
        subject = f"MediTrack Weekly Digest — {today.strftime('%B %d, %Y')}"

        # Helper to format optional values
        def fmt_mood(val):
            if val is None:
                return 'No logs'
            labels = {1: 'Very Bad', 2: 'Bad', 3: 'Okay', 4: 'Good', 5: 'Very Good'}
            return f"{val:.1f}/5 ({labels.get(round(val), '')})"

        def fmt_severity(val):
            return f"{val:.1f}/10" if val is not None else 'No logs'

        def fmt_adherence(val):
            return f"{val}%" if val is not None else 'No reminders sent'

        top_symptom_str = (
            f"{top_symptom['name']} ({top_symptom['count']} times)"
            if top_symptom else 'None logged'
        )

        html_message = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>MediTrack Weekly Digest</title>
</head>
<body style="margin:0;padding:0;background:#F1F5F9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#2563EB,#0891B2);border-radius:12px 12px 0 0;padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:26px;font-weight:700;letter-spacing:-0.5px;">
              ❤️ MediTrack
            </h1>
            <p style="margin:8px 0 0;color:#BFDBFE;font-size:14px;">
              Weekly Health Digest &nbsp;·&nbsp; {today.strftime('%B %d, %Y')}
            </p>
          </td>
        </tr>

        <!-- Greeting -->
        <tr>
          <td style="background:#ffffff;padding:28px 40px 8px;">
            <p style="margin:0;color:#0F172A;font-size:16px;">
              Hi <strong>{user.username}</strong>, here's your health summary for the past 7 days.
            </p>
          </td>
        </tr>

        <!-- Stats Grid -->
        <tr>
          <td style="background:#ffffff;padding:20px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <!-- Stat 1 -->
                <td width="48%" style="background:#EFF6FF;border-radius:10px;padding:18px;text-align:center;border:1px solid #DBEAFE;">
                  <p style="margin:0;font-size:28px;font-weight:700;color:#2563EB;">{symptom_count}</p>
                  <p style="margin:6px 0 0;font-size:12px;color:#475569;">Symptoms Logged</p>
                </td>
                <td width="4%"></td>
                <!-- Stat 2 -->
                <td width="48%" style="background:#F0FDF4;border-radius:10px;padding:18px;text-align:center;border:1px solid #BBF7D0;">
                  <p style="margin:0;font-size:28px;font-weight:700;color:#16A34A;">{active_meds}</p>
                  <p style="margin:6px 0 0;font-size:12px;color:#475569;">Active Medications</p>
                </td>
              </tr>
              <tr><td colspan="3" style="height:12px;"></td></tr>
              <tr>
                <!-- Stat 3 -->
                <td width="48%" style="background:#FFF7ED;border-radius:10px;padding:18px;text-align:center;border:1px solid #FED7AA;">
                  <p style="margin:0;font-size:20px;font-weight:700;color:#EA580C;">{fmt_mood(avg_mood)}</p>
                  <p style="margin:6px 0 0;font-size:12px;color:#475569;">Average Mood</p>
                </td>
                <td width="4%"></td>
                <!-- Stat 4 -->
                <td width="48%" style="background:#FDF4FF;border-radius:10px;padding:18px;text-align:center;border:1px solid #E9D5FF;">
                  <p style="margin:0;font-size:20px;font-weight:700;color:#9333EA;">{fmt_adherence(adherence_pct)}</p>
                  <p style="margin:6px 0 0;font-size:12px;color:#475569;">Medication Adherence</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Detail Row -->
        <tr>
          <td style="background:#ffffff;padding:0 40px 24px;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#F8FAFC;border-radius:10px;border:1px solid #E2E8F0;">
              <tr>
                <td style="padding:16px 20px;border-bottom:1px solid #E2E8F0;">
                  <span style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.5px;">Top Symptom</span><br/>
                  <span style="font-size:15px;color:#0F172A;font-weight:600;">{top_symptom_str}</span>
                </td>
              </tr>
              <tr>
                <td style="padding:16px 20px;">
                  <span style="font-size:12px;color:#94A3B8;text-transform:uppercase;letter-spacing:0.5px;">Average Severity</span><br/>
                  <span style="font-size:15px;color:#0F172A;font-weight:600;">{fmt_severity(avg_severity)}</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- AI Insight -->
        {"" if not ai_insight else f'''
        <tr>
          <td style="background:#ffffff;padding:0 40px 24px;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:linear-gradient(135deg,#EFF6FF,#F0F9FF);border-radius:10px;border:1px solid #BFDBFE;">
              <tr>
                <td style="padding:20px 24px;">
                  <p style="margin:0 0 8px;font-size:12px;color:#2563EB;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">
                    🧠 AI Health Insight
                  </p>
                  <p style="margin:0;font-size:14px;color:#1E3A5F;line-height:1.6;">
                    {ai_insight}
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        '''}

        <!-- CTA -->
        <tr>
          <td style="background:#ffffff;padding:0 40px 32px;text-align:center;">
            <a href="https://meditrack7.vercel.app"
               style="display:inline-block;background:linear-gradient(135deg,#2563EB,#0891B2);color:#ffffff;
                      text-decoration:none;font-weight:600;font-size:15px;padding:14px 32px;
                      border-radius:8px;">
              View Full Dashboard →
            </a>
          </td>
        </tr>

        <!-- Disclaimer -->
        <tr>
          <td style="background:#FFFBEB;border-top:1px solid #FDE68A;padding:16px 40px;border-radius:0 0 12px 12px;">
            <p style="margin:0;font-size:12px;color:#92400E;text-align:center;">
              ⚠️ MediTrack AI provides observations only — it does not diagnose medical conditions.
              Always consult a qualified healthcare professional.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px;text-align:center;">
            <p style="margin:0;font-size:12px;color:#94A3B8;">
              You're receiving this because weekly digests are enabled on your MediTrack account.<br/>
              To unsubscribe, turn off Weekly Digest in your profile settings.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>
        """

        plain_message = (
            f"MediTrack Weekly Digest — {today.strftime('%B %d, %Y')}\n\n"
            f"Hi {user.username},\n\n"
            f"Symptoms logged: {symptom_count}\n"
            f"Top symptom: {top_symptom_str}\n"
            f"Average severity: {fmt_severity(avg_severity)}\n"
            f"Average mood: {fmt_mood(avg_mood)}\n"
            f"Active medications: {active_meds}\n"
            f"Medication adherence: {fmt_adherence(adherence_pct)}\n\n"
            f"Visit your dashboard: https://meditrack7.vercel.app\n\n"
            f"— MediTrack"
        )

        if user.email:
            from django.core.mail import EmailMultiAlternatives
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            emails_sent += 1

    return f"Weekly digest sent to {emails_sent} patients"

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def test_email():
    send_mail(
        subject="MediTrack Email Test",
        message="If you received this, email is working.",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=["snaik0704@gmail.com"],
        fail_silently=False,
    )

    return "Email sent successfully"