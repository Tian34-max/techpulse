from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count, F, Sum
from django.db.models.functions import ExtractWeekDay
from django.contrib import messages
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Student, ClassGroup
from books.models import Book
from transactions.models import BorrowTransaction
from .forms import BookForm
import csv
from io import StringIO


@login_required
def student_dashboard(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return render(request, 'dashboard/student.html', {
            'borrows': [],
            'borrowed_count': 0,
            'overdue_count': 0,
            'total_fine': 0,
            'error_message': 'No student profile found. Contact the librarian.'
        })

    borrows = BorrowTransaction.objects.filter(student=student).order_by('-issued_date')

    borrowed_count = borrows.filter(status='ISSUED').count()
    overdue_count = borrows.filter(status='OVERDUE').count()
    total_fine = sum(b.fine_amount for b in borrows if not b.fine_paid)

    context = {
        'borrows': borrows,
        'borrowed_count': borrowed_count,
        'overdue_count': overdue_count,
        'total_fine': total_fine,
        'student': student,
    }
    return render(request, 'dashboard/student.html', context)


@login_required
def librarian_dashboard(request):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    school = request.user.school_profile.school
    today = timezone.now().date()

    class_stats = Student.objects.filter(school=school).values(
        'class_group__name'
    ).annotate(
        student_count=Count('id')
    ).order_by('class_group__name')

    total_students = Student.objects.filter(school=school).count()
    total_classes = class_stats.count()

    total_books = Book.objects.filter(school=school).count()
    available_books = Book.objects.filter(school=school, available__gt=0).order_by('-available')
    low_stock_books = Book.objects.filter(school=school, available__lte=2)
    low_stock_count = low_stock_books.count()

    borrowed_books = BorrowTransaction.objects.filter(
        book__school=school,
        status__in=['ISSUED', 'OVERDUE']
    ).select_related('student', 'book').order_by('-issued_date')

    total_borrowed = borrowed_books.count()
    today_issued = borrowed_books.filter(issued_date=today).count()
    overdue_count = borrowed_books.filter(status='OVERDUE').count()

    monthly_student_growth = total_students // 10

    # Weekly borrowings graph data
    week_start = today - timezone.timedelta(days=today.weekday())
    weekly_data = BorrowTransaction.objects.filter(
        book__school=school,
        issued_date__gte=week_start,
        issued_date__lte=today
    ).annotate(
        weekday=ExtractWeekDay('issued_date')
    ).values('weekday').annotate(
        count=Count('id')
    ).order_by('weekday')

    chart_data = [0] * 7
    for entry in weekly_data:
        weekday = entry['weekday'] - 1
        chart_data[weekday] = entry['count']

    max_count = max(chart_data) if any(chart_data) else 1
    scaled_heights = [(count / max_count * 100) for count in chart_data]

    context = {
        'class_stats': class_stats,
        'total_students': total_students,
        'monthly_student_growth': monthly_student_growth,
        'total_classes': total_classes,
        'available_books': available_books[:10],
        'low_stock_books': low_stock_books[:5],
        'borrowed_books': borrowed_books[:20],
        'total_borrowed': total_borrowed,
        'today_issued': today_issued,
        'overdue_count': overdue_count,
        'total_books': total_books,
        'low_stock_count': low_stock_count,
        'school': school,
        'weekly_borrow_counts': chart_data,
        'weekly_scaled_heights': scaled_heights,
    }
    return render(request, 'dashboard/librarian.html', context)


@login_required
def student_search(request):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    query = request.GET.get('q', '')
    school = request.user.school_profile.school

    students = Student.objects.filter(school=school)
    if query:
        students = students.filter(
            Q(name__icontains=query) |
            Q(student_id__icontains=query) |
            Q(class_group__name__icontains=query) |
            Q(email__icontains=query) |
            Q(roll_number__icontains=query)
        )

    context = {
        'students': students,
        'query': query,
        'title': 'Student Search',
    }
    return render(request, 'students/search.html', context)


@login_required
def student_list(request):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    school = request.user.school_profile.school
    query = request.GET.get('q', '')

    students = Student.objects.filter(school=school)
    if query:
        students = students.filter(
            Q(name__icontains=query) |
            Q(student_id__icontains=query) |
            Q(class_group__name__icontains=query)
        )

    context = {
        'students': students,
        'query': query,
    }
    return render(request, 'students/list.html', context)


@login_required
def add_book(request):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    school = request.user.school_profile.school

    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            book.school = school
            book.available = book.total_copies
            book.save()
            messages.success(request, 'Book added successfully!')
            return redirect('students:librarian_dashboard')
    else:
        form = BookForm()

    context = {'form': form}
    return render(request, 'dashboard/add_book.html', context)


@login_required
def issue_book(request):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    school = request.user.school_profile.school

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        due_date_str = request.POST.get('due_date')

        try:
            student = Student.objects.get(id=student_id, school=school)
            due_date = timezone.datetime.strptime(due_date_str, '%Y-%m-%d').date()

            issued_total = 0
            warnings = []

            for book in Book.objects.filter(school=school, available__gt=0):
                qty_key = f"qty_{book.id}"
                qty_str = request.POST.get(qty_key, "0")
                try:
                    qty = int(qty_str)
                    if qty > 0:
                        if qty > book.available:
                            warnings.append(f"Only {book.available} copy/copies of '{book.title}' available (requested {qty}).")
                            qty = book.available

                        for _ in range(qty):
                            BorrowTransaction.objects.create(
                                student=student,
                                book=book,
                                issued_date=timezone.now().date(),
                                due_date=due_date,
                                status='ISSUED'
                            )

                        book.available -= qty
                        book.save(update_fields=['available'])
                        issued_total += qty

                except ValueError:
                    pass

            if issued_total > 0:
                messages.success(request, f"{issued_total} book cop{'y' if issued_total == 1 else 'ies'} issued to {student.name}!")
                for w in warnings:
                    messages.warning(request, w)
            else:
                messages.warning(request, "No valid books or quantities selected.")

            return redirect('students:librarian_dashboard')

        except (Student.DoesNotExist, Book.DoesNotExist):
            messages.error(request, 'Invalid student or book selection.')
        except ValueError:
            messages.error(request, 'Invalid due date format.')

    students = Student.objects.filter(school=school).order_by('name')
    books = Book.objects.filter(school=school, available__gt=0).order_by('title')

    context = {
        'students': students,
        'books': books,
    }
    return render(request, 'dashboard/issue_book.html', context)


@login_required
def return_book(request, transaction_id):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    transaction = get_object_or_404(
        BorrowTransaction,
        id=transaction_id,
        book__school=request.user.school_profile.school,
        status__in=['ISSUED', 'OVERDUE']
    )

    if request.method == 'POST':
        return_date = timezone.now().date()
        transaction.returned_date = return_date
        transaction.status = 'RETURNED'

        if return_date > transaction.due_date:
            days_late = (return_date - transaction.due_date).days
            transaction.fine_amount = days_late * 1000
            transaction.fine_paid = False
            messages.warning(request, f"Returned {days_late} day(s) late. Fine: {transaction.fine_amount} UGX")
        else:
            messages.success(request, "Book returned successfully.")

        transaction.save()

        transaction.book.available = F('available') + 1
        transaction.book.save(update_fields=['available'])

        next_url = request.GET.get('next', 'students:librarian_dashboard')
        return redirect(next_url)

    context = {
        'transaction': transaction,
        'student': transaction.student,
        'book': transaction.book,
        'days_left': (transaction.due_date - timezone.now().date()).days if transaction.due_date >= timezone.now().date() else 0,
    }
    return render(request, 'dashboard/return_book_confirm.html', context)


@login_required
def returns_list(request):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    school = request.user.school_profile.school
    borrowed_books = BorrowTransaction.objects.filter(
        book__school=school,
        status__in=['ISSUED', 'OVERDUE']
    ).select_related('student', 'book').order_by('-issued_date')

    context = {
        'borrowed_books': borrowed_books,
        'title': 'Returns & Borrowed Books',
    }
    return render(request, 'dashboard/returns_list.html', context)


@login_required
def reports_overview(request):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    school = request.user.school_profile.school

    total_students = Student.objects.filter(school=school).count()
    total_books = Book.objects.filter(school=school).count()
    total_borrowed = BorrowTransaction.objects.filter(
        book__school=school, status__in=['ISSUED', 'OVERDUE']
    ).count()
    overdue_count = BorrowTransaction.objects.filter(
        book__school=school, status='OVERDUE'
    ).count()

    on_time_returns = BorrowTransaction.objects.filter(
        book__school=school,
        status='RETURNED',
        returned_date__lte=F('due_date')
    ).count()

    total_returns = BorrowTransaction.objects.filter(
        book__school=school, status='RETURNED'
    ).count()

    on_time_percentage = round((on_time_returns / total_returns * 100) if total_returns > 0 else 0, 1)

    students_with_borrows = Student.objects.filter(
        school=school,
        borrow_transactions__isnull=False
    ).distinct().select_related('class_group').order_by('class_group__name', 'name')

    for student in students_with_borrows:
        student.total_borrows = student.borrow_transactions.count()
        student.active_borrows = student.borrow_transactions.filter(status__in=['ISSUED', 'OVERDUE']).count()
        student.overdue_count = student.borrow_transactions.filter(status='OVERDUE').count()

    class_borrow_stats = ClassGroup.objects.filter(
        school=school,
        students__borrow_transactions__isnull=False
    ).distinct().annotate(
        borrower_count=Count('students__borrow_transactions', distinct=True),
        active_borrows=Count('students__borrow_transactions', filter=Q(students__borrow_transactions__status__in=['ISSUED', 'OVERDUE'])),
        overdue_count=Count('students__borrow_transactions', filter=Q(students__borrow_transactions__status='OVERDUE'))
    ).order_by('name')

    context = {
        'title': 'Library Reports',
        'total_students': total_students,
        'total_books': total_books,
        'total_borrowed': total_borrowed,
        'overdue_count': overdue_count,
        'on_time_percentage': on_time_percentage,
        'students_with_borrows': students_with_borrows,
        'class_borrow_stats': class_borrow_stats,
    }
    return render(request, 'dashboard/reports.html', context)


@login_required
def librarian_settings(request):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    context = {
        'title': 'Librarian Settings',
        'user': request.user,
    }
    return render(request, 'dashboard/settings.html', context)


@login_required
def class_lists_overview(request):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    school = request.user.school_profile.school

    classes = ClassGroup.objects.filter(school=school).order_by('name')

    class_summaries = []
    for cls in classes:
        total_students = cls.students.count()
        borrower_count = cls.students.filter(borrow_transactions__isnull=False).distinct().count()
        active_borrows = BorrowTransaction.objects.filter(
            student__class_group=cls,
            status__in=['ISSUED', 'OVERDUE']
        ).count()
        overdue = BorrowTransaction.objects.filter(
            student__class_group=cls,
            status='OVERDUE'
        ).count()

        class_summaries.append({
            'class_group': cls,
            'total_students': total_students,
            'borrower_count': borrower_count,
            'active_borrows': active_borrows,
            'overdue': overdue,
        })

    context = {
        'title': 'Class Lists',
        'class_summaries': class_summaries,
    }
    return render(request, 'dashboard/class_lists_overview.html', context)


@login_required
def class_detail(request, class_id):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    school = request.user.school_profile.school
    class_group = get_object_or_404(ClassGroup, id=class_id, school=school)

    students = Student.objects.filter(
        school=school,
        class_group=class_group
    ).order_by('name')

    for student in students:
        student.has_borrowed = student.borrow_transactions.exists()
        student.active_borrows = student.borrow_transactions.filter(status__in=['ISSUED', 'OVERDUE']).count()
        student.overdue_count = student.borrow_transactions.filter(status='OVERDUE').count()

    context = {
        'title': f'{class_group.name} - Student List',
        'class_group': class_group,
        'students': students,
    }
    return render(request, 'dashboard/class_detail.html', context)


@login_required
def library_stock(request):
    if not request.user.school_profile.is_librarian:
        return redirect('students:student_dashboard')

    school = request.user.school_profile.school

    stock_summary = Book.objects.filter(school=school).aggregate(
        total_copies=Sum('total_copies'),
        available_copies=Sum('available'),
    )

    total_copies = stock_summary['total_copies'] or 0
    available_copies = stock_summary['available_copies'] or 0
    borrowed_copies = total_copies - available_copies

    available_percentage = (available_copies / total_copies * 100) if total_copies > 0 else 0
    borrowed_percentage = (borrowed_copies / total_copies * 100) if total_copies > 0 else 0

    low_stock_books = Book.objects.filter(school=school, available__lte=2).order_by('available', 'title')
    for book in low_stock_books:
        book.borrowed_copies = book.total_copies - book.available

    all_books = Book.objects.filter(school=school).order_by('title')
    for book in all_books:
        book.borrowed_copies = book.total_copies - book.available

    context = {
        'title': 'Library Stock Summary',
        'total_copies': total_copies,
        'available_copies': available_copies,
        'borrowed_copies': borrowed_copies,
        'available_percentage': available_percentage,
        'borrowed_percentage': borrowed_percentage,
        'low_stock_books': low_stock_books,
        'all_books': all_books,
    }
    return render(request, 'dashboard/library_stock.html', context)


# ────────────────────────────────────────────────
#   Simplified Student Import (only 3 required fields)
# ────────────────────────────────────────────────

class ImportStudentsView(LoginRequiredMixin, View):
    template_name = 'students/import_students.html'

    def get(self, request):
        if not request.user.school_profile.is_librarian:
            messages.error(request, "Only librarians can import students.")
            return redirect('students:librarian_dashboard')
        return render(request, self.template_name)

    def post(self, request):
        if not request.user.school_profile.is_librarian:
            messages.error(request, "Only librarians can import students.")
            return redirect('students:librarian_dashboard')

        file = request.FILES.get('csv_file')
        if not file:
            messages.error(request, "No file uploaded.")
            return render(request, self.template_name)

        school = request.user.school_profile.school

        try:
            file_data = file.read().decode('utf-8')
            csv_file = StringIO(file_data)
            reader = csv.DictReader(csv_file)

            created = 0
            skipped = 0
            warnings = []

            for row in reader:
                student_id = row.get('student_id', '').strip()
                name = row.get('name', '').strip()
                class_name = row.get('class_group', '').strip()

                if not all([student_id, name, class_name]):
                    skipped += 1
                    warnings.append(f"Skipped row (missing required field): {row}")
                    continue

                try:
                    class_group = ClassGroup.objects.get(school=school, name__iexact=class_name)
                except ClassGroup.DoesNotExist:
                    skipped += 1
                    warnings.append(f"Class not found: '{class_name}' for student {student_id}")
                    continue

                if Student.objects.filter(school=school, student_id=student_id).exists():
                    skipped += 1
                    warnings.append(f"Student already exists: {student_id}")
                    continue

                Student.objects.create(
                    school=school,
                    student_id=student_id,
                    name=name,
                    class_group=class_group,
                    is_active=True,
                )
                created += 1

            messages.success(request, f"Successfully imported {created} students.")
            if skipped > 0:
                messages.warning(request, f"{skipped} rows were skipped.")
                for w in warnings[:10]:
                    messages.warning(request, w)
                if len(warnings) > 10:
                    messages.warning(request, f"...and {len(warnings)-10} more skipped rows.")

        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")

        return redirect('students:librarian_dashboard')


@login_required
def bulk_return(request):
    if not request.user.school_profile.is_librarian:
        messages.error(request, "Only librarians can return books.")
        return redirect('students:librarian_dashboard')

    if request.method == 'POST':
        borrow_ids = request.POST.getlist('borrow_ids')
        if not borrow_ids:
            messages.warning(request, "No books selected for return.")
            return redirect('students:returns_list')

        returned_count = 0
        for borrow_id in borrow_ids:
            try:
                borrow = BorrowTransaction.objects.get(id=borrow_id, status__in=['ISSUED', 'OVERDUE'])
                borrow.returned_date = timezone.now().date()
                borrow.status = 'RETURNED'
                borrow.save()

                # Increase book availability
                borrow.book.available = F('available') + 1
                borrow.book.save(update_fields=['available'])

                returned_count += 1
            except BorrowTransaction.DoesNotExist:
                continue

        if returned_count > 0:
            messages.success(request, f"Successfully returned {returned_count} book(s).")
        else:
            messages.warning(request, "No valid books were returned.")

    return redirect('students:returns_list')