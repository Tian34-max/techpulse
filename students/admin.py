from django.contrib import admin
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import path, reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from .models import Student, ClassGroup
from schools.models import School
import csv
from io import StringIO


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name', 'class_group', 'school', 'gender', 'is_active')
    list_filter = ('class_group', 'school', 'gender', 'is_active')
    search_fields = ('student_id', 'name', 'email', 'roll_number')

    # Pass the batch import URL to the template
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['batch_import_url'] = reverse('admin:student_batch_import')
        return super().changelist_view(request, extra_context=extra_context)

    # ... rest of your code (get_urls, get_classes_ajax, batch_import_view) ...
    # Custom URLs
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('batch-import/', self.admin_site.admin_view(self.batch_import_view), name='student_batch_import'),
            path('batch-import/get-classes/', self.admin_site.admin_view(self.get_classes_ajax), name='student_get_classes'),
        ]
        return custom_urls + urls

    # AJAX: Load class groups for selected school
    @method_decorator(require_POST)
    def get_classes_ajax(self, request):
        school_id = request.POST.get('school_id')
        if not school_id:
            return JsonResponse({'classes': []})

        try:
            classes = ClassGroup.objects.filter(school_id=school_id).order_by('name')
            return JsonResponse({
                'classes': [{'id': c.id, 'name': str(c)} for c in classes]
            })
        except Exception as e:
            print("AJAX error:", str(e))  # Debug in terminal
            return JsonResponse({'classes': []})

    # Batch import main view
    def batch_import_view(self, request):
        if request.method == 'POST':
            school_id = request.POST.get('school')
            class_group_id = request.POST.get('class_group')
            csv_file = request.FILES.get('csv_file')

            if not all([school_id, class_group_id, csv_file]):
                messages.error(request, "Please select school, class group, and upload a CSV file.")
                return redirect('admin:student_batch_import')

            try:
                school = School.objects.get(id=school_id)
                class_group = ClassGroup.objects.get(id=class_group_id, school=school)
            except (School.DoesNotExist, ClassGroup.DoesNotExist):
                messages.error(request, "Invalid school or class group selected.")
                return redirect('admin:student_batch_import')

            # Read CSV and perform bulk validation
            try:
                file_data = csv_file.read().decode('utf-8')
                csv_reader = csv.DictReader(StringIO(file_data))

                errors = []
                valid_rows = []
                row_num = 1

                for row in csv_reader:
                    row_num += 1
                    student_id = row.get('student_id', '').strip()
                    name = row.get('name', '').strip()

                    if not student_id or not name:
                        errors.append(f"Row {row_num}: Missing student_id or name")
                        continue

                    if Student.objects.filter(student_id=student_id).exists():
                        errors.append(f"Row {row_num}: student_id {student_id} already exists")
                        continue

                    valid_rows.append({
                        'student_id': student_id,
                        'name': name,
                        'gender': row.get('gender', ''),
                        'roll_number': row.get('roll_number', ''),
                        'email': row.get('email', ''),
                        'phone': row.get('phone', ''),
                        'admission_date': row.get('admission_date') or None,
                        'is_active': row.get('is_active', 'True').lower() in ('true', '1', 'yes', 't', 'y'),
                    })

                if errors:
                    messages.error(request, f"Validation failed ({len(errors)} errors):\n" + "\n".join(errors[:10]))
                    if len(errors) > 10:
                        messages.error(request, f"...and {len(errors)-10} more errors.")
                    return redirect('admin:student_batch_import')

                # Save valid rows
                created = 0
                for data in valid_rows:
                    Student.objects.create(
                        student_id=data['student_id'],
                        name=data['name'],
                        school=school,
                        class_group=class_group,
                        gender=data['gender'],
                        roll_number=data['roll_number'],
                        email=data['email'],
                        phone=data['phone'],
                        admission_date=data['admission_date'],
                        is_active=data['is_active'],
                    )
                    created += 1

                messages.success(request, f"Successfully imported {created} students.")
                return redirect('admin:students_student_changelist')

            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                return redirect('admin:student_batch_import')

        # GET: show the form
        schools = School.objects.all()
        classes = ClassGroup.objects.none()

        context = {
            'title': 'Batch Import Students',
            'schools': schools,
            'classes': classes,
            'opts': self.model._meta,
            'app_label': self.model._meta.app_label,
            'model_name': self.model._meta.model_name,
            'has_view_permission': True,
            'site_header': admin.site.site_header,
            'site_title': admin.site.site_title,
            'index_title': admin.site.index_title,
            'current_app': self.admin_site.name,
        }
        return render(request, 'admin/batch_import_students.html', context)


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'student_count')
    list_filter = ('school',)
    search_fields = ('name',)

    def student_count(self, obj):
        return obj.students.count()

    student_count.short_description = 'Students'