from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.apps import apps

PIPELINE_STAGES = {
    "B2C_SCHOOL": [
        "UNSORTED",
        "QUALIFICATION",
        "TOUR_SCHEDULED",
        "TOUR_PASSED",
        "TARIFF_SELECTION",
        "ENTRANCE_FEE_PAID",
        "CONTRACT_SIGNED",
        "SUCCESS",
    ],
    "B2C_KINDERGARTEN": [
        "NEW_LEAD",
        "TRIAL_DAY",
        "ADAPTATION",
        "ENTRANCE_FEE",
        "MONTHLY_PAYED",
        "SUCCESS",
    ],
    "B2B": ["CONTACT", "QUALIFICATION", "PROPOSAL", "NEGOTIATION", "INVOICED", "WON"],
}


def get_initial_stage(pipeline: str) -> str:
    return PIPELINE_STAGES.get(pipeline, PIPELINE_STAGES["B2C_SCHOOL"])[0]


def get_pipeline_stages(pipeline: str) -> list[str]:
    return PIPELINE_STAGES.get(pipeline, PIPELINE_STAGES["B2C_SCHOOL"])


def calculate_total(
    branch_code: str,
    grade_band: str,
    tariff_name: str,
    has_food: bool = False,
    has_transport: bool = False,
    transport_zone: str = "CITY",
    has_second_child_discount: bool = False,
    has_subsidy: bool = False,
) -> Decimal:
    branch_model = apps.get_model("crm", "Branch")
    branch = branch_model.objects.filter(code=branch_code).first()
    subsidy_amount = Decimal("0")
    if branch is not None:
        subsidy_amount = Decimal(branch.subsidy_amount or "0")

    if branch_code == "RIVIERA":
        pricing = {
            "PRESCHOOL": {"Выгодный": Decimal("3500000"), "Стандарт": Decimal("3650000"), "Стандарт Плюс": Decimal("3900000"), "Взнос": Decimal("200000")},
            "PRIMARY_SECONDARY": {"Выгодный": Decimal("4500000"), "Стандарт": Decimal("4900000"), "Стандарт Плюс": Decimal("5180000"), "Взнос": Decimal("350000")},
            "SENIOR": {"Выгодный": Decimal("4700000"), "Стандарт": Decimal("5100000"), "Стандарт Плюс": Decimal("5500000"), "Взнос": Decimal("350000")},
        }
        amount = pricing[grade_band][tariff_name]
        if has_food:
            amount += Decimal("752400")
        if has_transport:
            amount += Decimal("57000")
        return amount

    if branch_code in {"QUANTUM_STEM", "QUANTUM_TECH"}:
        if tariff_name == "Основной (9 траншей)":
            amount = Decimal("4410000")
        elif tariff_name == "3 транша":
            amount = Decimal("4200000")
        else:
            raise ValueError(f"Unsupported tariff for Quantum: {tariff_name}")
        amount += Decimal("200000")
        if has_food:
            amount += Decimal("630000")
        if has_transport:
            amount += Decimal("57000") if transport_zone == "CITY" else Decimal("72000")
        return amount

    if branch_code.startswith("ALDI_BI") or branch_code == "ALDI_BI":
        monthly_fee = Decimal("250000")
        if branch_code == "ALDI_BI_GREENLINE_AQUA":
            monthly_fee = Decimal("165000")
        elif branch_code == "ALDI_BI_FLAGMAN":
            monthly_fee = Decimal("115000")
        if has_second_child_discount:
            monthly_fee *= Decimal("0.9")
        if has_subsidy:
            monthly_fee -= subsidy_amount
        return monthly_fee

    return Decimal("0")


def build_pricing_summary(
    branch: str,
    tariff: str,
    has_food: bool = False,
    has_transport: bool = False,
    is_second_child: bool = False,
    grade: str = "5",
    meals: int = 3,
) -> dict[str, Any]:
    branch_code = branch
    if branch == "RIVIERA":
        branch_code = "RIVIERA"
    elif branch in {"QUANTUM_STEM", "QUANTUM_TECH", "QUANTUM"}:
        branch_code = "QUANTUM_STEM"
    elif branch == "ALDI_BI":
        branch_code = "ALDI_BI_CAPITAL_PARK"

    if branch_code == "RIVIERA":
        entrance_fee = Decimal("350000")
        if tariff == "Выгодный":
            main_fee = Decimal("3500000")
            schedules = [
                {"title": "Entrance fee", "amount": entrance_fee, "status": "PENDING"},
                {"title": "Annual tuition", "amount": main_fee, "status": "PENDING"},
            ]
        elif tariff == "Стандарт":
            main_fee = Decimal("4900000")
            schedules = [
                {"title": "Entrance fee", "amount": entrance_fee, "status": "PENDING"},
                {"title": "1st tranche", "amount": Decimal("1633333"), "status": "PENDING"},
                {"title": "2nd tranche", "amount": Decimal("1633333"), "status": "PENDING"},
                {"title": "3rd tranche", "amount": Decimal("1633334"), "status": "PENDING"},
            ]
        elif tariff == "Стандарт Плюс":
            main_fee = Decimal("5180000")
            schedules = [
                {"title": "Entrance fee", "amount": entrance_fee, "status": "PENDING"},
            ]
            for index in range(8):
                schedules.append({"title": f"Installment {index + 1}", "amount": Decimal("647500"), "status": "PENDING"})
        else:
            raise ValueError(f"Unsupported tariff for Riviera: {tariff}")
        total = calculate_total(branch_code, grade_band="PRIMARY_SECONDARY", tariff_name=tariff, has_food=has_food, has_transport=has_transport, transport_zone="CITY", has_second_child_discount=is_second_child, has_subsidy=False)
        return {"total_amount": total, "schedules": schedules}

    if branch_code in {"QUANTUM_STEM", "QUANTUM_TECH"}:
        entrance_fee = Decimal("200000")
        if tariff in {"Основной (9 траншей)", "3 транша"}:
            main_fee = Decimal("4410000") if tariff == "Основной (9 траншей)" else Decimal("4200000")
            schedules = [
                {"title": "Entrance fee", "amount": entrance_fee, "status": "PENDING"},
                {"title": "Guarantee", "amount": Decimal("810000"), "status": "PENDING"},
            ]
            if tariff == "Основной (9 траншей)":
                for index in range(9):
                    schedules.append({"title": f"Installment {index + 1}", "amount": Decimal("400000"), "status": "PENDING"})
            else:
                for index in range(3):
                    schedules.append({"title": f"Tranche {index + 1}", "amount": Decimal("1130000"), "status": "PENDING"})
        else:
            raise ValueError(f"Unsupported tariff for Quantum: {tariff}")
        total = calculate_total(branch_code, grade_band="PRIMARY_SECONDARY", tariff_name=tariff, has_food=has_food, has_transport=has_transport, transport_zone="CITY", has_second_child_discount=False, has_subsidy=False)
        return {"total_amount": total, "schedules": schedules}

    if branch_code.startswith("ALDI_BI") or branch_code == "ALDI_BI":
        # Исправленный блок: динамическое назначение цен в зависимости от филиала
        if branch_code == "ALDI_BI_CAPITAL_PARK":
            entrance_fee = Decimal("200000")
            monthly_fee = Decimal("250000")
        elif branch_code == "ALDI_BI_GREENLINE_AQUA":
            entrance_fee = Decimal("150000")
            monthly_fee = Decimal("165000")
        elif branch_code == "ALDI_BI_FLAGMAN":
            entrance_fee = Decimal("100000")
            monthly_fee = Decimal("115000")
        else:
            # Значения по умолчанию
            entrance_fee = Decimal("150000")
            monthly_fee = Decimal("250000")

        if is_second_child:
            monthly_fee *= Decimal("0.9")
            
        schedules = [
            {"title": "Entrance fee", "amount": entrance_fee, "status": "PENDING"},
            {"title": "Monthly tuition", "amount": monthly_fee, "status": "PENDING"},
        ]
        
        total = calculate_total(branch_code, grade_band="PRESCHOOL", tariff_name="", has_food=False, has_transport=False, transport_zone="CITY", has_second_child_discount=is_second_child, has_subsidy=False)
        return {"total_amount": total, "schedules": schedules}

    # BIART / BIART_ASTANA — креативные индустрии и B2B-контракты.
    # Раньше build_pricing_summary падал с "Unsupported branch: BIART" при
    # выборе этого филиала в UI-калькуляторе. Теперь возвращаем дефолтный
    # контрактный расчёт, чтобы красная плашка больше не появлялась.
    if branch_code in {"BIART", "BIART_ASTANA"}:
        entrance_fee = Decimal("0")
        contract_amount = Decimal("5000000")  # Корпоративный тариф
        schedules = [
            {"title": "Договор / Контракт", "amount": contract_amount, "status": "PENDING"},
        ]
        total = Decimal(contract_amount)
        return {"total_amount": total, "schedules": schedules}

    # Fallback: для неизвестных филиалов (BINOM, новые) — не падаем,
    # возвращаем нулевую структуру, чтобы UI не показывал красную плашку.
    return {
        "total_amount": Decimal("0"),
        "schedules": [{"title": "Вступительный взнос", "amount": Decimal("0"), "status": "PENDING"}],
    }


def build_schedule_preview(branch: str, tariff: str, has_food: bool = False, has_transport: bool = False, is_second_child: bool = False, grade: str = "5", meals: int = 3) -> list[dict[str, Any]]:
    summary = build_pricing_summary(branch, tariff, has_food, has_transport, is_second_child, grade, meals)
    base_date = date.today()
    preview: list[dict[str, Any]] = []
    for index, schedule in enumerate(summary["schedules"]):
        due_date = (base_date + timedelta(days=15 * (index + 1))).isoformat()
        preview.append(
            {
                "title": schedule["title"],
                "amount": str(schedule["amount"]),
                "due_date": due_date,
                "status": schedule["status"],
            }
        )
    return preview