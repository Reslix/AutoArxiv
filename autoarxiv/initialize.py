"""
This will populate the database with a certain amount of articles beforehand.
"""
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "autoarxiv.settings")
django.setup()

from warden.scripts.data_connector import DataConnector

d = DataConnector(number=10000, start=100)
d.clear_articles()
d.fetch_links(care=0)
d.fetch_pdfs()
d.pdf_to_txt()
d.save()
