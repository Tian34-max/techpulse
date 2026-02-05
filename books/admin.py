from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .models import Book, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


class BookResource(resources.ModelResource):
    class Meta:
        model = Book
        fields = (
            'title',
            'author',
            'isbn',
            'category__name',    # import/export by category name
            'school__name',      # if you want school name
            'total_copies',
            'available',
            'publication_year',
            'description',
        )
        export_order = fields


@admin.register(Book)
class BookAdmin(ImportExportModelAdmin):
    resource_class = BookResource
    list_display = ('title', 'author', 'category', 'available', 'total_copies', 'school')
    list_filter = ('category', 'school')
    search_fields = ('title', 'author', 'isbn', 'category__name')
    list_editable = ('available',)