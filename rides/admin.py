from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from rides.models import Ride, RideEvent, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("id_user", "username", "email", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
    fieldsets = UserAdmin.fieldsets + (("Ride profile", {"fields": ("role", "phone_number")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Ride profile", {"fields": ("email", "role", "phone_number")}),
    )


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ("id_ride", "status", "rider", "driver", "pickup_time")
    list_filter = ("status",)
    search_fields = ("rider__email", "driver__email")
    list_select_related = ("rider", "driver")


@admin.register(RideEvent)
class RideEventAdmin(admin.ModelAdmin):
    list_display = ("id_ride_event", "ride", "description", "created_at")
    search_fields = ("description",)
    list_select_related = ("ride",)
