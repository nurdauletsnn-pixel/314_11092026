from io import StringIO
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .business_logic import calculate_total
from .models import (
    ActivityLog,
    Branch,
    Child,
    ClassQuota,
    Contact,
    Deal,
    Funnel,
    Partner,
    PaymentSchedule,
    Stage,
    Task,
    User,
)

User = get_user_model()


def _unique_phone():
    import random

    return f"+7701{random.randint(1_000_000, 9_999_999)}"


class PricingCalculationTests(TestCase):
    def test_riviera_standard_primary_secondary(self):
        self.assertEqual(
            calculate_total(
                branch_code="RIVIERA",
                grade_band="PRIMARY_SECONDARY",
                tariff_name="Стандарт",
                has_food=True,
                has_transport=True,
                transport_zone="CITY",
                has_second_child_discount=False,
                has_subsidy=False,
            ),
            Decimal("4_900_000") + Decimal("752_400") + Decimal("57_000"),
        )

    def test_riviera_preschool_profitable(self):
        self.assertEqual(
            calculate_total(
                branch_code="RIVIERA",
                grade_band="PRESCHOOL",
                tariff_name="Выгодный",
                has_food=False,
                has_transport=False,
                transport_zone="CITY",
                has_second_child_discount=False,
                has_subsidy=False,
            ),
            Decimal("3_500_000"),
        )

    def test_quantum_basic(self):
        self.assertEqual(
            calculate_total(
                branch_code="QUANTUM_STEM",
                grade_band="PRIMARY_SECONDARY",
                tariff_name="Основной (9 траншей)",
                has_food=True,
                has_transport=False,
                transport_zone="CITY",
                has_second_child_discount=False,
                has_subsidy=False,
            ),
            Decimal("4_410_000") + Decimal("630_000") + Decimal("200_000"),
        )

    def test_aldi_bi_subsidy_and_second_child(self):
        branch = Branch.objects.create(
            name="ALDI BI Capital Park",
            code="ALDI_BI_CAPITAL_PARK",
            city="Астана",
            segment="KINDERGARTEN",
            is_free=False,
            subsidy_amount=Decimal("50_000"),
        )
        self.assertEqual(
            calculate_total(
                branch_code=branch.code,
                grade_band="PRESCHOOL",
                tariff_name="",
                has_food=False,
                has_transport=False,
                transport_zone="CITY",
                has_second_child_discount=True,
                has_subsidy=True,
            ),
            Decimal("250_000") - Decimal("50_000") - Decimal("25_000"),
        )


class DealModelTests(TestCase):
    def test_deal_clean_blocks_b2c_with_partner(self):
        funnel = Funnel.objects.create(slug="b2c_schools", name="B2C Schools")
        stage = Stage.objects.create(funnel=funnel, name="Qualification", order=1)
        branch = Branch.objects.create(name="Riviera", code="RIVIERA", city="Астана", segment="SCHOOL")
        parent = Contact.objects.create(full_name="Parent", phone="+77010000001", contact_type="PARENT")
        child = Child.objects.create(parent=parent, full_name="Child", grade_or_group="1 класс", grade_band="PRIMARY_SECONDARY")
        partner = Partner.objects.create(company_name="Acme", partner_type="CONSTRUCTION", contact_person="Person", contact_phone="+77010000002")
        deal = Deal(funnel=funnel, stage=stage, branch=branch, parent=parent, child=child, partner=partner)
        with self.assertRaises(ValidationError):
            deal.clean()

    def test_deal_clean_blocks_b2b_with_contact(self):
        funnel = Funnel.objects.create(slug="b2b_partnership", name="B2B")
        stage = Stage.objects.create(funnel=funnel, name="Qualification", order=1)
        branch = Branch.objects.create(name="BIART", code="BIART", city="Астана", segment="CREATIVE")
        parent = Contact.objects.create(full_name="Parent", phone="+77010000003", contact_type="PARENT")
        partner = Partner.objects.create(company_name="Acme", partner_type="BIART_RENTAL", contact_person="Person", contact_phone="+77010000004")
        deal = Deal(funnel=funnel, stage=stage, branch=branch, parent=parent, partner=partner)
        with self.assertRaises(ValidationError):
            deal.clean()


class QuotaReleaseTests(TestCase):
    def test_release_quota_slot_assigns_first_waitlisted_deal(self):
        branch = Branch.objects.create(name="Riviera", code="RIVIERA", city="Астана", segment="SCHOOL")
        quota = ClassQuota.objects.create(branch=branch, grade_or_group="1 класс", capacity=1, occupied=1)
        funnel = Funnel.objects.create(slug="b2c_schools", name="B2C Schools")
        stage = Stage.objects.create(funnel=funnel, name="Qualification", order=1)
        parent1 = Contact.objects.create(full_name="Parent 1", phone="+77010000005", contact_type="PARENT")
        child1 = Child.objects.create(parent=parent1, full_name="Child 1", grade_or_group="1 класс", grade_band="PRIMARY_SECONDARY")
        parent2 = Contact.objects.create(full_name="Parent 2", phone="+77010000006", contact_type="PARENT")
        child2 = Child.objects.create(parent=parent2, full_name="Child 2", grade_or_group="1 класс", grade_band="PRIMARY_SECONDARY")
        first = Deal.objects.create(funnel=funnel, stage=stage, branch=branch, parent=parent1, child=child1, status="WAITLIST", total_amount=Decimal("100"))
        second = Deal.objects.create(funnel=funnel, stage=stage, branch=branch, parent=parent2, child=child2, status="WAITLIST", total_amount=Decimal("200"))

        quota.occupied = 0
        quota.save(update_fields=["occupied"])
        first.release_quota_slot()

        first.refresh_from_db()
        self.assertEqual(first.status, "ACTIVE")
        self.assertEqual(ActivityLog.objects.filter(deal=first).count(), 1)
        self.assertEqual(Task.objects.filter(deal=second).count(), 0)


class UserModelTests(TestCase):
    def test_hq_admin_can_have_no_branch(self):
        user = User(username="hq", role=User.Role.HQ_ADMIN, branch=None)
        user.clean()
        user.save()
        self.assertIsNone(user.branch)

    def test_non_hq_admin_requires_branch(self):
        user = User(username="manager", role=User.Role.SALES_MANAGER, branch=None)
        with self.assertRaises(ValidationError):
            user.clean()


class RBACApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.branch_a = Branch.objects.create(name="Riviera", code="RIVIERA", city="Астана", segment="SCHOOL")
        self.branch_b = Branch.objects.create(name="Quantum", code="QUANTUM_STEM", city="Астана", segment="SCHOOL")

        self.hq = User.objects.create_user(username="hq_admin", password="pass1234", role=User.Role.HQ_ADMIN)
        self.director = User.objects.create_user(username="director", password="pass1234", role=User.Role.BRANCH_DIRECTOR, branch=self.branch_a)
        self.manager = User.objects.create_user(username="manager", password="pass1234", role=User.Role.SALES_MANAGER, branch=self.branch_a)

        self.hq_token = Token.objects.create(user=self.hq)
        self.director_token = Token.objects.create(user=self.director)
        self.manager_token = Token.objects.create(user=self.manager)

        self.funnel = Funnel.objects.create(slug="b2c_schools", name="B2C Schools")
        self.stage = Stage.objects.create(funnel=self.funnel, name="Qualification", order=1)

        self.deal_a = self._make_deal(self.branch_a)
        self.deal_b = self._make_deal(self.branch_b)

    def _make_deal(self, branch):
        parent = Contact.objects.create(full_name="Parent", phone=_unique_phone(), contact_type="PARENT")
        child = Child.objects.create(parent=parent, full_name="Child", grade_or_group="1 класс", grade_band="PRIMARY_SECONDARY")
        return Deal.objects.create(funnel=self.funnel, stage=self.stage, branch=branch, parent=parent, child=child, total_amount=Decimal("1000"))

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_hq_admin_sees_all_deals(self):
        self._auth(self.hq_token)
        response = self.client.get("/api/deals/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_manager_sees_only_own_branch_deals(self):
        self._auth(self.manager_token)
        response = self.client.get("/api/deals/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.deal_a.id)

    def test_director_sees_only_own_branch_deals(self):
        self._auth(self.director_token)
        response = self.client.get("/api/deals/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.deal_a.id)

    def test_manager_cannot_retrieve_other_branch_deal(self):
        self._auth(self.manager_token)
        response = self.client.get(f"/api/deals/{self.deal_b.id}/")
        self.assertEqual(response.status_code, 404)

    def test_hq_admin_can_retrieve_any_deal(self):
        self._auth(self.hq_token)
        response = self.client.get(f"/api/deals/{self.deal_b.id}/")
        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_delete_deal(self):
        self._auth(self.manager_token)
        response = self.client.delete(f"/api/deals/{self.deal_a.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Deal.objects.filter(pk=self.deal_a.id).exists())

    def test_director_can_delete_own_branch_deal(self):
        self._auth(self.director_token)
        response = self.client.delete(f"/api/deals/{self.deal_a.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Deal.objects.filter(pk=self.deal_a.id).exists())

    def test_director_cannot_delete_other_branch_deal(self):
        self._auth(self.director_token)
        response = self.client.delete(f"/api/deals/{self.deal_b.id}/")
        self.assertEqual(response.status_code, 404)

    def test_hq_admin_can_delete_any_deal(self):
        self._auth(self.hq_token)
        response = self.client.delete(f"/api/deals/{self.deal_b.id}/")
        self.assertEqual(response.status_code, 204)

    def test_manager_cannot_mark_paid(self):
        self._auth(self.manager_token)
        schedule = PaymentSchedule.objects.create(deal=self.deal_a, title="Entrance", due_date="2026-08-01", amount=Decimal("100"), status="PENDING")
        response = self.client.post(f"/api/payment-schedules/{schedule.id}/mark-paid/")
        self.assertEqual(response.status_code, 403)

    def test_director_can_mark_paid(self):
        self._auth(self.director_token)
        schedule = PaymentSchedule.objects.create(deal=self.deal_a, title="Entrance", due_date="2026-08-01", amount=Decimal("100"), status="PENDING")
        response = self.client.post(f"/api/payment-schedules/{schedule.id}/mark-paid/")
        self.assertEqual(response.status_code, 200)
        schedule.refresh_from_db()
        self.assertEqual(schedule.status, "PAID")

    def test_manager_cannot_update_payment_status_via_put(self):
        self._auth(self.manager_token)
        schedule = PaymentSchedule.objects.create(deal=self.deal_a, title="Entrance", due_date="2026-08-01", amount=Decimal("100"), status="PENDING")
        response = self.client.patch(f"/api/payment-schedules/{schedule.id}/", {"status": "PAID"}, format="json")
        self.assertEqual(response.status_code, 200)
        schedule.refresh_from_db()
        self.assertEqual(schedule.status, "PENDING")

    def test_me_returns_role_and_branch(self):
        self._auth(self.manager_token)
        response = self.client.get("/api/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], "SALES_MANAGER")
        self.assertEqual(response.data["branch"]["id"], self.branch_a.id)

    def test_auth_token_returns_role_and_branch(self):
        response = self.client.post(
            "/api/auth/token/",
            {"username": "manager", "password": "pass1234"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "SALES_MANAGER")
        self.assertEqual(response.data["user"]["branch"]["id"], self.branch_a.id)

    def test_manager_metadata_only_own_branch(self):
        self._auth(self.manager_token)
        response = self.client.get("/api/deals/metadata/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["branches"]), 1)
        self.assertEqual(response.data["branches"][0]["id"], self.branch_a.id)


class MockDataGenerationTests(TestCase):
    def test_generate_mock_data_creates_varied_lead_statuses(self):
        call_command("generate_mock_data", stdout=StringIO(), stderr=StringIO())

        deals = Deal.objects.all()
        statuses = set(deals.values_list("status", flat=True))

        self.assertGreaterEqual(deals.count(), 20)
        self.assertIn(Deal.STATUS_ACTIVE, statuses)
        self.assertIn(Deal.STATUS_WAITLIST, statuses)
        self.assertIn(Deal.STATUS_LOST, statuses)
        self.assertIn(Deal.STATUS_WON, statuses)