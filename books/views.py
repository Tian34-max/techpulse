from django.shortcuts import render
from .models import Book

def book_search(request):
    query = request.GET.get('q', '')
    books = Book.objects.all()
    if query:
        books = books.filter(title__icontains=query) | books.filter(author__icontains=query) | books.filter(isbn__icontains=query)
    return render(request, 'books/search.html', {'books': books, 'query': query})