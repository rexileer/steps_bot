from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class UserRoleChoices(models.TextChoices):
    USER = "user", "Пользователь"
    ADMIN = "admin", "Админ"


class MediaTypeChoices(models.TextChoices):
    NONE = "none", "Нет"
    PHOTO = "photo", "Фото"
    VIDEO = "video", "Видео"


class WalkFormChoices(models.TextChoices):
    STROLLER = "stroller", _("С коляской")
    DOG = "dog", _("С собакой")
    STROLLER_DOG = "stroller_dog", _("С коляской и собакой")


class OrderStatusChoices(models.TextChoices):
    NEW = "new", "Новый"
    PAID = "paid", "Оплачен"
    SHIPPED = "shipped", "Отправлен"
    DELIVERED = "delivered", "Доставлен"


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


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    telegram_id = models.BigIntegerField(_("Telegram ID"), unique=True)
    username = models.CharField(_("username"), unique=True)
    phone = models.CharField(_("Телефон"), max_length=20, null=True, blank=True)
    email = models.CharField(_("Email"), max_length=255, null=True, blank=True)
    balance = models.IntegerField(_("Баланс"), default=0)
    step_count = models.IntegerField(_("Шаги"), default=0)
    family = models.ForeignKey(Family, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Семья"), related_name="+")
    role = models.CharField(_("Роль"), max_length=10, choices=UserRoleChoices.choices, default=UserRoleChoices.USER)
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


class FamilyInvitation(models.Model):
    id = models.AutoField(primary_key=True)
    family = models.ForeignKey(Family, on_delete=models.CASCADE, verbose_name=_("Семья"), related_name="invites")
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


class WalkFormCoefficient(models.Model):
    walk_form = models.CharField(_("Форма прогулки"), max_length=20, primary_key=True, choices=WalkFormChoices.choices)
    coefficient = models.SmallIntegerField(_("Коэффициент"))

    class Meta:
        db_table = "walk_form_coefficients"
        managed = False
        verbose_name = _("Форма прогулки")
        verbose_name_plural = _("Формы прогулки")

    def __str__(self):
        return f"{self.get_walk_form_display()} = {self.coefficient}"


class TemperatureCoefficient(models.Model):
    id = models.AutoField(primary_key=True)
    walk_form = models.CharField(_("Форма прогулки"), max_length=20, choices=WalkFormChoices.choices)
    min_temp_c = models.SmallIntegerField(_("Мин °C"))
    max_temp_c = models.SmallIntegerField(_("Макс °C"))
    coefficient = models.SmallIntegerField(_("Коэффициент"))

    class Meta:
        db_table = "temperature_coefficients"
        managed = False
        verbose_name = _("Температурная надбавка")
        verbose_name_plural = _("Температурные надбавки")

    def __str__(self):
        return f"{self.get_walk_form_display()} {self.min_temp_c}–{self.max_temp_c}°C"


class Content(models.Model):
    """
    Контент для сообщений бота с локальным файлом медиа.
    """
    id = models.AutoField(primary_key=True)
    slug = models.CharField(_("Ключ"), max_length=100, unique=True)
    text = models.TextField(_("Текст"))
    media_type = models.CharField(_("Тип медиа"), max_length=10, choices=MediaTypeChoices.choices, default=MediaTypeChoices.NONE)
    telegram_file_id = models.CharField(_("Telegram file_id"), max_length=255, null=True, blank=True)
    media_url = models.CharField(_("URL медиа"), max_length=1024, null=True, blank=True)
    file = models.FileField(_("Файл медиа"), upload_to="uploads/contents", null=True, blank=True, db_column="media_file")

    class Meta:
        db_table = "contents"
        managed = False
        verbose_name = _("Описание")
        verbose_name_plural = _("Описания")

    def __str__(self) -> str:
        return self.slug

    def save(self, *args, **kwargs) -> None:
        """
        Сбрасывает telegram_file_id при замене файла.
        """
        if self.pk and Content.objects.filter(pk=self.pk).exists():
            old = Content.objects.get(pk=self.pk)
            if old.file and old.file != self.file:
                self.telegram_file_id = None
        super().save(*args, **kwargs)


class FAQ(models.Model):
    id = models.AutoField(primary_key=True)
    slug = models.CharField(_("Ключ"), max_length=100, unique=True)
    question = models.CharField(_("Вопрос"), max_length=255)
    answer = models.TextField(_("Ответ"))
    media_type = models.CharField(_("Тип медиа"), max_length=10, choices=MediaTypeChoices.choices, default=MediaTypeChoices.NONE)
    telegram_file_id = models.CharField(_("Telegram file_id"), max_length=255, blank=True, null=True)
    media_url = models.CharField(_("URL медиа"), max_length=1024, blank=True, null=True)

    class Meta:
        db_table = "faq_items"
        managed = False
        verbose_name = _("FAQ-пункт")
        verbose_name_plural = _("FAQ-пункты")

    def __str__(self):
        return self.slug


class CatalogCategory(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(_("Название"), max_length=100, unique=True)

    class Meta:
        db_table = "catalog_categories"
        managed = False
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.AutoField(primary_key=True)
    category = models.ForeignKey(CatalogCategory, on_delete=models.SET_NULL, null=True, verbose_name=_("Категория"), related_name="+")
    title = models.CharField(_("Название"), max_length=120)
    description = models.TextField(_("Описание"))
    price = models.IntegerField(_("Цена, баллы"))
    media_type = models.CharField(_("Тип медиа"), max_length=10, choices=MediaTypeChoices.choices, default=MediaTypeChoices.NONE)
    telegram_file_id = models.CharField(_("Telegram file_id"), max_length=255, blank=True, null=True)
    media_url = models.CharField(_("URL медиа"), max_length=1024, blank=True, null=True)
    is_active = models.BooleanField(_("Активен"), default=True)

    class Meta:
        db_table = "products"
        managed = False
        verbose_name = _("Товар")
        verbose_name_plural = _("Товары")

    def __str__(self):
        return self.title


class Order(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_("Пользователь"))
    status = models.CharField(_("Статус"), max_length=10, choices=OrderStatusChoices.choices, default=OrderStatusChoices.NEW)
    total_price = models.IntegerField(_("Баллы"))
    pvz_id = models.CharField(_("ID ПВЗ"), max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(_("Создан"), auto_now_add=True)

    class Meta:
        db_table = "orders"
        managed = False
        verbose_name = _("Заказ")
        verbose_name_plural = _("Заказы")

    def __str__(self):
        return f"#{self.id}"


class OrderItem(models.Model):
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name=_("Заказ"))
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name=_("Товар"))
    qty = models.IntegerField(_("Кол-во"), default=1)

    class Meta:
        db_table = "order_items"
        managed = False
        verbose_name = _("Позиция заказа")
        verbose_name_plural = _("Позиции заказа")

    def __str__(self):
        return f"{self.product} ×{self.qty}"


class UserAddress(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    full_name = models.CharField(_("ФИО"), max_length=120)
    phone = models.CharField(_("Телефон"), max_length=20)
    city = models.CharField(_("Город"), max_length=60)
    street = models.CharField(_("Улица, дом, кв."), max_length=120)
    postcode = models.CharField(_("Индекс"), max_length=10)

    class Meta:
        db_table = "user_addresses"
        managed = False
        verbose_name = _("Адрес")
        verbose_name_plural = _("Адреса")

    def __str__(self):
        return f"{self.city}, {self.street}"


class BotSetting(models.Model):
    key = models.CharField(_("Ключ"), max_length=100, primary_key=True)
    value = models.TextField(_("Значение"))

    class Meta:
        db_table = "bot_settings"
        managed = False
        verbose_name = _("Настройка бота")
        verbose_name_plural = _("Настройки бота")

    def __str__(self):
        return f"{self.key} = {self.value}"


class PromoGroup(models.Model):
    """
    Группа промокодов с процентной скидкой.
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(_("Название"), max_length=60, unique=True)
    discount_percent = models.IntegerField(_("Скидка, %"), default=0)
    price_points = models.IntegerField(_("Цена, баллы"), default=0)
    is_active = models.BooleanField(_("Активна"), default=True)
    created_at = models.DateTimeField(_("Создана"), auto_now_add=True)

    class Meta:
        db_table = "promo_groups"
        managed = False
        verbose_name = _("Группа промокодов")
        verbose_name_plural = _("Группы промокодов")

    def __str__(self) -> str:
        return f"{self.name} ({self.discount_percent}%)"


class PromoCode(models.Model):
    """
    Промокод без сроков действия.
    """
    id = models.AutoField(primary_key=True)
    code = models.CharField(_("Код"), max_length=64, unique=True)
    group = models.ForeignKey(PromoGroup, on_delete=models.CASCADE, related_name="codes", verbose_name=_("Группа"))
    max_uses = models.IntegerField(_("Лимит использований"), default=1)
    used_count = models.IntegerField(_("Использовано"), default=0)
    is_active = models.BooleanField(_("Активен"), default=True)
    created_at = models.DateTimeField(_("Создан"), auto_now_add=True)

    class Meta:
        db_table = "promo_codes"
        managed = False
        verbose_name = _("Промокод")
        verbose_name_plural = _("Промокоды")

    def __str__(self) -> str:
        return self.code


class Broadcast(models.Model):
    id = models.AutoField(primary_key=True)
    text = models.TextField(_("Текст"), null=True, blank=True)
    media_type = models.CharField(_("Тип медиа"), max_length=10, choices=MediaTypeChoices.choices, default=MediaTypeChoices.NONE)
    telegram_file_id = models.CharField(_("Telegram file_id"), max_length=255, null=True, blank=True)
    media_url = models.CharField(_("URL медиа"), max_length=1024, null=True, blank=True)
    media_file = models.FileField(_("Файл медиа"), upload_to="uploads/broadcasts", null=True, blank=True)
    scheduled_at = models.DateTimeField(_("Отправить в"), null=True, blank=True)
    sent_at = models.DateTimeField(_("Отправлено"), null=True, blank=True)
    status = models.CharField(_("Статус"), max_length=10, default="pending")

    class Meta:
        db_table = "broadcasts"
        managed = False
        verbose_name = _("Рассылка")
        verbose_name_plural = _("Рассылки")


class Referral(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="referred_by", 
        verbose_name=_("Пользователь")
    )
    inviter = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="my_referrals", 
        verbose_name=_("Пригласивший")
    )
    reward_points = models.IntegerField(_("Начислено баллов"), default=0)
    created_at = models.DateTimeField(_("Дата регистрации"), default=timezone.now)

    class Meta:
        db_table = "referrals"
        managed = False
        verbose_name = _("Реферал")
        verbose_name_plural = _("Рефералы")

    def __str__(self):
        return f"{self.inviter.telegram_id} → {self.user.telegram_id}"


class PVZ(models.Model):
    """
    Пункт выдачи (ПВЗ) для доставки заказов.
    """
    id = models.CharField(_("ID"), max_length=64, primary_key=True)
    full_address = models.CharField(_("Полный адрес"), max_length=255)
    created_at = models.DateTimeField(_("Создан"), auto_now_add=True)

    class Meta:
        db_table = "pvz"
        managed = False
        verbose_name = _("Пункт выдачи")
        verbose_name_plural = _("Пункты выдачи")

    def __str__(self):
        return f"{self.full_address} ({self.id})"

