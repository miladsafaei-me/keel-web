"""The panel's newsletter pages. The public sign-up and unsubscribe views are not here: the host mounts them."""
from django.urls import path

from . import views

app_name = "keel_web_newsletter"

urlpatterns = [
    path("", views.subscriber_list, name="list"),
    path("export.csv", views.subscriber_export, name="export"),
    path("<int:pk>/toggle/", views.subscriber_toggle, name="toggle"),
    path("<int:pk>/delete/", views.subscriber_delete, name="delete"),
]
