"""
For the time being, the most important heuristic for determining article priority will be based on the presence of
authors
"""
import stop_words

from warden.models import AuthorRating


class AuthorRank:
    """
    Given a member and a set of articles, return articles rated on author ratings.
    The more authors per article that have a good rating, the higher the article rating.
    """
    @classmethod
    def rank(cls, member, articles):
        author_ratings = AuthorRating.objects.filter(member=member)
        authors = {x.author: x.rating for x in author_ratings}
        ranks = {}
        for article in articles:
            a = article.authors.all()
            ranks[article] = sum([authors.get(author, 0) for author in a])

        return ranks


class ArticleRank:
    """
    Given a member and a set of articles, return articles rated on a set of article criteria:
    We ignore the authors and look at a few things:
    TODO:
     1. autoencoder feature learning using pytorch into collaborative filtering
     2. bayesian something something
     3. category rating learning
    """
    def __init__(self, rankers):
        """
        Input: list of ranking algorithms in tuples of (class, weight)
        :param rankers:
        """
        self.rankers = rankers

    def rank(self, member, articles):
        ranks = {}
        for article in articles:
            ranks[article] = sum([r(member,article)*weight for r,weight in self.rankers])

        return ranks

    def tokenize_and_stop(self,text):
        swords = stop_words.get_stop_words('en')

        pass
