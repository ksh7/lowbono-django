from django.urls import path, include
from . import views


urlpatterns = [
    path('llm_await', views.llmAwait, name="llm_await"),
    path('<int:step>', views.step, name="lawyer_step"),

    path('<str:professional_id>/pending-matters/<str:workflow_state>', views.overdueMattersEmail, name="pending-lawyer-matters-by-event"),
    path('lawyer_workflow_no_update/', views.updateLawyerReferralWorkflow, name="lawyer-workflow-no-update"),
]
