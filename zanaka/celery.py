import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zanaka.settings')

app = Celery("mchangohub")
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.task_default_queue = "zanaka_queue"
app.conf.timezone = "Africa/Nairobi"
app.conf.enable_utc = True
app.autodiscover_tasks()