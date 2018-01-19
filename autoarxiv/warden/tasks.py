from celery import Celery
from celery.schedules import crontab

from warden.scripts.emailer import receive_emails, send_listing
from .models import NewArticle, Member
from .scripts.article_sorting import AuthorRank
from .scripts.data_connector import DataConnector

app = Celery()

app.conf.beat_schedule = {
    'run_daily': {
        'task': 'tasks.run_day',
        'schedule': crontab(hour=1, minute=45)
    },
}

app.conf.timezone = 'EST'


@app.task
def run_day():
    # We update author preferences here.
    receive_emails()

    d = DataConnector()
    d.fetch_links()
    d.fetch_pdfs()
    d.pdf_to_txt()
    d.save()
    current = [x.article for x in NewArticle.objects.all()]
    am = AuthorRank()
    members = list(Member.objects.all())

    ranks = {}
    for member in members:
        ranks[member] = am.rank(member, current)

    # Presumably we do other ranking stuff here but for now it'll be like this

    for member in ranks:
        articles = sorted([[ranks[member][article], article] for article in ranks[member]], key=lambda x: x[:-1])
        listing = ["Author Rank, Arxiv ID, URL, Title, Authors"]
        for article in articles:
            msg = "{0} : {1} : {2} : {3}: \n    {4}" \
                .format(article[0],
                        article[1].shortid,
                        article[1].link,
                        article[1].title,
                        ", ".join([author.name for author in article[1].authors.all()]))
            listing.append(msg)

        send_listing(member.email, listing)
