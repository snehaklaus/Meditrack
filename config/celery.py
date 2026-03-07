import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('meditrack')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    #'check-medication-reminders': {
     #   'task': 'medications.tasks.send_medication_reminders',
      #  'schedule': 900.0,  # every 10 minutes (change to crontab(minute=0) after testing)
    #},
    'send-weekly-digest-sunday-9am': {
        'task': 'medications.tasks.send_weekly_digest',
        'schedule': crontab(hour=9, minute=0, day_of_week=0),  # Sunday 09:00 UTC
    },
}