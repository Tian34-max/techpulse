from django.urls import path
from . import views

app_name = 'books'  # ← this is required for 'books:search'

urlpatterns = [
    path('search/', views.book_search, name='search'),  # ← defines books:search
]