from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    # Core dashboards
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('librarian/', views.librarian_dashboard, name='librarian_dashboard'),

    # Search and list
    path('search/', views.student_search, name='student_search'),
    path('student-list/', views.student_list, name='student_list'),

    # Book management
    path('add-book/', views.add_book, name='add_book'),
    path('issue-book/', views.issue_book, name='issue_book'),
    path('return-book/<int:transaction_id>/', views.return_book, name='return_book'),

    # Newly added for the missing buttons
    path('returns/', views.returns_list, name='returns_list'),                  # Returns page
    path('reports/', views.reports_overview, name='reports_overview'),         # Reports page
    path('settings/', views.librarian_settings, name='librarian_settings'),    # Settings page
    path('class-lists/', views.class_lists_overview, name='class_lists_overview'),
    path('class/<int:class_id>/', views.class_detail, name='class_detail'),
    path('library-stock/', views.library_stock, name='library_stock'),
    path('search/', views.student_search, name='student_search'),
    path('import-students/', views.ImportStudentsView.as_view(), name='import_students'),
    path('bulk-return/', views.bulk_return, name='bulk_return'),
]
