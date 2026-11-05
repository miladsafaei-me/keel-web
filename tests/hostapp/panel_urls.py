from django.urls import include, path

urlpatterns = [
    path("panel/", include("keel_web.panel.urls")),
    path("panel/newsletter/", include("keel_web.newsletter.urls")),
]


def nav(request):
    from keel_web.newsletter.nav import newsletter_item
    from keel_web.panel.nav import account_section, dashboard_item

    return [{"label": "Overview", "items": [dashboard_item(), newsletter_item()]}, account_section(request)]


def cards(request):
    return [{"label": "Things", "value": 3, "icon": "calendar"}]
