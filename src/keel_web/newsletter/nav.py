from django.urls import reverse


def newsletter_item():
    url = reverse("keel_web_newsletter:list")
    return {"label": "Newsletter", "icon": "mail", "url": url, "match_prefix": url}
