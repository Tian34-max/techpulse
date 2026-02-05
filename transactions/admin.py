from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import path
from .models import BorrowTransaction


@admin.register(BorrowTransaction)
class BorrowTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'book',
        'issued_date',
        'due_date',
        'status_colored',
        'days_overdue_display',
        'fine_amount',
        'fine_paid',
        'renewal_count',
        'issued_by',
    )
    list_filter = ('status', 'issued_date', 'due_date', 'fine_paid', 'renewal_count')
    search_fields = (
        'student__name',
        'student__student_id',
        'book__title',
        'book__isbn',
    )
    date_hierarchy = 'issued_date'
    readonly_fields = ('fine_amount', 'returned_date', 'renewal_count')
    actions = ['renew_transaction', 'mark_lost', 'mark_damaged', 'mark_returned']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('overdue-report/', self.admin_site.admin_view(self.overdue_report_view),
                 name='overdue_report'),
        ]
        return custom_urls + urls

    def status_colored(self, obj):
        colors = {
            'ISSUED': 'blue',
            'OVERDUE': 'red',
            'RETURNED': 'green',
            'LOST': 'purple',
            'DAMAGED': 'orange',
            'CANCELLED': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color: {};">{}</span>', color, obj.status)
    status_colored.short_description = "Status"

    def days_overdue_display(self, obj):
        if obj.pk is None:
            return "-"
        days = obj.days_overdue()
        if days > 0:
            return format_html('<strong style="color:red;">{} days overdue</strong>', days)
        return "-"
    days_overdue_display.short_description = "Overdue"

    @admin.action(description="Renew selected transactions (extend due date by 14 days)")
    def renew_transaction(self, request, queryset):
        success_count = 0
        for transaction in queryset:
            try:
                transaction.renew(days=14)
                success_count += 1
                self.message_user(request, f"Renewed: {transaction}")
            except ValidationError as e:
                self.message_user(request, f"Cannot renew {transaction}: {e}", level='error')
        if success_count:
            self.message_user(request, f"Successfully renewed {success_count} transaction(s).")

    @admin.action(description="Mark selected as Lost (reduce stock permanently)")
    def mark_lost(self, request, queryset):
        success_count = 0
        for transaction in queryset:
            if transaction.status not in ['RETURNED', 'LOST', 'DAMAGED']:
                transaction.status = 'LOST'
                transaction.book.total_copies -= 1
                transaction.book.available -= 1
                transaction.book.save(update_fields=['total_copies', 'available'])
                transaction.save()
                success_count += 1
                self.message_user(request, f"Marked as Lost: {transaction}")
            else:
                self.message_user(request, f"Cannot mark {transaction} as Lost (already finalized)", level='error')
        if success_count:
            self.message_user(request, f"Successfully marked {success_count} as Lost.")

    @admin.action(description="Mark selected as Damaged (reduce available copies)")
    def mark_damaged(self, request, queryset):
        success_count = 0
        for transaction in queryset:
            if transaction.status not in ['RETURNED', 'LOST', 'DAMAGED']:
                transaction.status = 'DAMAGED'
                transaction.book.available -= 1
                transaction.book.save(update_fields=['available'])
                transaction.save()
                success_count += 1
                self.message_user(request, f"Marked as Damaged: {transaction}")
            else:
                self.message_user(request, f"Cannot mark {transaction} as Damaged (already finalized)", level='error')
        if success_count:
            self.message_user(request, f"Successfully marked {success_count} as Damaged.")

    @admin.action(description="Mark selected as Returned")
    def mark_returned(self, request, queryset):
        success_count = 0
        for transaction in queryset:
            try:
                if transaction.status in ['ISSUED', 'OVERDUE']:
                    transaction.status = 'RETURNED'
                    transaction.returned_date = timezone.now().date()
                    transaction.fine_amount = transaction.calculate_fine()
                    transaction.book.available += 1
                    transaction.book.save(update_fields=['available'])
                    transaction.save()
                    success_count += 1
                    self.message_user(request, f"Successfully returned: {transaction}")
                else:
                    raise ValidationError(f"Cannot return {transaction}: already {transaction.status.lower()}.")
            except ValidationError as e:
                self.message_user(request, f"Error returning {transaction}: {e}", level='error')
        if success_count:
            self.message_user(request, f"Successfully returned {success_count} transaction(s).")

    def overdue_report_view(self, request):
        today = timezone.now().date()
        overdue = BorrowTransaction.objects.filter(
            status__in=['ISSUED', 'OVERDUE'],
            due_date__lt=today
        ).select_related('student', 'book')

        total_overdue = overdue.count()
        total_fine = sum(t.calculate_fine() for t in overdue)

        context = {
            'overdue': overdue,
            'total_overdue': total_overdue,
            'total_fine': total_fine,
            'title': 'Overdue Borrow Report',
        }
        return render(request, 'admin/transactions/overdue_report.html', context)