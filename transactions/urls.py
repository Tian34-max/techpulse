from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('overdue-report/', views.overdue_report, name='overdue_report'),
    # Add more transaction URLs here later (issue, return, etc.)
]