from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from crm.models import Branch


class Command(BaseCommand):
    help = "Seed CRM users with RBAC roles and branches (раздел 8 спецификации)"

    def handle(self, *args, **options):
        User = get_user_model()

        # Создаём (или получаем) филиалы ДО привязки пользователей, иначе
        # user.branch останется None и менеджеры/директора не увидят сделок.
        branch_defs = [
            {"name": "Riviera International School", "code": "RIVIERA", "city": "Астана", "segment": Branch.SEGMENT_SCHOOL},
            {"name": "Quantum STEM School", "code": "QUANTUM_STEM", "city": "Астана", "segment": Branch.SEGMENT_SCHOOL},
            {"name": "Quantum TECH School", "code": "QUANTUM_TECH", "city": "Астана", "segment": Branch.SEGMENT_SCHOOL},
            {"name": "ALDI BI Capital Park", "code": "ALDI_BI_CAPITAL_PARK", "city": "Астана", "segment": Branch.SEGMENT_KINDERGARTEN},
        ]
        branches = {}
        for payload in branch_defs:
            branch, created = Branch.objects.get_or_create(
                code=payload["code"],
                defaults={k: v for k, v in payload.items() if k != "code"},
            )
            branches[branch.code] = branch
            if created:
                self.stdout.write(f"  Created branch {branch.code}")

        users = [
            # (username, email, role, branch_code)
            ("hq_admin", "hq_admin@test.com", User.Role.HQ_ADMIN, None),
            ("director_riviera", "director.riviera@test.com", User.Role.BRANCH_DIRECTOR, "RIVIERA"),
            ("manager_riviera", "manager.riviera@test.com", User.Role.SALES_MANAGER, "RIVIERA"),
            ("director_quantum", "director.quantum@test.com", User.Role.BRANCH_DIRECTOR, "QUANTUM_STEM"),
            ("manager_quantum", "manager.quantum@test.com", User.Role.SALES_MANAGER, "QUANTUM_STEM"),
            ("director_aldi", "director.aldi@test.com", User.Role.BRANCH_DIRECTOR, "ALDI_BI_CAPITAL_PARK"),
            ("manager_aldi", "manager.aldi@test.com", User.Role.SALES_MANAGER, "ALDI_BI_CAPITAL_PARK"),
        ]

        for username, email, role, branch_code in users:
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": email}
            )
            user.email = email
            user.role = role
            branch = branches.get(branch_code) if branch_code else None
            # ЯВНАЯ привязка к филиалу: даже если пользователь уже существовал
            # и branch был None (например, seed_users запускался до generate_mock_data).
            user.branch = branch
            user.set_password("administrator")
            user.save()
            if created:
                self.stdout.write(f"  Created {username} -> {role} / {branch_code or '-'}")
            elif user.branch_id != (branch.id if branch else None):
                self.stdout.write(f"  Rebound {username} -> {branch_code or '-'}")

        self.stdout.write(self.style.SUCCESS("Seeded CRM users with RBAC roles"))