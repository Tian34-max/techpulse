from django.contrib import admin
from .models import School, UserSchoolProfile


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'phone', 'email', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'short_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'short_name', 'address', 'phone', 'email', 'logo', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(UserSchoolProfile)
class UserSchoolProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'is_librarian', 'created_at')
    list_filter = ('is_librarian', 'school')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')