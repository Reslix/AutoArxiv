import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "autoarxiv.settings")
django.setup()

from warden.tasks import run_day

run_day()
