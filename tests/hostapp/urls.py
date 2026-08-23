from django.urls import include, path

from . import views

urlpatterns = [
    path("page/", views.public_page, name="page"),
    path("form-page/", views.form_page, name="form_page"),
    path("no-store/", views.explicit_no_store, name="no_store"),
    path("vary-page/", views.vary_page, name="vary_page"),
    path("broken/", views.broken, name="broken"),
    # Exempt-prefix probe -- same view, path under the default "/admin" prefix.
    path("admin/dashboard/", views.public_page, name="admin_dashboard"),
    path("csrf-check/", views.csrf_check, name="csrf_check"),
    path("", include("keel_web.csrf_defer.urls")),
]
