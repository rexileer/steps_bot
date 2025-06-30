from django.contrib import admin
from django.contrib.auth.models import Group, User as AuthUser

from core.models import (
    Family,
    FamilyInvitation,
    WalkFormCoefficient,
    TemperatureCoefficient,
    Content,
    User
)

admin.site.unregister(Group)
admin.site.unregister(AuthUser)


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "balance", "step_count")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(FamilyInvitation)
class FamilyInvitationAdmin(admin.ModelAdmin):
    list_display = ("id", "family", "inviter_id", "invitee_id", "status")
    list_filter = ("status", "family")
    search_fields = ("family__name", "invitee_id")


@admin.register(WalkFormCoefficient)
class WalkFormCoefficientAdmin(admin.ModelAdmin):
    list_display = ("walk_form", "coefficient")
    list_editable = ("coefficient",)
    ordering = ("walk_form",)


@admin.register(TemperatureCoefficient)
class TemperatureCoefficientAdmin(admin.ModelAdmin):
    list_display = ("walk_form", "min_temp_c", "max_temp_c", "coefficient")
    list_filter = ("walk_form",)
    list_editable = ("coefficient",)
    ordering = ("walk_form", "min_temp_c")


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ("slug", "media_type", "telegram_file_id", "media_url")
    list_editable = ("media_type", "telegram_file_id", "media_url")
    list_filter = ("media_type",)
    search_fields = ("slug",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id", "telegram_id", "username", "balance", "step_count",
        "role", "is_active", "family",
    )
    list_filter = ("role", "is_active")
    search_fields = ("telegram_id", "phone", "username")

    add_fieldsets = (
        (None, {
            "fields": (
                "telegram_id", "phone", "username",
                "balance", "step_count", "family",
            ),
        }),
    )

    fieldsets = (
        (None, {
            "fields": (
                "telegram_id", "username", "phone",
                "balance", "step_count", "family",
                "role", "is_active",
            ),
        }),
    )
