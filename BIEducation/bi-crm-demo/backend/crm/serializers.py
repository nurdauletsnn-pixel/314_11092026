from django.contrib.auth import get_user_model

from rest_framework import serializers

from .models import ActivityLog, BotMessage, Branch, Child, Contact, Deal, Partner, PaymentSchedule, Stage, Tariff, Task

User = get_user_model()


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = "__all__"


class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = "__all__"


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = "__all__"


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = "__all__"


class PaymentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentSchedule
        fields = "__all__"
        read_only_fields = ("status",)


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ("is_done", "is_completed")


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = "__all__"


class BotMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotMessage
        fields = "__all__"


class StageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = "__all__"


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    branch = BranchSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "branch")


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "first_name", "last_name", "role", "branch")
        extra_kwargs = {"password": {"write_only": True}, "role": {"required": True}}

    def validate(self, attrs):
        role = attrs.get("role")
        branch = attrs.get("branch")
        if role != User.Role.HQ_ADMIN and branch is None:
            raise serializers.ValidationError(
                {"branch": "Филиал обязателен для ролей, отличных от HQ_ADMIN."}
            )
        if role == User.Role.HQ_ADMIN and branch is not None:
            raise serializers.ValidationError(
                {"branch": "HQ_ADMIN не привязывается к филиалу."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class DealSerializer(serializers.ModelSerializer):
    parent = ContactSerializer(read_only=True)
    child = ChildSerializer(read_only=True)
    partner = PartnerSerializer(read_only=True)
    branch = BranchSerializer(read_only=True)
    tariff = TariffSerializer(read_only=True)
    payment_schedules = PaymentScheduleSerializer(many=True, read_only=True)
    tasks = TaskSerializer(many=True, read_only=True)
    activity = ActivityLogSerializer(many=True, read_only=True)
    bot_messages = BotMessageSerializer(many=True, read_only=True)
    branch_code = serializers.CharField(source="branch.code", read_only=True)
    funnel_slug = serializers.CharField(source="funnel.slug", read_only=True)
    stage_name = serializers.CharField(source="stage.name", read_only=True)
    pipeline = serializers.SerializerMethodField()
    # Гео-роутинг (раздел 8.5)
    source_city = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    source_branch_requested = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # Анти-дубль (раздел 7, Риск 4) — id исходного Contact
    is_duplicate_of = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.all(), required=False, allow_null=True
    )

    def get_pipeline(self, obj):
        slug = (getattr(obj.funnel, "slug", "") or "").lower()
        if slug in {"b2b_partnership", "b2b"}:
            return "B2B"
        if slug in {"b2c_kindergarten", "b2c_kindergartens", "b2c_kinder"}:
            return "B2C_KINDERGARTEN"
        return "B2C_SCHOOL"

    class Meta:
        model = Deal
        fields = "__all__"
