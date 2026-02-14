from django.urls import path, include
from . import views


urlpatterns = [
    path('login', views.loginPage, name="login"),
    path('logout', views.logoutUser, name="logout"),

    path('dashboard', views.dashboardPage, name="dashboard"),
    path('invite', views.inviteUserPage, name='invite'),
    path('signup/<str:token>', views.signupPage, name="signup"),
    path('reset_password', views.resetPasswordPage, name="reset_password"),

    path('email_template/<str:id>', views.emailTemplateView, name="email_template"),

    path('', views.ProfessionalListView.as_view(), name="professional-list"),

    path('<str:id>', views.UserDetailView.as_view(), name='user-detail'),
    path('<str:id>/edit', views.UserUpdateView.as_view(), name='user-update'),

    path('<str:user_id>/vacations', views.VacationList.as_view(), name='vacations'),
    path('<str:user_id>/vacations/add', views.VacationCreateView.as_view(), name='vacations-add'),
    path('<str:user_id>/vacations/<str:id>/edit', views.VacationUpdateView.as_view(), name='vacations-edit'),

    path('referrals/<str:id>', views.ReferralDetailView.as_view(), name="referral-detail"),
    path('referrals/<str:id>/edit', views.ReferralUpdateView.as_view(), name="referral-update"),

    path('<str:id>/matters', views.UserMatterListView.as_view(), name="user-matters"),

    path('get_workflow_pretty_nodes/', views.getWorkflowNodes, name="get-workflow-pretty-nodes"),
    path('get_professional_by_practicearea/', views.getProfessionalByPracticeAreas, name="get-professional-by-practicearea"),
]
