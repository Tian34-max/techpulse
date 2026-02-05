from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from students.models import Student  # absolute import from students app
from books.models import Book
from transactions.models import BorrowTransaction
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

# Home page view (public or redirect to dashboard if logged in)
def home(request):
    if request.user.is_authenticated:
        # Redirect based on role
        if hasattr(request.user, 'school_profile') and request.user.school_profile.is_librarian:
            return redirect('librarian_dashboard')
        else:
            return redirect('student_dashboard')
    else:
        # Public home page
        return render(request, 'home.html')

# Custom login view (optional - use this if you want more control)
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('home')  # or 'student_dashboard'

# If you want to keep the default LoginView, just use it in urls.py instead