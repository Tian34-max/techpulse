# students/resources.py
from import_export import resources
from import_export.fields import Field
from .models import Student, ClassGroup
from schools.models import School


class FullStudentImportResource(resources.ModelResource):
    # Special handling for class_group (imported as name string)
    class_group = Field(column_name='class_group', attribute='class_group')

    # Special handling for school (imported as name or short_name)
    school = Field(column_name='school', attribute='school')

    class Meta:
        model = Student
        # NO field restriction → ALL fields are importable if present in CSV
        import_id_fields = ('student_id',)  # unique key for updates
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, row_result, **kwargs):
        # Convert class_group name → actual object PK
        class_name = row.get('class_group')
        if class_name:
            try:
                cg = ClassGroup.objects.get(name__iexact=class_name.strip())
                row['class_group'] = cg.pk
            except ClassGroup.DoesNotExist:
                row['class_group'] = None  # or raise error

        # Convert school name/short_name → PK
        school_val = row.get('school')
        if school_val:
            try:
                sch = School.objects.get(name__iexact=school_val.strip())
                row['school'] = sch.pk
            except School.DoesNotExist:
                try:
                    sch = School.objects.get(short_name__iexact=school_val.strip())
                    row['school'] = sch.pk
                except School.DoesNotExist:
                    row['school'] = None

    def after_import_row(self, row, row_result, **kwargs):
        # Optional: any post-import cleanup or logging
        pass