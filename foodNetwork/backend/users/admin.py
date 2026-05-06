from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):

    model = User

    list_display = (
        "username",
        "email",
        "is_producer",
        "is_staff",
        "is_active",
    )

    fieldsets = UserAdmin.fieldsets + (
        ("Marketplace Info", {
            "fields": ("is_producer", "postcode")
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Marketplace Info", {
            "fields": ("is_producer", "postcode")
        }),
    )


admin.site.register(User, CustomUserAdmin)