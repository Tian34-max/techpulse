from django.db import models
from django.core.validators import MinValueValidator

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, blank=True, null=True)
    
    # NEW: Category as ForeignKey (recommended - better for management)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books'
    )
    
    # Alternative if you prefer simple text field (less powerful):
    # category = models.CharField(max_length=100, blank=True)

    school = models.ForeignKey('schools.School', on_delete=models.CASCADE)
    total_copies = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    available = models.PositiveIntegerField(default=1, validators=[MinValueValidator(0)])
    publication_year = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return f"{self.title} ({self.author})"

    @property
    def status(self):
        if self.available == 0:
            return "Not Available"
        elif self.available < self.total_copies:
            return f"{self.available} available"
        return "Available"