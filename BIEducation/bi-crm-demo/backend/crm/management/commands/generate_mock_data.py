import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from crm.business_logic import calculate_total
from crm.models import ActivityLog, BotMessage, Branch, Child, ClassQuota, Contact, Deal, Funnel, Partner, PaymentSchedule, Stage, Tariff, Task


class Command(BaseCommand):
    help = "Populate the database with rich realistic CRM mock data (15-20 deals across all branches/funnels)"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Recreate mock data even if deals already exist")

    def handle(self, *args, **options):
        if Deal.objects.exists() and not options["force"]:
            self.stdout.write(self.style.WARNING("Mock data already exists. Use --force to recreate."))
            return

        # Удаляем ТОЛЬКО симулируемые данные, НО НЕ Branch — иначе сломается
        # привязка user.branch у пользователей из seed_users (диагностика бага видимости).
        ActivityLog.objects.all().delete()
        BotMessage.objects.all().delete()
        PaymentSchedule.objects.all().delete()
        Task.objects.all().delete()
        Deal.objects.all().delete()
        ClassQuota.objects.all().delete()
        Tariff.objects.all().delete()
        Child.objects.all().delete()
        Contact.objects.all().delete()
        Partner.objects.all().delete()
        Stage.objects.all().delete()
        Funnel.objects.all().delete()

        # Branch: get_or_create по code — сохраняем целостность с User.branch
        branch_defs = [
            {"name": "Riviera International School", "code": "RIVIERA", "city": "Астана", "segment": Branch.SEGMENT_SCHOOL},
            {"name": "Quantum STEM School", "code": "QUANTUM_STEM", "city": "Астана", "segment": Branch.SEGMENT_SCHOOL},
            {"name": "Quantum TECH School", "code": "QUANTUM_TECH", "city": "Астана", "segment": Branch.SEGMENT_SCHOOL},
            {"name": "ALDI BI Capital Park", "code": "ALDI_BI_CAPITAL_PARK", "city": "Астана", "segment": Branch.SEGMENT_KINDERGARTEN, "subsidy_amount": Decimal("50000")},
            {"name": "ALDI BI GreenLine.Aqua", "code": "ALDI_BI_GREENLINE_AQUA", "city": "Астана", "segment": Branch.SEGMENT_KINDERGARTEN},
            {"name": "ALDI BI Flagman", "code": "ALDI_BI_FLAGMAN", "city": "Астана", "segment": Branch.SEGMENT_KINDERGARTEN},
            {"name": "BINOM Astana 1", "code": "BINOM_ASTANA_1", "city": "Астана", "segment": Branch.SEGMENT_FREE_SCHOOL, "is_free": True},
            {"name": "BINOM Astana 2", "code": "BINOM_ASTANA_2", "city": "Астана", "segment": Branch.SEGMENT_FREE_SCHOOL, "is_free": True},
            {"name": "BINOM Atyrau 1", "code": "BINOM_ATYRAU_1", "city": "Атырау", "segment": Branch.SEGMENT_FREE_SCHOOL, "is_free": True},
            {"name": "BIART", "code": "BIART", "city": "Астана", "segment": Branch.SEGMENT_CREATIVE},
        ]
        branch_objs = []
        for payload in branch_defs:
            branch, _ = Branch.objects.get_or_create(code=payload["code"], defaults={k: v for k, v in payload.items() if k != "code"})
            branch_objs.append(branch)

        # Страховка: если seed_users запускался ДО создания филиалов, user.branch
        # у менеджеров/директоров остался None. Перепривязываем всех пользователей
        # к филиалам по коду, чтобы manager_riviera видел сделки своего филиала.
        User = get_user_model()
        for user in User.objects.filter(branch__isnull=True).exclude(role=User.Role.HQ_ADMIN):
            branch = Branch.objects.filter(code=user.username.split("_", 1)[-1].upper()).first()
            if branch is None:
                # Fallback: ищем по совпадению кода филиала в имени пользователя
                branch = next((b for b in branch_objs if b.code.lower() in user.username.lower()), None)
            if branch is not None:
                user.branch = branch
                user.save(update_fields=["branch"])
                self.stdout.write(f"  Rebound {user.username} -> {branch.code}")
        # Дополнительно: для пользователей, у которых branch НЕ None, но код не совпадает
        for user in User.objects.select_related("branch").exclude(role=User.Role.HQ_ADMIN).exclude(branch__isnull=True):
            branch = Branch.objects.filter(code=user.username.split("_", 1)[-1].upper()).first()
            if branch is not None and user.branch_id != branch.id:
                user.branch = branch
                user.save(update_fields=["branch"])
                self.stdout.write(f"  Rebound {user.username} -> {branch.code} (was {user.branch.code if user.branch else None})")

        for branch in branch_objs:
            if branch.segment in {Branch.SEGMENT_SCHOOL, Branch.SEGMENT_KINDERGARTEN}:
                for grade in ["1 класс", "2 класс", "Ясли"]:
                    ClassQuota.objects.get_or_create(branch=branch, grade_or_group=grade, defaults={"capacity": 20, "occupied": 0})
            elif branch.segment == Branch.SEGMENT_FREE_SCHOOL:
                ClassQuota.objects.get_or_create(branch=branch, grade_or_group="Бесплатная группа", defaults={"capacity": 20, "occupied": 0})

        funnel_defs = [
            ("b2c_schools", "B2C Schools"),
            ("b2c_kindergarten", "B2C Kindergarten"),
            ("b2b_partnership", "B2B Partnership"),
        ]
        funnel_stages = {
            "b2c_schools": ["Unsorted", "Qualification", "Tour/Test Scheduled", "Tour/Test Passed", "Tariff & Addons Selection", "Entrance Fee Paid", "Contract Signed"],
            "b2c_kindergarten": ["New Lead", "Free Trial Day Set", "Adaptation Period", "Entrance Fee", "Monthly Payment", "Won"],
            "b2b_partnership": ["Primary Contact", "Qualification/Meeting", "Commercial Proposal", "Contract/Tender Negotiation", "Invoicing", "Deal Closed"],
        }
        funnels = []
        for slug, name in funnel_defs:
            funnel, _ = Funnel.objects.get_or_create(slug=slug, defaults={"name": name})
            funnels.append(funnel)
            for order, stage_name in enumerate(funnel_stages[slug], start=1):
                Stage.objects.get_or_create(
                    funnel=funnel, name=stage_name,
                    defaults={"order": order, "is_won": stage_name in {"Contract Signed", "Won", "Deal Closed"}},
                )
            if not funnel.stages.filter(is_won=True).exists():
                Stage.objects.get_or_create(funnel=funnel, name="Won", defaults={"order": 999, "is_won": True})
            if not funnel.stages.filter(is_lost=True).exists():
                Stage.objects.get_or_create(funnel=funnel, name="Lost", defaults={"order": 1000, "is_lost": True})

        # Тарифы — только для реально продающих филиалов
        tariff_defs = {
            "RIVIERA": [
                ("Выгодный", "4500000", "350000", 1),
                ("Стандарт", "4900000", "350000", 3),
                ("Стандарт Плюс", "5180000", "350000", 8),
            ],
            "QUANTUM_STEM": [
                ("Основной (9 траншей)", "4410000", "200000", 9),
                ("3 транша", "4200000", "200000", 3),
            ],
            "QUANTUM_TECH": [
                ("Основной (9 траншей)", "4410000", "200000", 9),
                ("3 транша", "4200000", "200000", 3),
            ],
            "ALDI_BI_CAPITAL_PARK": [("Помесячно 250k", "2500000", "200000", 1)],
            "ALDI_BI_GREENLINE_AQUA": [("Помесячно 165k", "1650000", "150000", 1)],
            "ALDI_BI_FLAGMAN": [("Помесячно 115k", "1150000", "100000", 1)],
        }
        for branch in branch_objs:
            for name, base, entrance, count in tariff_defs.get(branch.code, []):
                Tariff.objects.get_or_create(
                    branch=branch, name=name, grade_band="PRIMARY_SECONDARY",
                    defaults={"base_amount": Decimal(base), "entrance_fee": Decimal(entrance), "installments_count": count},
                )

        parent_names = [
            "Айгуль Серикова", "Нурлан Токтаев", "Мадина Оспанова", "Аслан Жумабаев",
            "Динара Бекетова", "Серик Куанышев", "Ляззат Айтмухамбетова", "Марина Куанышова",
        ]
        child_names = ["Аружан", "Нурали", "Дарина", "Рамазан", "Аня", "Ильяс", "София", "Али"]
        partner_names = ["Alem Logistics", "Global Education", "Bright Labs", "North Star", "EduBridge"]

        # ————— 16–20 сделок по ВСЕМ филиалам —————
        # Riviera: 7 (стадии: Unsorted→Contract Signed + 1 WON + 1 LOST) — чтобы manager/director Riviera видели заполненную доску
        riviera_deals = [
            ("unsorted", "ACTIVE"), ("qualification", "ACTIVE"), ("tour/test scheduled", "ACTIVE"),
            ("tariff & addons selection", "ACTIVE"), ("entrance fee paid", "ACTIVE"),
            ("contract signed", "WON"), ("lost", "LOST"),
        ]
        # Quantum: 4
        quantum_deals = [
            ("qualification", "ACTIVE"), ("tour/test scheduled", "ACTIVE"),
            ("tariff & addons selection", "ACTIVE"), ("contract signed", "WON"),
        ]
        # ALDI Capital Park (Kindergarten): 4
        aldi_deals = [
            ("New Lead", "ACTIVE"), ("Free Trial Day Set", "ACTIVE"),
            ("Adaptation Period", "WAITLIST"), ("Monthly Payment", "WON"),
        ]
        # B2B: 2
        b2b_deals = [
            ("Commercial Proposal", "ACTIVE"), ("Deal Closed", "WON"),
        ]
        # Дополнительно: WAITLIST в Riviera и Quantum (для проверки бейджа Waitlist #N)
        extra_waitlist = [
            ("branch_code", "RIVIERA", "1 класс", "Тарас Булатов", "Нурали"),
            ("branch_code", "QUANTUM_STEM", "5 класс", "Гульмира Ахметова", "Аружан"),
        ]

        deal_plan = []
        b2c_school_funnel = funnels[0]
        for stage, status in riviera_deals:
            deal_plan.append({"funnel": funnels[0], "branch_code": "RIVIERA", "stage_in_funnel": b2c_school_funnel, "stage": stage, "status": status, "grade": "1 класс", "grade_band": "PRIMARY_SECONDARY", "is_riviera": True})
        for stage, status in quantum_deals:
            deal_plan.append({"funnel": funnels[0], "branch_code": "QUANTUM_STEM", "stage_in_funnel": b2c_school_funnel, "stage": stage, "status": status, "grade": "5 класс", "grade_band": "PRIMARY_SECONDARY", "is_riviera": False})
        kinder_funnel = funnels[1]
        for stage, status in aldi_deals:
            deal_plan.append({"funnel": funnels[1], "branch_code": "ALDI_BI_CAPITAL_PARK", "stage_in_funnel": kinder_funnel, "stage": stage, "status": status, "grade": "Ясли", "grade_band": "PRIMARY_SECONDARY", "is_riviera": False})
        b2b_funnel = funnels[2]
        for stage, status in b2b_deals:
            deal_plan.append({"funnel": funnels[2], "branch_code": "RIVIERA", "stage_in_funnel": b2b_funnel, "stage": stage, "status": status, "grade": "", "grade_band": "", "is_riviera": False, "is_b2b": True})

        index = 0
        for plan in deal_plan:
            branch = next(b for b in branch_objs if b.code == plan["branch_code"])
            index += 1
            funnel = plan["funnel"]
            status = plan["status"]

            # Выбираем стадию из плана (приводим к нижнему регистру для поиска)
            stage_name_lower = plan["stage"].lower()
            stage = None
            for s in funnel.stages.order_by("order"):
                if s.name.lower() == stage_name_lower:
                    stage = s
                    break
            if status == "WON":
                stage = funnel.stages.filter(is_won=True).order_by("order").first() or funnel.stages.order_by("order").last()
            if status == "LOST":
                stage = funnel.stages.filter(is_lost=True).order_by("order").first() or funnel.stages.order_by("order").last()

            # Гарантия: stage никогда не должен быть None — иначе ValidationError
            # (например, 'tour scheduled' не совпадает с существующей 'Tour/Test Scheduled').
            if stage is None:
                self.stdout.write(self.style.WARNING(f"  Стадия '{plan['stage']}' не найдена, fallback на первую стадию {funnel.slug}"))
                stage = funnel.stages.order_by("order").first()

            if stage is None:
                raise CommandError(f"В воронке {funnel.slug} нет ни одной стадии — создайте стадии перед генерацией сделок.")

            parent = Contact.objects.create(
                full_name=parent_names[index % len(parent_names)],
                phone=f"+7701{1000000 + index}",
                contact_type=Contact.CONTACT_TYPE_PARENT,
            )
            child = None
            partner = None
            total_amount = Decimal("0")
            has_food = plan["is_riviera"] and index % 2 == 0
            has_transport = plan["is_riviera"] and index % 3 == 0

            if plan.get("is_b2b"):
                partner = Partner.objects.create(
                    company_name=partner_names[index % len(partner_names)],
                    partner_type=Partner.PARTNER_TYPE_CONSTRUCTION,
                    contact_person="Aynur", contact_phone=f"+7701{2000000 + index}",
                )
                contract_value = Decimal("4200000") if index % 2 == 0 else Decimal("5000000")
                deal = Deal.objects.create(funnel=funnel, stage=stage, branch=branch, partner=partner, contract_value=contract_value, total_amount=contract_value, status=status)
            else:
                child = Child.objects.create(parent=parent, full_name=child_names[index % len(child_names)], grade_or_group=plan["grade"], grade_band=plan["grade_band"])
                tariff_name = "Стандарт"
                if branch.code == "RIVIERA":
                    tariff_name = ["Выгодный", "Стандарт", "Стандарт Плюс"][index % 3]
                elif branch.code in {"QUANTUM_STEM", "QUANTUM_TECH"}:
                    tariff_name = "Основной (9 траншей)" if index % 2 == 0 else "3 транша"
                else:  # ALDI
                    tariff_name = "Помесячно 250k"
                tariff = Tariff.objects.filter(branch=branch, name=tariff_name).first()
                total_amount = calculate_total(branch.code, plan["grade_band"] or "PRIMARY_SECONDARY", tariff_name, has_food=has_food, has_transport=has_transport, transport_zone="CITY", has_second_child_discount=False, has_subsidy=False)
                deal = Deal.objects.create(
                    funnel=funnel, stage=stage, branch=branch, parent=parent, child=child,
                    tariff=tariff, has_food=has_food, has_transport=has_transport,
                    total_amount=total_amount, status=status,
                    is_cross_branch=status == "WAITLIST",
                )
                if status == "WAITLIST":
                    quota = ClassQuota.objects.filter(branch=branch, grade_or_group=child.grade_or_group).first()
                    if quota is not None:
                        quota.occupied = quota.capacity
                        quota.save(update_fields=["occupied"])
                    ActivityLog.objects.create(deal=deal, type="SYSTEM", actor="SYSTEM", content="Класс заполнен, лид переведён в лист ожидания")

            if status == "WON":
                ActivityLog.objects.create(deal=deal, type="SYSTEM", actor="SYSTEM", content="Сделка успешно закрыта и передана в финансовый блок")
            elif status == "LOST":
                ActivityLog.objects.create(deal=deal, type="SYSTEM", actor="SYSTEM", content="Лид не прошёл по критериям и закрыт как проигранный")

            # Платежи: PENDING / OVERDUE / PAID
            if not plan.get("is_b2b"):
                if status == "WON":
                    schedule_status = "PAID"
                elif index % 6 == 0:
                    schedule_status = "OVERDUE"  # для проверки индикаторов просрочки
                else:
                    schedule_status = "PENDING"
                PaymentSchedule.objects.create(
                    deal=deal,
                    title="Entrance fee",
                    due_date=date.today() + timedelta(days=10 + index % 7),
                    amount=tariff.entrance_fee if tariff else Decimal("200000"),
                    status=schedule_status,
                )

            if status != "LOST" and not plan.get("is_b2b") and status != "WAITLIST":
                Task.objects.create(deal=deal, title="Проверить следующий шаг по лид-обработке", due_date=date.today() + timedelta(days=2 + index % 3), is_done=status == "WON", auto_generated=True)

        # Дополнительные WAITLIST-сделки (чтобы было видно «Waitlist #N» в Riviera и Quantum)
        for idx, (_, branch_code, grade, parent_name, child_name) in enumerate(extra_waitlist):
            branch = next(b for b in branch_objs if b.code == branch_code)
            parent = Contact.objects.create(full_name=parent_name, phone=f"+7701{3000000 + idx}", contact_type=Contact.CONTACT_TYPE_PARENT)
            child = Child.objects.create(parent=parent, full_name=child_name, grade_or_group=grade, grade_band="PRIMARY_SECONDARY")
            funnel = b2c_school_funnel
            stage = funnel.stages.filter(name__iexact="Unsorted").first() or funnel.stages.order_by("order").first()
            tariff = Tariff.objects.filter(branch=branch).first()
            deal = Deal.objects.create(funnel=funnel, stage=stage, branch=branch, parent=parent, child=child, tariff=tariff, total_amount=Decimal("0"), status=Deal.STATUS_WAITLIST)
            quota = ClassQuota.objects.filter(branch=branch, grade_or_group=grade).first()
            if quota is not None:
                quota.occupied = quota.capacity
                quota.save(update_fields=["occupied"])
            ActivityLog.objects.create(deal=deal, type="SYSTEM", actor="SYSTEM", content="Класс заполнен, лид переведён в лист ожидания")
            PaymentSchedule.objects.create(deal=deal, title="Entrance fee", due_date=date.today() + timedelta(days=15 + idx), amount=Decimal("200000"), status="PENDING")

        # BINOM: лидогенерация с редиректом
        binom_branch = next(b for b in branch_objs if b.code == "BINOM_ASTANA_1")
        parent = Contact.objects.create(full_name="Нурлан BINOM", phone="+77019999999", contact_type=Contact.CONTACT_TYPE_PARENT)
        child = Child.objects.create(parent=parent, full_name="Миша BINOM", grade_or_group="1 класс", grade_band="PRIMARY_SECONDARY")
        deal = Deal.objects.create(funnel=funnels[0], stage=funnels[0].stages.order_by("order").first(), branch=binom_branch, parent=parent, child=child, total_amount=Decimal("0"), status="ACTIVE")
        ActivityLog.objects.create(deal=deal, type="SYSTEM", actor="SYSTEM", content="Заявка перенаправлена в BINOM через Mektep Smart Nation")

        self.stdout.write(self.style.SUCCESS(f"Created CRM mock data: {Deal.objects.count()} deals across {Branch.objects.count()} branches."))