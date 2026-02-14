import os
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.static import serve


def news_article_page(request, slug):
    from lowbono_app.models import NewsArticles
    news = NewsArticles.objects.filter(slug=slug).first()
    if news:
        return render(request, 'lowbono_cms/news_article.html', {'news': news})
    messages.info(request, "Sorry, Page you requested doesn't exist!")
    return redirect('/news')

def robots_txt(request):
    content = "User-agent: *\nDisallow: /professionals/\nDisallow: /admin/"
    return HttpResponse(content, content_type="text/plain")

def favicon_ico(request):
    favicon_path = os.path.join(settings.BASE_DIR, 'lowbono_cms', 'static', 'favicon.ico')
    return serve(request, os.path.basename(favicon_path), os.path.dirname(favicon_path))
