from django.db import models


class ClassGroup(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="e.g., S4A, P7 Blue, Form 5 Science, Senior 3 Green"
    )
    short_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Short code or abbreviation (optional)"
    )
    teacher_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Class teacher or form teacher name (optional)"
    )
    academic_year = models.CharField(
        max_length=9,
        default="2025/2026",
        help_text="Current academic year (e.g., 2025/2026)"
    )
    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='class_groups',
        verbose_name="School"
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Class / Grade Group"
        verbose_name_plural = "Classes / Grade Groups"

    def __str__(self):
        return f"{self.name} ({self.school.short_name if self.school else 'No school'})"


class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('P', 'Prefer not to say'),
    ]

    student_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique student registration/ID number"
    )
    name = models.CharField(
        max_length=150,
        help_text="Full name of the student"
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        help_text="Student's gender"
    )
    class_group = models.ForeignKey(
        ClassGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        help_text="The class/grade group the student belongs to"
    )
    roll_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Roll number within the class (optional)"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Student email (optional)"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Contact phone number (optional)"
    )
    photo = models.ImageField(
        upload_to='student_photos/',
        blank=True,
        null=True,
        help_text="Student passport photo (optional)"
    )
    admission_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date of admission to the school"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is the student currently active/enrolled?"
    )

    school = models.ForeignKey(
        'schools.School',
        on_delete=models.CASCADE,
        related_name='students',
        verbose_name="School"
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        class_str = self.class_group.name if self.class_group else "No class"
        school_str = self.school.short_name if self.school and hasattr(self.school, 'short_name') else "No school"
        return f"{self.name} ({self.student_id}) - {class_str} ({school_str})"