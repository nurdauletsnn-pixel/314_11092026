from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    """Кастомная модель пользователя с RBAC-полями (раздел 8 спецификации)."""

    class Role(models.TextChoices):
        HQ_ADMIN = "HQ_ADMIN", "HQ Admin"
        BRANCH_DIRECTOR = "BRANCH_DIRECTOR", "Директор филиала"
        SALES_MANAGER = "SALES_MANAGER", "Менеджер продаж"

    role = models.CharField(max_length=30, choices=Role.choices, default=Role.SALES_MANAGER)
    branch = models.ForeignKey("Branch", null=True, blank=True, on_delete=models.PROTECT)

    def clean(self):
        super().clean()
        if self.role != self.Role.HQ_ADMIN and self.branch is None:
            raise ValidationError(
                {"branch": "Филиал обязателен для ролей, отличных от HQ_ADMIN."}
            )

    def __str__(self) -> str:
        return self.username


class Branch(models.Model):
    SEGMENT_SCHOOL = "SCHOOL"
    SEGMENT_KINDERGARTEN = "KINDERGARTEN"
    SEGMENT_FREE_SCHOOL = "FREE_SCHOOL"
    SEGMENT_CREATIVE = "CREATIVE"
    SEGMENT_CHOICES = [
        (SEGMENT_SCHOOL, "Школа"),
        (SEGMENT_KINDERGARTEN, "Детский сад"),
        (SEGMENT_FREE_SCHOOL, "Бесплатная школа (ГЧП)"),
        (SEGMENT_CREATIVE, "Креативные индустрии"),
    ]

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=30, unique=True)
    city = models.CharField(max_length=50)
    segment = models.CharField(max_length=30, choices=SEGMENT_CHOICES)
    shares_pricing_with = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    is_free = models.BooleanField(default=False)
    subsidy_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    def __str__(self) -> str:
        return self.name


class ClassQuota(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    grade_or_group = models.CharField(max_length=30)
    capacity = models.PositiveIntegerField()
    occupied = models.PositiveIntegerField(default=0)

    @property
    def is_full(self) -> bool:
        return self.occupied >= self.capacity

    def __str__(self) -> str:
        return f"{self.branch.code} :: {self.grade_or_group}"


class Funnel(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name


class Stage(models.Model):
    funnel = models.ForeignKey(Funnel, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField()
    color = models.CharField(max_length=7, default="#94A3B8")
    is_won = models.BooleanField(default=False)
    is_lost = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.name


class Contact(models.Model):
    CONTACT_TYPE_PARENT = "PARENT"
    CONTACT_TYPE_B2B = "B2B_REPRESENTATIVE"
    CONTACT_TYPE_CHOICES = [
        (CONTACT_TYPE_PARENT, "Родитель"),
        (CONTACT_TYPE_B2B, "Представитель компании"),
    ]

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, unique=True)
    iin = models.CharField(max_length=12, blank=True)
    email = models.EmailField(blank=True)
    contact_type = models.CharField(max_length=30, choices=CONTACT_TYPE_CHOICES, default=CONTACT_TYPE_PARENT)
    has_subsidy = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.full_name


class Child(models.Model):
    GRADE_BAND_PRESCHOOL = "PRESCHOOL"
    GRADE_BAND_PRIMARY_SECONDARY = "PRIMARY_SECONDARY"
    GRADE_BAND_SENIOR = "SENIOR"
    GRADE_BAND_CHOICES = [
        (GRADE_BAND_PRESCHOOL, "0 класс"),
        (GRADE_BAND_PRIMARY_SECONDARY, "1-11 класс"),
        (GRADE_BAND_SENIOR, "12 класс"),
    ]

    parent = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="children")
    full_name = models.CharField(max_length=200)
    grade_or_group = models.CharField(max_length=30, blank=True, default="")
    grade_band = models.CharField(max_length=30, choices=GRADE_BAND_CHOICES, blank=True)
    allergies = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    is_second_child = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.full_name


class Partner(models.Model):
    PARTNER_TYPE_CONSTRUCTION = "CONSTRUCTION"
    PARTNER_TYPE_MANAGEMENT = "MANAGEMENT"
    PARTNER_TYPE_BIART_RENTAL = "BIART_RENTAL"
    PARTNER_TYPE_CHOICES = [
        (PARTNER_TYPE_CONSTRUCTION, "Строительство"),
        (PARTNER_TYPE_MANAGEMENT, "Управление"),
        (PARTNER_TYPE_BIART_RENTAL, "Аренда зала BIART"),
    ]

    company_name = models.CharField(max_length=200)
    partner_type = models.CharField(max_length=30, choices=PARTNER_TYPE_CHOICES)
    contact_person = models.CharField(max_length=200)
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField(blank=True)
    bin_number = models.CharField(max_length=12, blank=True)

    def __str__(self) -> str:
        return self.company_name


class Tariff(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    grade_band = models.CharField(max_length=30, blank=True)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2)
    entrance_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    installments_count = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.branch.code} :: {self.name}"


class Deal(models.Model):
    STATUS_ACTIVE = "ACTIVE"
    STATUS_WON = "WON"
    STATUS_LOST = "LOST"
    STATUS_WAITLIST = "WAITLIST"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Активна"),
        (STATUS_WON, "Выиграна"),
        (STATUS_LOST, "Проиграна"),
        (STATUS_WAITLIST, "Лист ожидания"),
    ]

    funnel = models.ForeignKey(Funnel, on_delete=models.PROTECT)
    stage = models.ForeignKey(Stage, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    parent = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.CASCADE)
    child = models.ForeignKey(Child, null=True, blank=True, on_delete=models.SET_NULL)
    tariff = models.ForeignKey(Tariff, null=True, blank=True, on_delete=models.SET_NULL)
    has_food = models.BooleanField(default=False)
    has_transport = models.BooleanField(default=False)
    transport_zone = models.CharField(max_length=20, choices=[("CITY", "Город"), ("SUBURB", "Пригород")], blank=True)
    partner = models.ForeignKey(Partner, null=True, blank=True, on_delete=models.CASCADE)
    contract_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    discount_percent = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    is_cross_branch = models.BooleanField(default=False)
    # Гео-роутинг (раздел 8.5): что зафиксировала входящая форма
    source_city = models.CharField(max_length=50, null=True, blank=True)
    source_branch_requested = models.CharField(max_length=100, null=True, blank=True)
    # Анти-дубль (раздел 7, Риск 4): если контакт уже существовал — ссылка на исходный Contact
    is_duplicate_of = models.ForeignKey("Contact", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicate_deals")

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.funnel_id and self.funnel.slug == "b2b_partnership" and self.parent_id:
            raise ValidationError("B2B-сделка не может иметь Contact/Child.")
        if self.funnel_id and self.funnel.slug != "b2b_partnership" and self.partner_id:
            raise ValidationError("B2C-сделка не может иметь Partner.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def release_quota_slot(self):
        quota = ClassQuota.objects.filter(branch=self.branch, grade_or_group=self.child.grade_or_group if self.child else "").first()
        if quota is not None:
            quota.occupied = max(0, quota.occupied - 1)
            quota.save(update_fields=["occupied"])
        waitlist_deals = Deal.objects.filter(branch=self.branch, status=Deal.STATUS_WAITLIST, child__isnull=False).order_by("created_at")
        if self.child and self.child.grade_or_group:
            waitlist_deals = waitlist_deals.filter(child__grade_or_group=self.child.grade_or_group)
        self.status = Deal.STATUS_ACTIVE
        self.save(update_fields=["status"])
        ActivityLog.objects.create(deal=self, type="SYSTEM", actor="SYSTEM", content="Место в квоте освобождено, сделка переведена из листа ожидания.")
        return self

    def __str__(self) -> str:
        return f"{self.parent.full_name if self.parent else self.partner.company_name if self.partner else 'Deal'}"


class PaymentSchedule(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_PAID = "PAID"
    STATUS_OVERDUE = "OVERDUE"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_OVERDUE, "Overdue"),
    ]

    deal = models.ForeignKey(Deal, related_name="payment_schedules", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"


class Task(models.Model):
    PRIORITY_LOW = "LOW"
    PRIORITY_MEDIUM = "MEDIUM"
    PRIORITY_HIGH = "HIGH"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
    ]

    deal = models.ForeignKey(Deal, related_name="tasks", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    due_date = models.DateField()
    is_done = models.BooleanField(default=False)
    auto_generated = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)

    @property
    def is_completed(self) -> bool:
        return self.is_done


class ActivityLog(models.Model):
    TYPE_BOT_MESSAGE = "BOT_MESSAGE"
    TYPE_CALL = "CALL"
    TYPE_WHATSAPP = "WHATSAPP"
    TYPE_SYSTEM = "SYSTEM"
    TYPE_TASK = "TASK"
    TYPE_CHOICES = [
        (TYPE_BOT_MESSAGE, "Бот"),
        (TYPE_CALL, "Звонок"),
        (TYPE_WHATSAPP, "WhatsApp"),
        (TYPE_SYSTEM, "Система"),
        (TYPE_TASK, "Задача"),
    ]

    ACTOR_BOT = "BOT"
    ACTOR_MANAGER = "MANAGER"
    ACTOR_SYSTEM = "SYSTEM"
    ACTOR_CHOICES = [
        (ACTOR_BOT, "Бот"),
        (ACTOR_MANAGER, "Менеджер"),
        (ACTOR_SYSTEM, "Система"),
    ]

    deal = models.ForeignKey(Deal, related_name="activity", on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    actor = models.CharField(max_length=20, choices=ACTOR_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


class BotMessage(models.Model):
    deal = models.ForeignKey(Deal, related_name="bot_messages", on_delete=models.CASCADE)
    sender = models.CharField(max_length=20, choices=[("BOT", "Бот"), ("CLIENT", "Клиент")])
    text = models.TextField()
    field_filled = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)


