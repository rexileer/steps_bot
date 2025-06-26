from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class UserRoleChoices(models.TextChoices):
    USER = "USER", "Пользователь"
    ADMIN = "ADMIN", "Админ"


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    telegram_id = models.BigIntegerField(_("Telegram ID"), unique=True)
    username = models.CharField(_("username"), unique=True)

    phone = models.CharField(_("Телефон"), max_length=20, null=True, blank=True)
    balance = models.IntegerField(_("Баланс"), default=0)
    step_count = models.IntegerField(_("Шаги"), default=0)

    family = models.ForeignKey(
        "Family",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Семья"),
        related_name="+",
    )

    class Role(models.TextChoices):
        USER = "USER", "Пользователь"
        ADMIN = "ADMIN", "Админ"

    role = models.CharField(
        _("Роль"),
        max_length=10,
        choices=Role.choices,
        default=Role.USER
    )
    is_active = models.BooleanField(_("Активен"), default=True)

    created_at = models.DateTimeField(_("Создан"), default=timezone.now)
    updated_at = models.DateTimeField(_("Обновлён"), default=timezone.now)

    class Meta:
        db_table = "users"
        managed = False
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")

    def __str__(self):
        return str(self.telegram_id)


class Family(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(_("Название семьи"), max_length=100, unique=True)
    balance = models.IntegerField(_("Баланс"))
    step_count = models.IntegerField(_("Шаги"))

    class Meta:
        db_table = "families"
        managed = False
        verbose_name = _("Семья")
        verbose_name_plural = _("Семьи")

    def __str__(self):
        return self.name


class FamilyInvitation(models.Model):
    id = models.AutoField(primary_key=True)
    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        verbose_name=_("Семья"),
        related_name="invites",
    )
    inviter_id = models.BigIntegerField(_("Пригласил (User ID)"))
    invitee_id = models.BigIntegerField(_("Кого пригласили (User ID)"))
    status = models.CharField(_("Статус"), max_length=10)

    class Meta:
        db_table = "family_invitations"
        managed = False
        verbose_name = _("Приглашение в семью")
        verbose_name_plural = _("Приглашения в семью")

    def __str__(self):
        return f"{self.family} → {self.invitee_id}"


class WalkFormChoices(models.TextChoices):
    STROLLER = "STROLLER", _("С коляской")
    DOG = "DOG", _("С собакой")
    STROLLER_DOG = "STROLLER_DOG", _("С коляской и собакой")


class WalkFormCoefficient(models.Model):
    walk_form = models.CharField(
        _("Форма прогулки"),
        max_length=20,
        primary_key=True,
        choices=WalkFormChoices.choices,
    )
    coefficient = models.SmallIntegerField(_("Коэффициент"))

    class Meta:
        db_table = "walk_form_coefficients"
        managed = False
        verbose_name = _("Коэф. формы")
        verbose_name_plural = _("Коэф. форм")

    def __str__(self):
        return f"{self.get_walk_form_display()} = {self.coefficient}"


class TemperatureCoefficient(models.Model):
    id = models.AutoField(primary_key=True)
    walk_form = models.CharField(
        _("Форма прогулки"),
        max_length=20,
        choices=WalkFormChoices.choices,
    )

    min_temp_c = models.SmallIntegerField(_("Мин °C"))
    max_temp_c = models.SmallIntegerField(_("Макс °C"))
    coefficient = models.SmallIntegerField(_("Коэффициент"))

    class Meta:
        db_table = "temperature_coefficients"
        managed = False
        verbose_name = _("Температурная надбавка")
        verbose_name_plural = _("Температурные надбавки")

    def __str__(self):
        return (
            f"{self.get_walk_form_display()} "
            f"{self.min_temp_c} – {self.max_temp_c}°C"
        )


class Content(models.Model):
    id = models.AutoField(primary_key=True)
    slug = models.CharField(_("Ключ"), max_length=100, unique=True)
    text = models.TextField(_("Текст"))
    media_type = models.CharField(_("Тип медиа"), max_length=10)
    telegram_file_id = models.CharField(
        _("Telegram file_id"), max_length=255, null=True, blank=True
    )
    media_url = models.CharField(
        _("URL медиа"), max_length=1024, null=True, blank=True
    )

    class Meta:
        db_table = "contents"
        managed = False
        verbose_name = _("Контент-блок")
        verbose_name_plural = _("Контент-блоки")

    def __str__(self):
        return self.slug
