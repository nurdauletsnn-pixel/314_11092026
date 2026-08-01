"""Сервис автоматизации (раздел 6 п.4 + раздел 7 Риск 2).

- Waitlist: авто-продвижение первой сделки из листа ожидания при освобождении места.
- Триггеры платежей: D-3 напоминание, D+2 просрочка (OVERDUE) + срочная задача + уведомление директора.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.apps import apps
from django.db import transaction


# ──────────────────────────────────────────────────────────────────────────────
# 1. WAITLIST / ЛИСТ ОЖИДАНИЯ (раздел 7, Риск 2)
# ──────────────────────────────────────────────────────────────────────────────

@transaction.atomic
def notify_waitlist_next(branch, grade_or_group: str) -> dict:
    """При освобождении места продвигает первую сделку из WAITLIST.

    Находит первую WAITLIST-сделку по филиалу и классу/группе (по created_at),
    переводит в ACTIVE, ставит стадию QUALIFICATION, создаёт ActivityLog
    и задачу менеджеру с приоритетом HIGH.

    Возвращает: { promoted: Deal | None, task: Task | None }
    """
    Deal = apps.get_model("crm", "Deal")
    ActivityLog = apps.get_model("crm", "ActivityLog")
    Task = apps.get_model("crm", "Task")
    Stage = apps.get_model("crm", "Stage")
    Funnel = apps.get_model("crm", "Funnel")

    waitlist = (
        Deal.objects.filter(branch=branch, status=Deal.STATUS_WAITLIST, child__isnull=False)
        .order_by("created_at")
    )
    if grade_or_group:
        waitlist = waitlist.filter(child__grade_or_group=grade_or_group)

    deal = waitlist.first()
    if deal is None:
        return {"promoted": None, "task": None}

    # Переводим в ACTIVE и ставим стадию QUALIFICATION
    deal.status = Deal.STATUS_ACTIVE
    funnel_slug = deal.funnel.slug if deal.funnel else "b2c_schools"
    funnel, _ = Funnel.objects.get_or_create(slug=funnel_slug, defaults={"name": funnel_slug.replace("-", " ").title()})
    stage, _ = Stage.objects.get_or_create(funnel=funnel, name="QUALIFICATION", defaults={"order": 2})
    deal.stage = stage
    deal.save(update_fields=["status", "stage"])

    # ActivityLog
    ActivityLog.objects.create(
        deal=deal,
        type=ActivityLog.TYPE_SYSTEM,
        actor=ActivityLog.ACTOR_SYSTEM,
        content="Место в квоте освободилось — сделка продвинута из листа ожидания.",
    )

    # Задача менеджеру (HIGH)
    task = Task.objects.create(
        deal=deal,
        title="Связаться с клиентом: место освободилось, сделка продвинута из листа ожидания",
        due_date=date.today(),
        auto_generated=True,
        assigned_to=deal.assigned_to,
        priority=Task.PRIORITY_HIGH,
    )

    return {"promoted": deal, "task": task}


# ──────────────────────────────────────────────────────────────────────────────
# 2. ТРИГГЕРЫ ДЕДЛАЙНОВ ПЛАТЕЖЕЙ (раздел 6, п.4)
# ──────────────────────────────────────────────────────────────────────────────

def check_payment_deadlines() -> dict:
    """Проверяет все PENDING-платежи и применяет триггеры D-3 / D+2.

    D-3  (due_date = today + 3): создаёт задачу «Отправить напоминание об оплате»
          (без дублирования, если такая задача уже есть).
    D+2  (due_date < today - 1): статус транша → OVERDUE, срочная задача (HIGH)
          менеджеру + ActivityLog + уведомление BRANCH_DIRECTOR филиала.

    Возвращает статистику: { reminders_created, overdue_promoted, tasks_created }
    """
    PaymentSchedule = apps.get_model("crm", "PaymentSchedule")
    Task = apps.get_model("crm", "Task")
    ActivityLog = apps.get_model("crm", "ActivityLog")
    User = apps.get_model("crm", "User")

    today = date.today()
    d_minus_3 = today + timedelta(days=3)
    d_plus_2_threshold = today - timedelta(days=1)  # due_date < today-1 => просрочка на 2+ дня

    stats = {"reminders_created": 0, "overdue_promoted": 0, "tasks_created": 0}

    # --- D-3: напоминание об оплате ---
    reminders_targets = PaymentSchedule.objects.filter(
        status=PaymentSchedule.STATUS_PENDING,
        due_date=d_minus_3,
    ).select_related("deal", "deal__assigned_to")
    for schedule in reminders_targets:
        already_exists = Task.objects.filter(
            deal=schedule.deal,
            title="Отправить напоминание об оплате",
            is_done=False,
        ).exists()
        if already_exists:
            continue
        Task.objects.create(
            deal=schedule.deal,
            title="Отправить напоминание об оплате",
            due_date=schedule.due_date,
            auto_generated=True,
            assigned_to=schedule.deal.assigned_to,
            priority=Task.PRIORITY_MEDIUM,
        )
        stats["reminders_created"] += 1

    # --- D+2: просрочка ---
    overdue_targets = PaymentSchedule.objects.filter(
        status=PaymentSchedule.STATUS_PENDING,
        due_date__lt=d_plus_2_threshold,
    ).select_related("deal", "deal__branch", "deal__assigned_to")
    for schedule in overdue_targets:
        schedule.status = PaymentSchedule.STATUS_OVERDUE
        schedule.save(update_fields=["status"])
        stats["overdue_promoted"] += 1

        # Срочная задача менеджеру
        Task.objects.create(
            deal=schedule.deal,
            title=f"Просрочен платёж: {schedule.title} ({schedule.amount})",
            due_date=today,
            auto_generated=True,
            assigned_to=schedule.deal.assigned_to,
            priority=Task.PRIORITY_HIGH,
        )
        stats["tasks_created"] += 1

        # ActivityLog
        ActivityLog.objects.create(
            deal=schedule.deal,
            type=ActivityLog.TYPE_SYSTEM,
            actor=ActivityLog.ACTOR_SYSTEM,
            content=f"Платёж {schedule.title} просрочен на 2+ дня, переведён в OVERDUE.",
        )

        # Уведомление BRANCH_DIRECTOR филиала
        if schedule.deal.branch is not None:
            directors = User.objects.filter(
                role=User.Role.BRANCH_DIRECTOR,
                branch=schedule.deal.branch,
            )
            for director in directors:
                Task.objects.create(
                    deal=schedule.deal,
                    title=f"[Директор] Просрочен платёж в филиале: {schedule.title}",
                    due_date=today,
                    auto_generated=True,
                    assigned_to=director,
                    priority=Task.PRIORITY_HIGH,
                )
                stats["tasks_created"] += 1

    return stats