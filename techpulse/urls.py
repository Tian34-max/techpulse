from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication
    path('accounts/login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # Public home page
    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    # Apps
    path('students/', include('students.urls')),
    path('books/', include('books.urls')),
    path('transactions/', include('transactions.urls')),
]