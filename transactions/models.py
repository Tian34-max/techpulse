from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings

from books.models import Book
from students.models import Student


class BorrowTransaction(models.Model):
    STATUS_CHOICES = [
        ('ISSUED', 'Issued'),
        ('OVERDUE', 'Overdue'),
        ('RETURNED', 'Returned'),
        ('LOST', 'Lost'),
        ('DAMAGED', 'Damaged'),
        ('CANCELLED', 'Cancelled'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='borrow_transactions',
        verbose_name="Borrower"
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='borrow_transactions',
        verbose_name="Book"
    )
    issued_date = models.DateField(default=timezone.now, verbose_name="Date Issued")
    due_date = models.DateField(verbose_name="Due Date")
    returned_date = models.DateField(null=True, blank=True, verbose_name="Date Returned")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ISSUED', verbose_name="Status")
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total Fine (UGX)")
    fine_paid = models.BooleanField(default=False, verbose_name="Fine Paid?")
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_transactions', verbose_name="Issued By")
    notes = models.TextField(blank=True, verbose_name="Notes")
    renewal_count = models.PositiveIntegerField(default=0, verbose_name="Renewal Count")
    max_renewals = models.PositiveIntegerField(default=2, verbose_name="Max Renewals Allowed")

    class Meta:
        ordering = ['-issued_date']
        verbose_name = "Borrow Transaction"
        verbose_name_plural = "Borrow Transactions"
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['book', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.student} - {self.book} ({self.status})"

    def clean(self):
        if self.pk is None:
            if self.book.available <= 0:
                raise ValidationError(f"Cannot issue '{self.book.title}' - no copies available.")
            if self.due_date and self.due_date <= self.issued_date:
                raise ValidationError("Due date must be after issued date.")

    def save(self, *args, **kwargs):
        if self.pk is None:
            if self.book.available <= 0:
                raise ValidationError("No copies available to issue.")
            self.book.available -= 1
            self.book.save(update_fields=['available'])

            if not self.due_date:
                self.due_date = self.issued_date + timezone.timedelta(days=14)

        elif self.status == 'RETURNED' and self.returned_date is None:
            self.returned_date = timezone.now().date()
            self.book.available += 1
            self.book.save(update_fields=['available'])
            self.fine_amount = self.calculate_fine()

        super().save(*args, **kwargs)

    def is_overdue(self):
        if self.status in ['RETURNED', 'LOST', 'DAMAGED', 'CANCELLED']:
            return False
        if self.due_date is None:
            return False
        return timezone.now().date() > self.due_date

    def days_overdue(self):
        if not self.is_overdue() or self.due_date is None:
            return 0
        return (timezone.now().date() - self.due_date).days

    def calculate_fine(self, daily_rate=1000):
        if not self.is_overdue():
            return 0
        return self.days_overdue() * daily_rate

    def can_renew(self):
        return self.status == 'ISSUED' and self.renewal_count < self.max_renewals

    def renew(self, days=14):
        if not self.can_renew():
            raise ValidationError("Cannot renew this borrow (max renewals reached or not issued).")
        self.due_date += timezone.timedelta(days=days)
        self.renewal_count += 1
        self.save()