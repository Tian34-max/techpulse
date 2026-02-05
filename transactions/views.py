from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import BorrowTransaction

@login_required
def overdue_report(request):
    today = timezone.now().date()
    overdue = BorrowTransaction.objects.filter(
        status__in=['ISSUED', 'OVERDUE'],
        due_date__lt=today
    ).select_related('student', 'book').order_by('due_date')

    total_overdue = overdue.count()
    total_fine = sum(transaction.calculate_fine() for transaction in overdue)

    context = {
        'overdue': overdue,
        'total_overdue': total_overdue,
        'total_fine': total_fine,
        'title': 'Overdue Borrow Report',
    }
    return render(request, 'transactions/overdue_report.html', context)