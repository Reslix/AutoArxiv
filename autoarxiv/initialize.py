"""
This will populate the database with a certain amount of articles beforehand.
"""
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "autoarxiv.settings")
django.setup()

from warden.models import Article, Category, Author
from warden.scripts.data_connector import DataConnector

Article.objects.all().delete()

d = DataConnector(number=10, start=10)
d.fetch_links(care=0)
d.fetch_pdfs()
d.pdf_to_txt()
d.save()
