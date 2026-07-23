"""URL routes for the keel-web client-panel shell.

Mount under a ``client`` namespace so the shared reverse() names resolve:

    path("client/", include("keel_web.client.urls", namespace="client"))

This ships only the shell routes (profile / billing / resend-verification). The
host adds its own product routes (dashboard, signals, etc.) under the same
namespace.
"""
from __future__ import annotations

from django.urls import path

from .views import BillingView, ProfileView, ResendVerificationView

app_name = "client"

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="profile"),
    path("billing/", BillingView.as_view(), name="billing"),
    path("resend-verification", ResendVerificationView.as_view(), name="resend_verification"),
]
