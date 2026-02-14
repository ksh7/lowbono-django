from django.urls import path, include
from . import views


urlpatterns = [
    path('<int:step>', views.step, name="mediator_step"),

    path('<str:professional_id>/pending-matters/<str:workflow_state>', views.overdueMattersEmail, name="pending-mediator-matters-by-event"),
    path('mediator_workflow_no_update/', views.updateMediatorReferralWorkflow, name="mediator-workflow-no-update"),
]
