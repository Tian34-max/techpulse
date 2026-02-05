from django.contrib import admin


class SchoolFilteredAdmin(admin.ModelAdmin):
    """
    Base admin class that filters querysets by the current user's school.
    Superusers see all data; normal users see only their assigned school.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Superuser sees everything
        # For normal users: filter by their assigned school
        try:
            profile = request.user.school_profile
            if profile.school:
                return qs.filter(school=profile.school)
        except AttributeError:
            pass
        # If no profile or no school → show nothing
        return qs.none()