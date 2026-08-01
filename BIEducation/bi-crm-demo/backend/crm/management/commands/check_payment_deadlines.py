from django.core.management.base import BaseCommand

from crm.services.automation import check_payment_deadlines


class Command(BaseCommand):
    help = "Проверяет дедлайны платежей: создаёт напоминания (D-3) и переводит просроченные (D+2) в OVERDUE."

    def handle(self, *args, **options):
        stats = check_payment_deadlines()
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: напоминаний D-3 создано {stats['reminders_created']}, "
                f"платежей переведено в OVERDUE {stats['overdue_promoted']}, "
                f"задач создано {stats['tasks_created']}."
            )
        )