from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsHQAdmin(BasePermission):
    """Доступ только для HQ_ADMIN."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "HQ_ADMIN"
        )


class IsBranchDirector(BasePermission):
    """Доступ только для BRANCH_DIRECTOR."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "BRANCH_DIRECTOR"
        )


class IsHQAdminOrBranchDirector(BasePermission):
    """Доступ для HQ_ADMIN и BRANCH_DIRECTOR (удаление, отметка платежей, финансы)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None)
            in {"HQ_ADMIN", "BRANCH_DIRECTOR"}
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == "HQ_ADMIN":
            return True
        if user.role == "BRANCH_DIRECTOR":
            branch = getattr(obj, "branch", None)
            if branch is None and hasattr(obj, "deal"):
                branch = getattr(obj.deal, "branch", None)
            return branch is not None and branch.id == user.branch_id
        return False


class IsHQAdminOrReadOnly(BasePermission):
    """Чтение — всем аутентифицированным, изменение — только HQ_ADMIN (прайс, конфиг)."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(user, "role", None) == "HQ_ADMIN"