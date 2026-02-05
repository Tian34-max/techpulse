from django.urls import path
from . import views  # we'll add real views later

app_name = 'schools'

urlpatterns = [
    # Placeholder - add real school URLs later
    path('', views.school_home, name='school_home'),
]