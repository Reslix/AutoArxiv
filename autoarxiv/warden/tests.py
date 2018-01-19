from django.test import TestCase

# Create your tests here.
from warden.models import Article, Author, Member, AuthorRating
from warden.scripts.article_sorting import AuthorRank
from warden.scripts.data_connector import DataConnector
from warden.scripts.emailer import receive_emails


def print_article(article):
    print(article.title)
    print(article.shortid)


class MainTestCase(TestCase):

    def test_data_connector(self):
        print()
        d = DataConnector(number=2)
        d.fetch_links()
        d.fetch_pdfs()
        d.pdf_to_txt()
        d.save()
        print('\n'+'test_data_connector:'+'\n')
        [print_article(article) for article in Article.objects.all()]

    def test_author_ranking(self):
        author1 = Author(name='test1', email='test1')
        author2 = Author(name='test2', email='test2')

        author1.save(), author2.save()

        article1 = Article(title='article1')
        article2 = Article(title='article2')
        article3 = Article(title='article3')
        article4 = Article(title='article4')

        article1.save(), article2.save(), article3.save(), article4.save()

        article1.set_authors([author1])
        article2.set_authors([author2])
        article3.set_authors([author1, author2])

        member = Member(name='test0', email='test0')

        member.save()

        AuthorRating(member=member, author=author1, rating=1).save()
        AuthorRating(member=member, author=author2, rating=2).save()
        print('\n'+'test_author_ranking:'+'\n')
        print(AuthorRank.rank(member, [article1, article2, article3, article4]))

    """

    def test_emailer(self):
        a = Member(name="Will", email="huashengz@gmail.com")
        a.save()
        receive_emails()
        print(AuthorRating.objects.all())
    """