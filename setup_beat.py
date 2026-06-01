"""
Run this script once after migrations to set up Celery Beat periodic tasks.
Usage: python setup_beat.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_celery_beat.models import PeriodicTask, IntervalSchedule

# Every 1 hour — process matured investments
schedule, _ = IntervalSchedule.objects.get_or_create(
    every=1,
    period=IntervalSchedule.HOURS,
)

PeriodicTask.objects.update_or_create(
    name='Process Matured Investments',
    defaults={
        'interval': schedule,
        'task': 'apps.notifications.tasks.process_matured_investments',
        'enabled': True,
    }
)

print('✅ Celery Beat tasks configured successfully.')