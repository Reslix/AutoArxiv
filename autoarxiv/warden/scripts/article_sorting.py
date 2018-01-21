"""
For the time being, the most important heuristic for determining article priority will be based on the presence of
authors
"""
from sklearn import svm
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer

from warden.models import AuthorRating, ArticleRating


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


class CompositeRank:
    """
    Given a member and a set of articles, return articles rated on a set of article criteria:
        Basically everything, including a composite author rating. The weights will be learned.
        For now, only the abstracts of articles will be used to reduce the dimensionality of the problem space.
    TODO:
     1. autoencoder feature learning using pytorch into collaborative filtering
     2. bayesian something something
     3. category rating learning
    """

    def rank(self, member, articles):
        ranks = {}
        labeled = list(ArticleRating.objects.filter(member=member))
        if len(labeled) > 0:
            labeled_text = [rating.article.abstract for rating in labeled]
            labeled_authors = [rating.article.authors.all() for rating in labeled]
            labels = [rating.rating for rating in labeled]
            unlabeled_text = [article.abstract for article in articles]

            model, count_vect, tfidf_transformer = self.train_model(labeled_text, labels)

            predictions = self.predict(model, count_vect, tfidf_transformer, unlabeled_text)

            author_rating = {}
            for label, l_authors in zip(labels, labeled_authors):
                for author in l_authors:
                    if author in author_rating:
                        author_rating[author] += label
                    else:
                        author_rating[author] = label

            author_pred = [sum([author_rating.get(author, 0) for author in article.authors.all()]) for article in
                           articles]

            for article, author_pred, prediction in zip(articles, author_pred, predictions):
                ranks[article] = (author_pred, prediction)
        else:
            ranks = {article: (0, 0) for article in articles}

        return ranks

    def predict(self, model, count_vect, tfidf_transformer, text):
        counts = count_vect.transform(text)
        tfidf = tfidf_transformer.transform(counts)
        return model.predict(tfidf)

    def train_model(self, text, labels):
        """
        This is a SVM that uses tfidf vectors as features. In the future, we want to use a more sophisticated
        model for recommendation, but this should suffice on naive examples (there's no basis for this assumption).
        :param text:
        :return:
        """
        clf = svm.SVR()
        count_vect = CountVectorizer()
        tfidf_transformer = TfidfTransformer()
        counts = count_vect.fit_transform(text)
        tfidf = tfidf_transformer.fit_transform(counts)
        clf.fit(tfidf, labels)

        return clf, count_vect, tfidf_transformer
