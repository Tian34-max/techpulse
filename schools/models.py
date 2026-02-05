from django.db import models
from django.conf import settings


class School(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="School Name")
    short_name = models.CharField(max_length=50, unique=True, verbose_name="Short Code")
    address = models.TextField(blank=True, verbose_name="Physical Address")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Phone Number")
    email = models.EmailField(blank=True, verbose_name="Email")
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True, verbose_name="School Logo")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "School"
        verbose_name_plural = "Schools"

    def __str__(self):
        return self.name


class UserSchoolProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='school_profile',
        verbose_name="User"
    )
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_profiles',
        verbose_name="Assigned School"
    )
    is_librarian = models.BooleanField(default=False, verbose_name="Is Librarian?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User School Profile"
        verbose_name_plural = "User School Profiles"

    def __str__(self):
        school_name = self.school.name if self.school else "No school"
        return f"{self.user.username} - {school_name}"