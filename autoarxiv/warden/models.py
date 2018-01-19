from django.db import models


# Create your models here.

class Article(models.Model):
    """
    Contains all the meta information of the articles as well as the article text itself, unprocessed.
    """
    abstract = models.TextField()
    authors = models.ManyToManyField('Author')
    basename = models.CharField(max_length=64)
    categories = models.ManyToManyField('Category')
    date = models.CharField(max_length=10)
    link = models.CharField(max_length=512)
    pdflink = models.CharField(max_length=512)
    pdfname = models.CharField(max_length=64)
    shortid = models.CharField(max_length=64, unique=True)
    text = models.TextField()
    txtname = models.CharField(max_length=64)
    title = models.CharField(max_length=512)

    def set_abstract(self, abstract):
        self.abstract = abstract

    def set_authors(self, authors):
        self.authors.set(authors)

    def set_basename(self, name):
        self.basename = name

    def set_categories(self, categories):
        self.categories.set(categories)

    def set_date(self, date):
        self.date = date

    def set_link(self, link):
        self.link = link

    def set_pdflink(self, link):
        self.pdflink = link

    def set_pdfname(self, name):
        self.pdfname = name

    def set_shortid(self, shortid):
        self.shortid = shortid

    def set_text(self, text):
        self.text = text

    def set_txtname(self, name):
        self.txtname = name

    def set_title(self, title):
        self.title = title

    class Meta:
        unique_together = ['shortid']


class Author(models.Model):
    name = models.CharField(max_length=64)
    email = models.EmailField()

    def set_name(self, name):
        self.name = name

    def set_email(self, email):
        self.email = email

    class Meta:
        unique_together = ['name', 'email']


class Category(models.Model):
    name = models.CharField(max_length=16, unique=True)

    def set_name(self, name):
        self.name = name


class NewArticle(models.Model):
    article = models.ForeignKey('Article', on_delete=models.CASCADE)


class ArticleRating(models.Model):
    """
    Used with the Member class to store meta information
    """
    member = models.ForeignKey('Member', on_delete=models.CASCADE)
    article = models.ForeignKey('Article', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ['member', 'article']


class AuthorRating(models.Model):
    """
    Used with the Member class to store meta information
    """
    member = models.ForeignKey('Member', on_delete=models.CASCADE)
    author = models.ForeignKey('Author', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ['member', 'author']


class Member(models.Model):
    """
    Member is pretty analogous to a Django user
    """
    name = models.CharField(max_length=32)
    email = models.EmailField()
    library = models.ManyToManyField('Article', through='ArticleRating')
    authors = models.ManyToManyField('Author', through='AuthorRating')

    def set_name(self, name):
        self.name = name

    def set_email(self, email):
        self.email = email

    def add_article(self, article, rating=0):
        self.library.add(AuthorRating(member=self, article=article, rating=rating))

    def add_author(self, author, rating=0):
        self.authors.add(AuthorRating(member=self, author=author, rating=rating))

    class Meta:
        unique_together = ['name', 'email']
