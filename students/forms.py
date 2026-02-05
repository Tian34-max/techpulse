from django import forms
from books.models import Book, Category

class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title',
            'author',
            'isbn',
            'category',           # now included
            'total_copies',
            'publication_year',
            'description',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }