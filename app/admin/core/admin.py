from django.contrib import admin
from django.contrib.auth.models import Group, User as AuthUser

from core.models import (
    Family,
    FamilyInvitation,
    WalkFormCoefficient,
    TemperatureCoefficient,
    Content,
    User,
    FAQ,CatalogCategory,
    Product,
    OrderStatusChoices,
    Order,
    OrderItem,
    UserAddress,
    BotSetting,
    PromoGroup,
    PromoCode,
    Broadcast
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
    """
    Контент с медиа.
    """
    list_display = ("slug", "media_type", "file", "telegram_file_id", "media_url")
    list_editable = ("media_type", "telegram_file_id", "media_url")
    list_filter = ("media_type",)
    search_fields = ("slug",)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id", "telegram_id", "username", "phone", "email", "balance", "step_count",
        "role", "is_active", "family",
    )
    list_filter = ("role", "is_active")
    search_fields = ("telegram_id", "phone", "username")

    add_fieldsets = (
        (None, {
            "fields": (
                "telegram_id", "phone", "email", "username",
                "balance", "step_count", "family",
            ),
        }),
    )

    fieldsets = (
        (None, {
            "fields": (
                "telegram_id", "username", "phone", "email",
                "balance", "step_count", "family",
                "role", "is_active",
            ),
        }),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display  = ("slug", "question", "media_type", "telegram_file_id", "media_url")
    list_editable = ("media_type", "telegram_file_id", "media_url")
    search_fields = ("slug", "question")


@admin.register(CatalogCategory)
class CatalogCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "price", "is_active", "media_type")
    list_filter = ("category", "is_active", "media_type")
    search_fields = ("title",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "qty")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total_price", "created_at", "track_code")
    list_filter = ("status",)
    search_fields = ("id", "track_code", "user__telegram_id")
    inlines = (OrderItemInline,)


@admin.register(BotSetting)
class BotSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value")
    search_fields = ("key",)
from django.contrib import admin
from core.models import PromoGroup, PromoCode


class PromoCodeInline(admin.TabularInline):
    """
    Инлайн промокодов внутри группы.
    """
    model = PromoCode
    extra = 0
    fields = ("code", "max_uses", "used_count", "is_active")
    show_change_link = True
    can_delete = True


@admin.register(PromoGroup)
class PromoGroupAdmin(admin.ModelAdmin):
    """
    Управление группами промокодов.
    """
    list_display = ("id", "name", "discount_percent", "price_points", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    inlines = (PromoCodeInline,)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    """
    Управление отдельными промокодами.
    """
    list_display = ("id", "code", "group", "max_uses", "used_count", "is_active", "created_at")
    list_filter = ("is_active", "group")
    search_fields = ("code",)
    autocomplete_fields = ("group",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    fields = ("code", "group", "max_uses", "used_count", "is_active", "created_at")


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "scheduled_at", "sent_at")
    list_filter = ("status",)
    search_fields = ("id", "text")
    fields = ("text", "media_type", "media_file", "telegram_file_id", "media_url", "scheduled_at", "sent_at")
    readonly_fields = ("sent_at", "status")
