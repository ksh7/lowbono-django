from django.urls import path
from django.views.generic.base import RedirectView
from .views import robots_txt, favicon_ico, news_article_page

urlpatterns = [
    path('robots.txt/', robots_txt, name='robots_txt'),
    path('favicon.ico/', favicon_ico, name='favicon_ico'),
    path('news/<str:slug>', news_article_page, name="news_article_page"),
]
