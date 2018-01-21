from celery import Celery
from celery.schedules import crontab

from warden.scripts.emailer import receive_emails, send_listing
from .models import NewArticle, Member
from .scripts.article_sorting import AuthorRank, CompositeRank
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
    NewArticle.objects.all().delete()

    # We update author preferences here.
    receive_emails()

    d = DataConnector()
    d.fetch_links()
    d.fetch_pdfs()
    d.pdf_to_txt()
    d.save()
    current = [x.article for x in NewArticle.objects.all()]
    am = AuthorRank()
    cm = CompositeRank()
    members = list(Member.objects.all())

    author_ranks = {}
    composite_ranks = {}
    ranks = {}
    t_ranks = [author_ranks, composite_ranks]
    if len(current) != 0:
        for member in members:
            author_ranks[member] = am.rank(member, current)
            composite_ranks[member] = cm.rank(member, current)

        for member in members:
            ranks[member] = {article: [rank[member][article] for rank in t_ranks] for article in current}

        for member in ranks:
            articles = sorted([[article, ranks[member][article][0], ranks[member][article][1]]
                               for article in ranks[member]], key=lambda x: x[1:], reverse=True)
            split = 0
            while articles[split][1] > 0:
                split += 1
            listing = ["Author Rank, Composite Rank (Author, Abstract), Arxiv ID, URL, Title, Authors",
                       "Recommended according to author preferences:"]
            for i, article in enumerate(articles):
                if i == split:
                    listing.append("Discovery list according to composite score:")
                msg = "{0}, {1}, {2}, {3}: \"{4}\": \n\t{5}" \
                    .format(article[1],
                            article[2],
                            article[0].shortid,
                            article[0].link,
                            article[0].title.strip().replace('\n', ''),
                            ", ".join([author.name for author in article[0].authors.all()]))
                listing.append(msg)

            send_listing(member.email, listing)
