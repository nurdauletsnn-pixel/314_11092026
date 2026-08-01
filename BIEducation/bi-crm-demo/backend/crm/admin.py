from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ActivityLog, BotMessage, Branch, Child, ClassQuota, Contact, Deal, Funnel, Partner, PaymentSchedule, Stage, Tariff, Task, User

admin.site.register(Branch)
admin.site.register(ClassQuota)
admin.site.register(Funnel)
admin.site.register(Stage)
admin.site.register(Contact)
admin.site.register(Child)
admin.site.register(Partner)
admin.site.register(Tariff)
admin.site.register(Deal)
admin.site.register(PaymentSchedule)
admin.site.register(Task)
admin.site.register(ActivityLog)
admin.site.register(BotMessage)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "branch", "is_staff")
    list_filter = ("role", "branch", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("RBAC", {"fields": ("role", "branch")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("RBAC", {"fields": ("role", "branch")}),
    )
