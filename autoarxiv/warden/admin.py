from django.contrib import admin

# Register your models here.
from .models import Member, NewArticle
from .models import Article
from .models import Category
from .models import Author
from .models import ArticleRating
from .models import AuthorRating

admin.site.register(Member)
admin.site.register(Article)
admin.site.register(Category)
admin.site.register(Author)
admin.site.register(ArticleRating)
admin.site.register(AuthorRating)
admin.site.register(NewArticle)