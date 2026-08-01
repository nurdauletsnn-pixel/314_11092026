from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChildViewSet, ContactViewSet, DealViewSet, MeView, PaymentScheduleViewSet, TariffViewSet, TaskViewSet

router = DefaultRouter()
router.register(r"contacts", ContactViewSet, basename="contact")
router.register(r"deals", DealViewSet, basename="deal")
router.register(r"children", ChildViewSet, basename="child")
router.register(r"payment-schedules", PaymentScheduleViewSet, basename="payment-schedule")
router.register(r"tariffs", TariffViewSet, basename="tariff")
router.register(r"tasks", TaskViewSet, basename="task")

urlpatterns = [
    path("me/", MeView.as_view({"get": "list", "patch": "update"}), name="me"),
    path("", include(router.urls)),
]
