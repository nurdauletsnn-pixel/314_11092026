from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from decimal import Decimal

from django.db import models, transaction
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .business_logic import build_pricing_summary, calculate_total, get_initial_stage
from .services.automation import check_payment_deadlines as run_check_payment_deadlines, notify_waitlist_next
from .services.tariff_engine import calculate_tariff_preview, check_second_child_discount, generate_payment_schedule
from .models import ActivityLog, BotMessage, Branch, Child, ClassQuota, Contact, Deal, Funnel, Partner, PaymentSchedule, Stage, Tariff, Task, User
from .permissions import IsHQAdmin, IsHQAdminOrBranchDirector, IsHQAdminOrReadOnly
from .serializers import BranchSerializer, ChildSerializer, ContactSerializer, DealSerializer, PaymentScheduleSerializer, TaskSerializer, UserSerializer

logger = logging.getLogger(__name__)


def _format_schedules(schedules):
    for item in schedules:
        if "amount" in item:
            item["amount"] = str(item["amount"])
    return schedules


class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer

    def get_queryset(self):
        qs = Contact.objects.prefetch_related("children").all()
        user = self.request.user
        if user.role != User.Role.HQ_ADMIN:
            qs = qs.filter(deal_set__branch=user.branch).distinct()
        return qs

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == User.Role.HQ_ADMIN:
            return True
        if user.branch is None:
            return False
        return obj.deal_set.filter(branch=user.branch).exists()

    @action(detail=False, methods=["get"], url_path="check-duplicate")
    def check_duplicate(self, request):
        """Анти-дубль (раздел 7, Риск 4): ищет Contact по всей БД,
        не ограничиваясь филиалом текущего пользователя.

        GET /api/contacts/check-duplicate/?phone=...&iin=...
        Возвращает { exists, contact, branch } — branch поможет показать
        плашку «Контакт найден в филиале X».
        """
        phone = request.query_params.get("phone", "").strip()
        iin = request.query_params.get("iin", "").strip()

        contact = None
        if phone:
            contact = Contact.objects.filter(phone=phone).first()
        if contact is None and iin:
            contact = Contact.objects.filter(iin=iin).first()

        if contact is None:
            return Response({"exists": False, "contact": None, "branch": None})

        deal = contact.deal_set.select_related("branch").first()
        branch = deal.branch if deal else None
        return Response({
            "exists": True,
            "contact": ContactSerializer(contact).data,
            "branch": BranchSerializer(branch).data if branch else None,
        })


class ChildViewSet(viewsets.ModelViewSet):
    serializer_class = ChildSerializer

    def get_queryset(self):
        qs = Child.objects.select_related("parent").all()
        user = self.request.user
        if user.role != User.Role.HQ_ADMIN:
            qs = qs.filter(deal_set__branch=user.branch).distinct()
        return qs

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == User.Role.HQ_ADMIN:
            return True
        if user.branch is None:
            return False
        return obj.deal_set.filter(branch=user.branch).exists()


class PaymentScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentScheduleSerializer

    def get_queryset(self):
        qs = PaymentSchedule.objects.select_related("deal__branch").all()
        user = self.request.user
        if user.role != User.Role.HQ_ADMIN:
            qs = qs.filter(deal__branch=user.branch)
        return qs

    def get_permissions(self):
        if self.action in ("mark_paid", "destroy"):
            return [IsHQAdminOrBranchDirector()]
        return [IsAuthenticated()]

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == User.Role.HQ_ADMIN:
            return True
        return obj.deal.branch_id == user.branch_id

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        schedule = self.get_object()
        schedule.status = PaymentSchedule.STATUS_PAID
        schedule.save(update_fields=["status"])
        return Response(PaymentScheduleSerializer(schedule).data)


class TariffViewSet(viewsets.ViewSet):
    """Тарифы и калькулятор (раздел 6): /api/tariffs/calculate/."""

    @action(detail=False, methods=["get"], url_path="calculate")
    def calculate(self, request):
        """Предварительный расчёт тарифа без сохранения (для UI-калькулятора).

        Query params: branch, tariff, grade_band, has_food, has_transport,
                      transport_zone, is_second_child, has_subsidy.
        """
        branch = request.query_params.get("branch")
        tariff = request.query_params.get("tariff")
        grade_band = request.query_params.get("grade_band") or "PRIMARY_SECONDARY"
        has_food = request.query_params.get("has_food", "false").lower() in ("true", "1")
        has_transport = request.query_params.get("has_transport", "false").lower() in ("true", "1")
        transport_zone = request.query_params.get("transport_zone", "CITY")
        is_second_child = request.query_params.get("is_second_child", "false").lower() in ("true", "1")
        has_subsidy = request.query_params.get("has_subsidy", "false").lower() in ("true", "1")

        if not branch:
            return Response({"error": "Параметр branch обязателен."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            summary = calculate_tariff_preview(
                branch_code=branch,
                tariff_name=tariff,
                grade_band=grade_band,
                has_food=has_food,
                has_transport=has_transport,
                transport_zone=transport_zone,
                is_second_child=is_second_child,
                has_subsidy=has_subsidy,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Decimal -> str для JSON-сериализации
        summary["total_amount"] = str(summary["total_amount"])
        summary["entrance_fee"] = str(summary["entrance_fee"])
        for item in summary.get("schedules", []):
            item["amount"] = str(item["amount"])
        return Response(summary)


class TaskViewSet(viewsets.ModelViewSet):
    """Задачи и уведомления (раздел 6 п.4): /api/tasks/."""

    serializer_class = TaskSerializer

    def get_queryset(self):
        qs = Task.objects.select_related("deal", "deal__branch", "assigned_to").all()
        user = self.request.user
        if user.role == User.Role.HQ_ADMIN:
            return qs
        if user.role == User.Role.BRANCH_DIRECTOR:
            return qs.filter(deal__branch=user.branch)
        # SALES_MANAGER: свои задачи ИЛИ задачи своего филиала
        return qs.filter(models.Q(assigned_to=user) | models.Q(deal__branch=user.branch))


class DealViewSet(viewsets.ModelViewSet):
    serializer_class = DealSerializer

    def get_queryset(self):
        qs = (
            Deal.objects.select_related("parent", "child", "branch", "funnel", "stage", "tariff", "partner")
            .prefetch_related("payment_schedules", "activity", "bot_messages")
            .all()
        )
        user = self.request.user
        if user.role == User.Role.HQ_ADMIN:
            return qs
        # Не-HQ роли (SALES_MANAGER / BRANCH_DIRECTOR) видят ТОЛЬКО сделки
        # своего филиала. Если филиал не привязан (branch=None) — возвращаем
        # пустой queryset, чтобы менеджер не видел чужие (или все) сделки.
        if user.branch_id is None:
            return Deal.objects.none()
        return qs.filter(branch=user.branch)

    def get_permissions(self):
        if self.action == "destroy":
            return [IsHQAdminOrBranchDirector()]
        return [IsAuthenticated()]

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == User.Role.HQ_ADMIN:
            return True
        if obj.branch_id != user.branch_id:
            return False
        if self.action in ("destroy",):
            return user.role == User.Role.BRANCH_DIRECTOR
        return True

    def _ensure_funnel_stage(self, funnel_slug: str, stage_name: str | None = None):
        funnel, _ = Funnel.objects.get_or_create(slug=funnel_slug, defaults={"name": funnel_slug.replace("-", " ").title()})
        if stage_name:
            stage, _ = Stage.objects.get_or_create(funnel=funnel, name=stage_name, defaults={"order": 1})
        else:
            stage = funnel.stages.order_by("order").first() or Stage.objects.create(funnel=funnel, name="Qualification", order=1)
        return funnel, stage

    def _ensure_branch(self, code: str):
        branch, _ = Branch.objects.get_or_create(
            code=code,
            defaults={"name": code.replace("_", " ").title(), "city": "Астана", "segment": Branch.SEGMENT_SCHOOL},
        )
        return branch

    def _ensure_tariff(self, branch: Branch, tariff_name: str, grade_band: str):
        tariff, _ = Tariff.objects.get_or_create(
            branch=branch,
            name=tariff_name,
            grade_band=grade_band,
            defaults={"base_amount": Decimal("0.00"), "entrance_fee": Decimal("0.00"), "installments_count": 1},
        )
        return tariff

    def _resolve_branch_code(self, requested: str) -> str:
        user = self.request.user
        if user.role != User.Role.HQ_ADMIN and user.branch is not None:
            return user.branch.code
        return requested or "RIVIERA"

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        parent_profile = data.pop("parent_profile", None)
        child_profile = data.pop("child_profile", None)
        partner_profile = data.pop("partner_profile", None)
        # Анти-дубль: если фронт нашёл существующий Contact и передал его id — используем его,
        # НЕ создавая новый Contact (раздел 7, Риск 4).
        contact_id = data.get("contact_id")
        # Гео-роутинг (раздел 8.5)
        source_city = data.get("source_city") or None
        source_branch_requested = data.get("source_branch_requested") or None
        funnel_slug = data.get("funnel_slug") or data.get("pipeline") or "b2c_schools"
        branch_code = self._resolve_branch_code(data.get("branch"))
        tariff_name = data.get("tariff") or "Стандарт"
        has_food = data.get("has_food", False)
        has_transport = data.get("has_transport", False)
        transport_zone = data.get("transport_zone", "CITY")
        is_waitlisted = data.get("is_waitlisted", False)
        grade_band = data.get("grade_band") or "PRIMARY_SECONDARY"
        child_grade = child_profile.get("grade_or_group") if child_profile else None

        with transaction.atomic():
            funnel, stage = self._ensure_funnel_stage(funnel_slug, "Qualification")
            branch = self._ensure_branch(branch_code)
            tariff = self._ensure_tariff(branch, tariff_name, grade_band)
            child = None
            parent = None
            partner = None
            is_duplicate_of = None

            if partner_profile:
                partner = Partner.objects.create(**partner_profile)
                deal = Deal.objects.create(
                    funnel=funnel,
                    stage=stage,
                    branch=branch,
                    partner=partner,
                    contract_value=data.get("contract_value"),
                    total_amount=data.get("contract_value") or Decimal("0"),
                    source_city=source_city,
                    source_branch_requested=source_branch_requested,
                    is_cross_branch=bool(
                        source_branch_requested
                        and source_branch_requested != branch.code
                    ),
                )
            else:
                # Анти-дубль: используем существующий Contact, если передан contact_id
                if contact_id:
                    parent = Contact.objects.filter(pk=contact_id).first()
                    is_duplicate_of = parent
                if parent is None:
                    parent = Contact.objects.create(**parent_profile) if parent_profile else Contact.objects.create(full_name="New lead", phone=f"+7701{random.randint(1000000, 9999999)}", contact_type=Contact.CONTACT_TYPE_PARENT)
                child = Child.objects.create(parent=parent, **child_profile) if child_profile else Child.objects.create(parent=parent, full_name="New child", grade_or_group="1 класс", grade_band=grade_band)
                total_amount = calculate_total(branch_code=branch.code, grade_band=grade_band, tariff_name=tariff_name, has_food=has_food, has_transport=has_transport, transport_zone=transport_zone, has_second_child_discount=bool(child.is_second_child), has_subsidy=parent.has_subsidy)
                deal = Deal.objects.create(
                    funnel=funnel,
                    stage=stage,
                    branch=branch,
                    parent=parent,
                    child=child,
                    tariff=tariff,
                    has_food=has_food,
                    has_transport=has_transport,
                    transport_zone=transport_zone,
                    total_amount=total_amount,
                    status=Deal.STATUS_WAITLIST if is_waitlisted else Deal.STATUS_ACTIVE,
                    source_city=source_city,
                    source_branch_requested=source_branch_requested,
                    is_cross_branch=bool(
                        source_branch_requested
                        and source_branch_requested != branch.code
                    ),
                    is_duplicate_of=is_duplicate_of,
                )

            summary = build_pricing_summary(branch.code, tariff_name, has_food=has_food, has_transport=has_transport, is_second_child=child.is_second_child if child else False, grade=child_grade or "1", meals=3)
            deal.total_amount = summary["total_amount"]
            deal.save(update_fields=["total_amount"])
            PaymentSchedule.objects.filter(deal=deal).delete()
            for index, item in enumerate(summary["schedules"]):
                PaymentSchedule.objects.create(deal=deal, title=item["title"], due_date=deal.created_at.date() + timedelta(days=15 * (index + 1)), amount=item["amount"], status=item["status"])

        return Response(DealSerializer(deal).data, status=status.HTTP_201_CREATED)

    # Системные slug стадий канбана → ИМЕНА стадий в Django (созданы generate_mock_data).
    # Фронт отправляет в PATCH строгий slug ('entrance_fee', 'enrolled', ...), а не
    # человекочитаемый заголовок колонки — иначе создаются ДУБЛИКАТЫ Stage'ов.
    #
    # ВАЖНО: имена стадий РАЗЛИЧАЮТСЯ по воронкам — для b2c_kindergarten нет
    # "Contract Signed" (там "Won"), для b2b_partnership — "Deal Closed".
    FUNNEL_STAGE_SLUG_TO_NAME = {
        "b2c_kindergarten": {
            "new": "New Lead", "qualification": "Qualification",
            "trial_scheduled": "Free Trial Day Set", "adaptation": "Adaptation Period",
            "entrance_fee": "Entrance Fee", "contract_signing": "Entrance Fee",
            "first_month_paid": "Monthly Payment", "monthly payment": "Monthly Payment",
            "enrolled": "Won", "won": "Won", "lost": "Lost",
        },
        "b2b_partnership": {
            "new": "Primary Contact", "qualification": "Qualification/Meeting",
            "meeting": "Qualification/Meeting", "commercial_offer": "Commercial Proposal",
            "contract_negotiation": "Contract/Tender Negotiation",
            "invoice_sent": "Invoicing", "enrolled": "Deal Closed",
            "won": "Deal Closed", "lost": "Lost",
        },
    }

    STAGE_SLUG_TO_NAME = {
        # B2C Schools / Kindergarten
        "new": "Unsorted", "new-lead": "Unsorted", "new_lead": "Unsorted", "unsorted": "Unsorted",
        "qualification": "Qualification", "qualification/meeting": "Qualification",
        "tour_scheduled": "Tour/Test Scheduled", "tour": "Tour/Test Scheduled", "tour scheduled": "Tour/Test Scheduled",
        "testing": "Tour/Test Passed", "tour/test passed": "Tour/Test Passed",
        "contract_signing": "Tariff & Addons Selection", "contract": "Tariff & Addons Selection",
        "tariff & addons selection": "Tariff & Addons Selection", "tariff selection": "Tariff & Addons Selection",
        "entrance_fee": "Entrance Fee Paid", "entrance-fee": "Entrance Fee Paid", "entrance fee paid": "Entrance Fee Paid",
        "enrolled": "Contract Signed", "contract signed": "Contract Signed", "won": "Contract Signed", "monthly payment": "Monthly Payment",
        # Kindergarten специфичные
        "trial_scheduled": "Free Trial Day Set", "trial-day": "Free Trial Day Set", "free trial day set": "Free Trial Day Set",
        "adaptation": "Adaptation Period", "adaptation period": "Adaptation Period",
        "first_month_paid": "Won", "first month paid": "Monthly Payment",
        # B2B
        "meeting": "Qualification/Meeting",
        "commercial_offer": "Commercial Proposal", "commercial offer": "Commercial Proposal", "commercial proposal": "Commercial Proposal",
        "contract_negotiation": "Contract/Tender Negotiation", "negotiation": "Contract/Tender Negotiation",
        "invoice_sent": "Invoicing", "invoice sent": "Invoicing", "invoicing": "Invoicing",
        "deal closed": "Deal Closed",
        "lost": "Lost",
    }

    def partial_update(self, request, *args, **kwargs):
        deal = self.get_object()

        # RBAC (раздел 8.2/8.4): PATCH использует permission [IsAuthenticated],
        # у которого нет has_object_permission — поэтому НЕ-HQ пользователь мог бы
        # редактировать/перетаскивать сделки чужого филиала. Явная объектная проверка:
        user = request.user
        if (
            user
            and user.is_authenticated
            and user.role != User.Role.HQ_ADMIN
            and user.branch_id != deal.branch_id
        ):
            return Response(
                {"error": "У вас нет доступа к сделкам этого филиала."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy()
        parent_profile = data.pop("parent_profile", None)
        child_profile = data.pop("child_profile", None)

        # Drag-and-Drop: фронт отправляет СИСТЕМНЫЙ slug стадии ('entrance_fee', ...).
        # Резолвим его в реальное ИМЯ стадии и ищем/создаём Stage в воронке сделки.
        stage_value = data.get("stage")
        if isinstance(stage_value, str) and stage_value.strip() and not stage_value.strip().isdigit():
            raw_stage = stage_value.strip().lower()
            # Сначала ищем по воронке (Kindergarten/B2B), потом по общей таблице.
            funnel_map = self.FUNNEL_STAGE_SLUG_TO_NAME.get(deal.funnel.slug, {})
            stage_name = (
                funnel_map.get(raw_stage)
                or self.STAGE_SLUG_TO_NAME.get(raw_stage)
                or raw_stage
            )
            # Ищем СУЩЕСТВУЮЩУЮ стадию по имени (без создания дубликатов).
            stage_obj = Stage.objects.filter(funnel=deal.funnel, name__iexact=stage_name).first()
            # Fallback для воронок, где имя слегка отличается (например "Entrance Fee" без "Paid").
            if stage_obj is None and raw_stage in self.STAGE_SLUG_TO_NAME:
                for needle in stage_name.split():
                    if len(needle) < 3:
                        continue
                    stage_obj = Stage.objects.filter(funnel=deal.funnel, name__icontains=needle).first()
                    if stage_obj is not None:
                        break
            if stage_obj is None:
                _, stage_obj = self._ensure_funnel_stage(deal.funnel.slug, stage_name)
            data["stage"] = stage_obj.pk

        # Раздел 7 (Риск 2): при переводе занятой сделки в LOST —
        # продвигаем первую сделку из WAITLIST по тому же филиалу/классу.
        new_status = data.get("status")
        if new_status == Deal.STATUS_LOST and deal.status != Deal.STATUS_LOST:
            grade_or_group = deal.child.grade_or_group if deal.child else ""
            notify_waitlist_next(deal.branch, grade_or_group)

        serializer = self.get_serializer(deal, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if parent_profile and deal.parent:
            for field_name in ("full_name", "phone", "iin", "email", "contact_type", "has_subsidy"):
                value = parent_profile.get(field_name)
                if value is not None:
                    setattr(deal.parent, field_name, value)
            deal.parent.save()

        if child_profile and deal.child:
            for field_name in ("full_name", "grade_or_group", "grade_band", "allergies", "birth_date", "is_second_child"):
                value = child_profile.get(field_name)
                if value is not None:
                    setattr(deal.child, field_name, value)
            deal.child.save()

        return Response(self.get_serializer(deal).data)

    @action(detail=False, methods=["post"], url_path="simulate-lead")
    def simulate_lead(self, request):
        """Симуляция лидов: Стандартный / Кросс-филиальный / Вайтлист / Дубликат.

        Гарантирует, что Deal получает корректный stage, branch, тариф и сумму.
        Любая ошибка логируется и возвращается как 400/500 с понятным текстом,
        чтобы сервер не падал без контекста.
        """
        try:
            with transaction.atomic():
                funnel_slug = request.data.get("funnel_slug") or request.data.get("pipeline") or "b2c_schools"
                funnel, stage = self._ensure_funnel_stage(funnel_slug, "Qualification")
                if stage is None:
                    stage = funnel.stages.order_by("order").first()
                if stage is None:
                    stage = Stage.objects.create(funnel=funnel, name="Qualification", order=1)

                branch_code = self._resolve_branch_code(request.data.get("branch") or random.choice(["RIVIERA", "QUANTUM_STEM", "ALDI_BI_CAPITAL_PARK"]))
                branch = self._ensure_branch(branch_code)

                # Нормализация тарифа: подбираем ТОЛЬКО совместимый с филиалом,
                # иначе build_pricing_summary/calculate_total упадут с KeyError/ValueError.
                if branch.code == "RIVIERA":
                    tariff_choices = ["Выгодный", "Стандарт", "Стандарт Плюс"]
                elif branch.code in {"QUANTUM_STEM", "QUANTUM_TECH"}:
                    tariff_choices = ["Основной (9 траншей)", "3 транша"]
                else:
                    tariff_choices = ["Стандарт", "Выгодный"]
                requested_tariff = request.data.get("tariff")
                tariff_name = requested_tariff if requested_tariff in tariff_choices else random.choice(tariff_choices)

                grade_band = request.data.get("grade_band") or random.choice(["PRESCHOOL", "PRIMARY_SECONDARY", "SENIOR"])
                has_food = random.choice([True, False])
                has_transport = random.choice([True, False])
                transport_zone = random.choice(["CITY", "SUBURB"])
                has_subsidy = random.choice([True, False])
                is_second_child = random.choice([True, False])
                full_name = random.choice(["Айгуль Серикова", "Нурлан Токтаев", "Мадина Оспанова", "Аслан Жумабаев", "Динара Бекетова"])

                # Сценарий «Дубликат»: фронт передаёт существующий phone — используем его Contact.
                phone = request.data.get("phone") or f"+7701{random.randint(1000000, 9999999)}"
                parent = Contact.objects.filter(phone=phone).first()
                is_duplicate_of = parent
                if parent is None:
                    while Contact.objects.filter(phone=phone).exists():
                        phone = f"+7701{random.randint(1000000, 9999999)}"
                    parent = Contact.objects.create(
                        full_name=full_name,
                        phone=phone,
                        email=f"parent{random.randint(1, 999)}@example.com",
                        contact_type=Contact.CONTACT_TYPE_PARENT,
                        has_subsidy=has_subsidy,
                    )

                # Сценарий «Waitlist»: фронт может передать конкретный класс/группу.
                grade_or_group = request.data.get("grade_or_group") or random.choice(["0 класс", "1 класс", "5 класс", "7 класс", "10 класс"])
                child = Child.objects.create(
                    parent=parent,
                    full_name=random.choice(["Аружан", "Нурали", "Дарина", "Рамазан", "Аня"]),
                    grade_or_group=grade_or_group,
                    grade_band=grade_band,
                    is_second_child=is_second_child,
                )
                tariff = self._ensure_tariff(branch, tariff_name, grade_band)

                # Корректная сумма: тариф совместим с филиалом, поэтому расчёт не падает.
                summary = build_pricing_summary(
                    branch.code,
                    tariff_name,
                    has_food=has_food,
                    has_transport=has_transport,
                    is_second_child=is_second_child,
                    grade=child.grade_or_group,
                    meals=3,
                )

                quota = ClassQuota.objects.filter(branch=branch, grade_or_group=child.grade_or_group).first()
                deal_status = Deal.STATUS_ACTIVE
                if quota is not None and quota.is_full:
                    deal_status = Deal.STATUS_WAITLIST

                # Сценарий «Кросс-филиальный» (гео-роутинг, раздел 8.5).
                source_city = request.data.get("source_city") or None
                source_branch_requested = request.data.get("source_branch_requested") or None
                is_cross_branch = bool(source_branch_requested and source_branch_requested != branch.code)

                deal = Deal.objects.create(
                    funnel=funnel,
                    stage=stage,
                    branch=branch,
                    parent=parent,
                    child=child,
                    tariff=tariff,
                    has_food=has_food,
                    has_transport=has_transport,
                    transport_zone=transport_zone,
                    total_amount=summary["total_amount"],
                    status=deal_status,
                    source_city=source_city,
                    source_branch_requested=source_branch_requested,
                    is_cross_branch=is_cross_branch,
                    is_duplicate_of=is_duplicate_of,
                )
                if quota is not None:
                    quota.occupied += 1
                    quota.save(update_fields=["occupied"])
                PaymentSchedule.objects.filter(deal=deal).delete()
                for index, item in enumerate(summary["schedules"]):
                    PaymentSchedule.objects.create(
                        deal=deal,
                        title=item["title"],
                        due_date=deal.created_at.date() + timedelta(days=15 * (index + 1)),
                        amount=item["amount"],
                        status=item["status"],
                    )
                BotMessage.objects.create(deal=deal, sender="BOT", text="Здравствуйте! Подскажите, какой тариф и дополнительные услуги вам подходят?", field_filled="tariff")
                BotMessage.objects.create(deal=deal, sender="BOT", text=f"Автозаполнение: филиал {branch.name}, тариф {tariff_name}.", field_filled="profile")
                if deal_status == Deal.STATUS_WAITLIST:
                    ActivityLog.objects.create(deal=deal, type="SYSTEM", actor="SYSTEM", content="Класс заполнен, лид переведён в лист ожидания")

            return Response(
                {
                    "deal": DealSerializer(deal).data,
                    "toast": {"type": "success", "message": "Lead generated and routed to the first pipeline stage."},
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            # Подробное логирование, чтобы сервер не падал с 500 без контекста.
            logger.exception("Simulate lead failed (pipeline=%s): %s", request.data.get("pipeline"), exc)
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Ошибка симуляции лида: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"], url_path="metadata")
    def metadata(self, request):
        """Return available branches and tariffs to power frontend selects."""
        user = request.user
        if user.role == User.Role.HQ_ADMIN:
            branches = Branch.objects.all()
        else:
            branches = Branch.objects.filter(pk=user.branch_id)
        branches = list(branches.values("id", "name", "code", "city", "segment", "is_free", "subsidy_amount"))
        tariffs = list(Tariff.objects.filter(branch_id__in=[b["id"] for b in branches]).values("id", "branch_id", "name", "grade_band", "base_amount", "entrance_fee", "installments_count"))
        return Response({"branches": branches, "tariffs": tariffs})

    @action(detail=False, methods=["post"], url_path="pricing")
    def pricing(self, request):
        """Compute pricing summary without creating a deal.

        Expects: branch (code), tariff (name), has_food, has_transport, is_second_child, grade, meals, transport_zone
        """
        payload = request.data or {}
        branch_code = payload.get("branch")
        if request.user.role != User.Role.HQ_ADMIN:
            branch_code = request.user.branch.code if request.user.branch else branch_code
        tariff_name = payload.get("tariff")
        has_food = bool(payload.get("has_food", False))
        has_transport = bool(payload.get("has_transport", False))
        is_second_child = bool(payload.get("is_second_child", False))
        grade = payload.get("grade", "1")
        meals = int(payload.get("meals", 3))
        try:
            summary = build_pricing_summary(branch_code, tariff_name, has_food=has_food, has_transport=has_transport, is_second_child=is_second_child, grade=grade, meals=meals)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        # Make Decimal serializable
        for k in ("total_amount", "entrance_fee"):
            if k in summary:
                summary[k] = str(summary[k])
        summary["schedules"] = _format_schedules(summary.get("schedules", []))
        return Response(summary)

    @action(detail=True, methods=["post"], url_path="simulate-overdue")
    def simulate_overdue(self, request, pk=None):
        deal = self.get_object()
        deal.payment_schedules.update(status="OVERDUE")
        return Response({"status": "ok", "deal_id": deal.id})

    @action(detail=True, methods=["post"], url_path="generate-kaspi-link")
    def generate_kaspi_link(self, request, pk=None):
        deal = self.get_object()
        return Response({"link": f"https://kaspi.kz/pay/{deal.id}"})

    @action(detail=False, methods=["post"], url_path="release-quota-slot")
    def release_quota_slot(self, request):
        deal_id = request.data.get("deal_id")
        base_qs = self.get_queryset()
        deal = base_qs.filter(pk=deal_id).first() if deal_id else base_qs.filter(status=Deal.STATUS_WAITLIST).order_by("created_at").first()
        if deal is None:
            return Response({"status": "ok"})
        deal.release_quota_slot()
        return Response({"status": "ok", "deal_id": deal.id})

    @action(detail=True, methods=["post"], url_path="select-tariff")
    def select_tariff(self, request, pk=None):
        """Выбор тарифа и авто-генерация графика платежей (раздел 6, п.3).

        POST /api/deals/{id}/select-tariff/
        Body: { tariff, has_food, has_transport, transport_zone, is_second_child }
        """
        deal = self.get_object()
        tariff_name = request.data.get("tariff") or (deal.tariff.name if deal.tariff else None)
        if not tariff_name:
            return Response({"error": "Параметр tariff обязателен."}, status=status.HTTP_400_BAD_REQUEST)

        has_food = bool(request.data.get("has_food", deal.has_food))
        has_transport = bool(request.data.get("has_transport", deal.has_transport))
        transport_zone = request.data.get("transport_zone", deal.transport_zone or "CITY")
        is_second_child = bool(request.data.get("is_second_child", deal.child.is_second_child if deal.child else False))
        has_subsidy = deal.parent.has_subsidy if deal.parent else False

        # Авто-проверка скидки 10% на 2-го ребёнка для ALDI BI (раздел 6, п.5)
        if deal.branch and deal.branch.code.startswith("ALDI_BI") and deal.parent:
            auto_second_child = check_second_child_discount(deal.parent)
            if auto_second_child:
                is_second_child = True

        # Сохраняем тариф в Deal (находим/создаём)
        grade_band = deal.child.grade_band if deal.child else "PRIMARY_SECONDARY"
        tariff = self._ensure_tariff(deal.branch, tariff_name, grade_band)
        deal.tariff = tariff
        deal.has_food = has_food
        deal.has_transport = has_transport
        deal.transport_zone = transport_zone
        if deal.child:
            deal.child.is_second_child = is_second_child
            deal.child.save(update_fields=["is_second_child"])
        deal.save(update_fields=["tariff", "has_food", "has_transport", "transport_zone"])

        # Авто-генерация PaymentSchedule (удаляет старые + создаёт новые)
        generate_payment_schedule(
            deal,
            tariff_name=tariff_name,
            has_food=has_food,
            has_transport=has_transport,
            transport_zone=transport_zone,
            is_second_child=is_second_child,
            has_subsidy=has_subsidy,
        )

        return Response(DealSerializer(deal).data)

    @action(detail=True, methods=["patch"], url_path="move-stage")
    def move_stage(self, request, pk=None):
        deal = self.get_object()
        stage_name = request.data.get("stage")
        if stage_name:
            stage = Stage.objects.filter(funnel=deal.funnel, name=stage_name).first()
            if stage is None:
                stage = Stage.objects.create(funnel=deal.funnel, name=stage_name, order=999)
            deal.stage = stage
            deal.clean()
            deal.save(update_fields=["stage"])
            if stage_name in {"ENTRANCE_FEE_PAID", "ENTRANCE_FEE"}:
                Task.objects.get_or_create(deal=deal, defaults={"title": "Collect entrance fee", "due_date": date.today() + timedelta(days=3)})
        return Response(DealSerializer(deal).data)

    @action(detail=False, methods=["post"], url_path="webhook/leads")
    def webhook_leads(self, request):
        payload = request.data or {}
        branch_code = self._resolve_branch_code(payload.get("branch_code"))
        branch = self._ensure_branch(branch_code)
        funnel, stage = self._ensure_funnel_stage("b2c_schools")
        parent = Contact.objects.create(full_name=payload.get("full_name", "Web lead"), phone=payload.get("phone", f"+7701{random.randint(1000000, 9999999)}"), email=payload.get("email", ""), contact_type=Contact.CONTACT_TYPE_PARENT)
        child = Child.objects.create(parent=parent, full_name=payload.get("child_name", "New child"), grade_or_group=payload.get("grade_or_group", "1 класс"), grade_band=payload.get("grade_band", "PRIMARY_SECONDARY"))
        deal = Deal.objects.create(funnel=funnel, stage=stage, branch=branch, parent=parent, child=child, total_amount=Decimal("0"))
        return Response(DealSerializer(deal).data, status=status.HTTP_201_CREATED)


class MeView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=["patch"])
    def update(self, request):
        user = request.user
        payload = {k: v for k, v in request.data.items() if k in ("email", "first_name", "last_name", "role", "branch")}
        serializer = UserSerializer(user, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data)


class ObtainAuthTokenWithRole(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = AuthTokenSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})