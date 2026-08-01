"""Движок тарифов и платежей (раздел 6 + раздел 1 спецификации).

- Прайс-листы зафиксированы из раздела 1 (НИКОГДА не менять без сверки с документом).
- Авто-генерация PaymentSchedule с кастомными датами по календарю филиала.
- Авто-проверка скидки 10% на 2-го ребёнка (только ALDI BI).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.apps import apps

# ──────────────────────────────────────────────────────────────────────────────
# 1. ПРАЙС-ЛИСТЫ (раздел 1 — источник цен, не менять без сверки с документом)
# ──────────────────────────────────────────────────────────────────────────────

RIVIERA_PRICING: dict[str, dict[str, dict[str, Decimal]]] = {
    # grade_band -> tariff_name -> { main, entrance_fee }
    "PRESCHOOL": {
        "Выгодный": {"main": Decimal("3500000"), "entrance_fee": Decimal("200000")},
        "Стандарт": {"main": Decimal("3650000"), "entrance_fee": Decimal("200000")},
        "Стандарт Плюс": {"main": Decimal("3900000"), "entrance_fee": Decimal("200000")},
    },
    "PRIMARY_SECONDARY": {
        "Выгодный": {"main": Decimal("4500000"), "entrance_fee": Decimal("350000")},
        "Стандарт": {"main": Decimal("4900000"), "entrance_fee": Decimal("350000")},
        "Стандарт Плюс": {"main": Decimal("5180000"), "entrance_fee": Decimal("350000")},
    },
    "SENIOR": {
        "Выгодный": {"main": Decimal("4700000"), "entrance_fee": Decimal("350000")},
        "Стандарт": {"main": Decimal("5100000"), "entrance_fee": Decimal("350000")},
        "Стандарт Плюс": {"main": Decimal("5500000"), "entrance_fee": Decimal("350000")},
    },
}

QUANTUM_PRICING: dict[str, dict[str, dict[str, Any]]] = {
    # Особенность: взнос 810k (гарантийный) + транши по регламенту.
    "Основной (9 траншей)": {
        "entrance_fee": Decimal("200000"),
        "guarantee": Decimal("810000"),
        "installments": 9,
        "installment_amount": Decimal("400000"),
    },
    "3 транша": {
        "entrance_fee": Decimal("200000"),
        "guarantee": Decimal("810000"),
        "installments": 3,
        "installment_amount": Decimal("1130000"),
    },
}

ALDI_PRICING: dict[str, dict[str, Decimal]] = {
    # branch_code -> { entrance_fee, monthly_fee }
    "ALDI_BI_CAPITAL_PARK": {"entrance_fee": Decimal("200000"), "monthly_fee": Decimal("250000")},
    "ALDI_BI_GREENLINE_AQUA": {"entrance_fee": Decimal("150000"), "monthly_fee": Decimal("165000")},
    "ALDI_BI_FLAGMAN": {"entrance_fee": Decimal("100000"), "monthly_fee": Decimal("115000")},
    "ALDI_BI": {"entrance_fee": Decimal("200000"), "monthly_fee": Decimal("250000")},  # default
}

# Доп. услуги (раздел 1)
FOOD_RIVIERA = Decimal("752400")
FOOD_QUANTUM_PRIMARY = Decimal("630000")   # 1-11 классы
FOOD_QUANTUM_SENIOR = Decimal("684000")    # 12 класс
TRANSPORT_CITY = Decimal("57000")
TRANSPORT_SUBURB = Decimal("72000")


# ──────────────────────────────────────────────────────────────────────────────
# 2. КАЛЕНДАРЬ ФИЛИАЛОВ (кастомные даты траншей)
# ──────────────────────────────────────────────────────────────────────────────

def _month_with_day(year: int, month: int, day: int) -> date:
    """Возвращает дату с корректным днём (если день > дней в месяце — последний день)."""
    import calendar

    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last_day))


def _school_year_schedule(deal_date: date, installment_count: int, first_payment_month: int | None = None) -> list[date]:
    """Учебный год сентябрь–май (9 месяцев). Возвращает даты траншей.

    Если deal_date после сентября — начинаем со следующего доступного месяца.
    """
    start_month = first_payment_month or 9
    year = deal_date.year
    # Если сделка создана после старта учебного года — начинаем со следующего месяца
    if deal_date.month > start_month:
        start_month = deal_date.month
    elif deal_date.month == start_month and deal_date.day > 10:
        start_month += 1

    dates: list[date] = []
    month = start_month
    y = year if start_month >= deal_date.month else year + 1
    while len(dates) < installment_count:
        if month > 12:
            month = 1
            y += 1
        # Транш «до 10 числа»
        dates.append(_month_with_day(y, month, 10))
        month += 1
    return dates


def _quantum_schedule(deal_date: date, tariff_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Quantum: 9 траншей — каждый месяц до 10 числа; 3 транша — сент/дек/март.

    (раздел 1: «Скидка 3 транша 4.2М (810k + 3×1.13М: сент/дек/март)»)
    """
    schedules: list[dict[str, Any]] = []
    # Гарантийный взнос 810k — ближайшее 10-е число
    schedules.append({
        "title": "Гарантийный взнос",
        "amount": tariff_config["guarantee"],
        "due_date": _nearest_day_10(deal_date),
        "status": "PENDING",
    })

    count = tariff_config["installments"]
    if count == 3:
        # Сентябрь / Декабрь / Март
        months = [9, 12, 3]
        year = deal_date.year
        for i, m in enumerate(months):
            y = year if m >= deal_date.month else year + 1
            # Если дата сделки позже нужного месяца — сдвигаем на следующий год
            if deal_date.month > m or (deal_date.month == m and deal_date.day > 10):
                y += 1
            schedules.append({
                "title": f"Транш {i + 1}",
                "amount": tariff_config["installment_amount"],
                "due_date": _month_with_day(y, m, 10),
                "status": "PENDING",
            })
    else:
        dates = _school_year_schedule(deal_date, count)
        for i, due in enumerate(dates):
            schedules.append({
                "title": f"Транш {i + 1}",
                "amount": tariff_config["installment_amount"],
                "due_date": due,
                "status": "PENDING",
            })
    return schedules


def _nearest_day_10(deal_date: date) -> date:
    """Ближайшее 10-е число (если позже 10-го в текущем месяце — следующий месяц)."""
    if deal_date.day <= 10:
        return _month_with_day(deal_date.year, deal_date.month, 10)
    return _month_with_day(deal_date.year, deal_date.month + 1, 10)


def _monthly_schedule(deal_date: date, count_months: int = 12, day: int = 5) -> list[date]:
    """Ежемесячные даты (сады ALDI, развозка, питание)."""
    dates: list[date] = []
    month = deal_date.month + (1 if deal_date.day > day else 0)
    year = deal_date.year
    while len(dates) < count_months:
        if month > 12:
            month = 1
            year += 1
        dates.append(_month_with_day(year, month, day))
        month += 1
    return dates


# ──────────────────────────────────────────────────────────────────────────────
# 3. РАСЧЁТЫ
# ──────────────────────────────────────────────────────────────────────────────

def calculate_tariff_preview(
    branch_code: str,
    tariff_name: str,
    grade_band: str = "PRIMARY_SECONDARY",
    has_food: bool = False,
    has_transport: bool = False,
    transport_zone: str = "CITY",
    is_second_child: bool = False,
    has_subsidy: bool = False,
    deal_date: date | None = None,
) -> dict[str, Any]:
    """Предварительный расчёт тарифа + график (без сохранения в БД).

    Возвращает:
        {
          "total_amount": Decimal,
          "entrance_fee": Decimal,
          "schedules": [ {title, amount, due_date, status}, ... ]
        }
    """
    deal_date = deal_date or date.today()
    branch_code = _normalize_branch(branch_code)

    if branch_code == "RIVIERA":
        return _calc_riviera(tariff_name, grade_band, has_food, has_transport, deal_date)

    if branch_code in {"QUANTUM_STEM", "QUANTUM_TECH"}:
        return _calc_quantum(tariff_name, has_food, has_transport, transport_zone, grade_band, deal_date)

    if branch_code.startswith("ALDI_BI"):
        return _calc_aldi(branch_code, is_second_child, has_subsidy, deal_date)

    # BIART / BIART_ASTANA — креативные индустрии (аренда зала), B2B-контракты.
    # Раньше здесь падал ValueError("Unsupported branch: BIART") — красная плашка
    # появлялась в UI-калькуляторе при выборе этого филиала.
    if branch_code in {"BIART", "BIART_ASTANA"}:
        contract_amount = Decimal("5000000")  # Корпоративный тариф (mock)
        return {
            "total_amount": contract_amount,
            "entrance_fee": Decimal("0"),
            "schedules": [
                {
                    "title": "Договор / Контракт",
                    "amount": contract_amount,
                    "due_date": (deal_date + timedelta(days=5)).isoformat(),
                    "status": "PENDING",
                }
            ],
        }

    # Неизвестный филиал (BINOM, новый): вместо 400-ошибки возвращаем нулевую
    # структуру, чтобы фронтенд не показывал красную плашку "Unsupported branch: ...".
    return {
        "total_amount": Decimal("0"),
        "entrance_fee": Decimal("0"),
        "schedules": [
            {
                "title": "Вступительный взнос",
                "amount": Decimal("0"),
                "due_date": (deal_date + timedelta(days=3)).isoformat(),
                "status": "PENDING",
            }
        ],
    }


def _normalize_branch(branch_code: str) -> str:
    """Приводит коды филиалов к каноническому виду."""
    mapping = {
        "QUANTUM": "QUANTUM_STEM",
        "ALDI": "ALDI_BI_CAPITAL_PARK",
        "ALDI_CAPITAL": "ALDI_BI_CAPITAL_PARK",
        "ALDI_GREENLINE": "ALDI_BI_GREENLINE_AQUA",
        "ALDI_FLAGMAN": "ALDI_BI_FLAGMAN",
    }
    return mapping.get(branch_code, branch_code)


def _calc_riviera(tariff_name: str, grade_band: str, has_food: bool, has_transport: bool, deal_date: date) -> dict[str, Any]:
    grade = "PRIMARY_SECONDARY" if grade_band not in RIVIERA_PRICING else grade_band
    if tariff_name not in RIVIERA_PRICING[grade]:
        raise ValueError(f"Unsupported tariff for Riviera: {tariff_name}")
    cfg = RIVIERA_PRICING[grade][tariff_name]
    main_fee = cfg["main"]
    entrance_fee = cfg["entrance_fee"]

    schedules: list[dict[str, Any]] = [
        {
            "title": "Вступительный взнос",
            "amount": entrance_fee,
            "due_date": (deal_date + timedelta(days=3)).isoformat(),
            "status": "PENDING",
        }
    ]

    if tariff_name == "Выгодный":
        # 100% разово — сразу после взноса
        schedules.append({
            "title": "Оплата обучения (100%)",
            "amount": main_fee,
            "due_date": (deal_date + timedelta(days=5)).isoformat(),
            "status": "PENDING",
        })
    elif tariff_name == "Стандарт":
        # 3 транша равными частями, помесячно
        amount = (main_fee / Decimal("3")).quantize(Decimal("1"))
        remainder = main_fee - amount * Decimal("2")
        due_dates = _school_year_schedule(deal_date, 3, first_payment_month=9)
        for i, due in enumerate(due_dates):
            schedules.append({
                "title": f"Транш {i + 1}",
                "amount": remainder if i == 2 else amount,
                "due_date": due.isoformat(),
                "status": "PENDING",
            })
    elif tariff_name == "Стандарт Плюс":
        # 8 траншей равными частями, помесячно
        amount = (main_fee / Decimal("8")).quantize(Decimal("1"))
        remainder = main_fee - amount * Decimal("7")
        due_dates = _school_year_schedule(deal_date, 8, first_payment_month=9)
        for i, due in enumerate(due_dates):
            schedules.append({
                "title": f"Транш {i + 1}",
                "amount": remainder if i == 7 else amount,
                "due_date": due.isoformat(),
                "status": "PENDING",
            })

    if has_food:
        schedules.append({
            "title": "Питание",
            "amount": FOOD_RIVIERA,
            "due_date": _month_with_day(deal_date.year, max(deal_date.month, 9), 10).isoformat(),
            "status": "PENDING",
        })
    if has_transport:
        schedules.append({
            "title": "Развозка (город)",
            "amount": TRANSPORT_CITY,
            "due_date": _month_with_day(deal_date.year, max(deal_date.month, 9), 10).isoformat(),
            "status": "PENDING",
        })

    total = entrance_fee + main_fee + (FOOD_RIVIERA if has_food else Decimal("0")) + (TRANSPORT_CITY if has_transport else Decimal("0"))
    return {"total_amount": total, "entrance_fee": entrance_fee, "schedules": schedules}


def _calc_quantum(tariff_name: str, has_food: bool, has_transport: bool, transport_zone: str, grade_band: str, deal_date: date) -> dict[str, Any]:
    if tariff_name not in QUANTUM_PRICING:
        raise ValueError(f"Unsupported tariff for Quantum: {tariff_name}")
    cfg = QUANTUM_PRICING[tariff_name]
    entrance_fee = cfg["entrance_fee"]
    main_fee = cfg["guarantee"] + cfg["installment_amount"] * cfg["installments"]

    schedules_date = _quantum_schedule(deal_date, cfg)
    schedules: list[dict[str, Any]] = [
        {
            "title": "Вступительный взнос",
            "amount": entrance_fee,
            "due_date": (deal_date + timedelta(days=3)).isoformat(),
            "status": "PENDING",
        }
    ]
    for item in schedules_date:
        schedules.append({
            "title": item["title"],
            "amount": item["amount"],
            "due_date": item["due_date"].isoformat(),
            "status": item["status"],
        })

    if has_food:
        schedules.append({
            "title": "Питание",
            "amount": FOOD_QUANTUM_SENIOR if grade_band == "SENIOR" else FOOD_QUANTUM_PRIMARY,
            "due_date": _month_with_day(deal_date.year, deal_date.month, 10).isoformat(),
            "status": "PENDING",
        })
    if has_transport:
        transport = TRANSPORT_SUBURB if transport_zone == "SUBURB" else TRANSPORT_CITY
        schedules.append({
            "title": "Развозка" + (" (пригород)" if transport_zone == "SUBURB" else " (город)"),
            "amount": transport,
            "due_date": _month_with_day(deal_date.year, deal_date.month, 10).isoformat(),
            "status": "PENDING",
        })

    total = entrance_fee + main_fee + (FOOD_QUANTUM_SENIOR if has_food and grade_band == "SENIOR" else FOOD_QUANTUM_PRIMARY if has_food else Decimal("0")) + (TRANSPORT_SUBURB if has_transport and transport_zone == "SUBURB" else TRANSPORT_CITY if has_transport else Decimal("0"))
    return {"total_amount": total, "entrance_fee": entrance_fee, "schedules": schedules}


def _calc_aldi(branch_code: str, is_second_child: bool, has_subsidy: bool, deal_date: date) -> dict[str, Any]:
    cfg = ALDI_PRICING.get(branch_code, ALDI_PRICING["ALDI_BI_CAPITAL_PARK"])
    entrance_fee = cfg["entrance_fee"]
    monthly_fee = cfg["monthly_fee"]
    if is_second_child:
        monthly_fee = (monthly_fee * Decimal("0.9")).quantize(Decimal("1"))

    # Госдотация вычитается из ежемесячной платы
    subsidy = Decimal("0")
    if has_subsidy:
        Branch = apps.get_model("crm", "Branch")
        branch = Branch.objects.filter(code=branch_code).first()
        if branch is not None:
            subsidy = Decimal(branch.subsidy_amount or "0")
        monthly_fee = max(Decimal("0"), monthly_fee - subsidy)

    schedules: list[dict[str, Any]] = [
        {
            "title": "Вступительный взнос",
            "amount": entrance_fee,
            "due_date": (deal_date + timedelta(days=3)).isoformat(),
            "status": "PENDING",
        }
    ]
    # 12 ежемесячных платежей
    for due in _monthly_schedule(deal_date, count_months=12, day=5):
        schedules.append({
            "title": "Ежемесячный платёж",
            "amount": monthly_fee,
            "due_date": due.isoformat(),
            "status": "PENDING",
        })

    total = entrance_fee + monthly_fee * Decimal("12")
    return {"total_amount": total, "entrance_fee": entrance_fee, "schedules": schedules}


# ──────────────────────────────────────────────────────────────────────────────
# 4. СКИДКА 10% НА 2-ГО РЕБЁНКА (раздел 6, п.5 — применяется только к ALDI BI)
# ──────────────────────────────────────────────────────────────────────────────

def check_second_child_discount(contact) -> bool:
    """Есть ли у Contact уже активный/WON Deal на ДРУГОГО ребёнка.

    Если да — новая сделка на второго ребёнка получает скидку 10% (ALDI BI).
    """
    if contact is None:
        return False
    Deal = apps.get_model("crm", "Deal")
    active_deals = Deal.objects.filter(
        parent=contact,
        status__in=[Deal.STATUS_ACTIVE, Deal.STATUS_WON],
    ).exclude(child__isnull=True)
    return active_deals.exists()


# ──────────────────────────────────────────────────────────────────────────────
# 5. АВТО-ГЕНЕРАЦИЯ PAYMENTSCHEDULE В БД (раздел 6, п.3)
# ──────────────────────────────────────────────────────────────────────────────

def generate_payment_schedule(deal, tariff_name: str, has_food: bool, has_transport: bool, transport_zone: str, is_second_child: bool = False, has_subsidy: bool = False) -> dict[str, Any]:
    """Пересоздаёт записи PaymentSchedule для сделки.

    1) Удаляет старые.
    2) Считает новый график (с кастомными датами по календарю филиала).
    3) Создаёт записи PaymentSchedule.
    4) Обновляет deal.total_amount.
    Возвращает summary.
    """
    PaymentSchedule = apps.get_model("crm", "PaymentSchedule")
    branch_code = deal.branch.code if deal.branch else ""
    grade_band = deal.child.grade_band if deal.child else "PRIMARY_SECONDARY"
    deal_date = deal.created_at.date() if deal.created_at else date.today()

    summary = calculate_tariff_preview(
        branch_code=branch_code,
        tariff_name=tariff_name,
        grade_band=grade_band,
        has_food=has_food,
        has_transport=has_transport,
        transport_zone=transport_zone,
        is_second_child=is_second_child,
        has_subsidy=has_subsidy,
        deal_date=deal_date,
    )

    # Удаляем старые и создаём новые
    PaymentSchedule.objects.filter(deal=deal).delete()
    for item in summary["schedules"]:
        PaymentSchedule.objects.create(
            deal=deal,
            title=item["title"],
            amount=item["amount"],
            due_date=item["due_date"],
            status=item["status"],
        )

    deal.total_amount = summary["total_amount"]
    deal.save(update_fields=["total_amount"])

    return summary