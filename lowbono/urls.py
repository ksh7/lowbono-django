"""lowbono URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.urls import path, re_path, include
from django.conf.urls.i18n import i18n_patterns
from django.views.static import serve
from lowbono_lawyer.workflows import ReferralLawyerWorkflowState
from lowbono_mediator.workflows import ReferralMediatorWorkflowState


urlpatterns = [
    path('professionals/', include('lowbono_app.urls_professionals')),
    path('', include('lowbono_cms.urls')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('lawyers/', include('lowbono_lawyer.urls')),
    path('mediators/', include('lowbono_mediator.urls')),
    path('referral_workflow_lawyer/', include(ReferralLawyerWorkflowState.urls())),
    path('referral_workflow_mediator/', include(ReferralMediatorWorkflowState.urls())),
    re_path(r'^', include('cms.urls')),
    prefix_default_language=False,
)

urlpatterns += i18n_patterns(
    re_path(r'^' + settings.MEDIA_URL[1:] + r'(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
    prefix_default_language=False,
)
