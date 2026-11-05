"""The newsletter: the panel's list of subscribers (search, add, unsubscribe, delete, CSV),
and two public views a host may mount on addresses of its choosing.

Panel: ``include("keel_web.newsletter.urls")`` inside the panel. Public: the host wires
``subscribe`` (POST, form or JSON, answers JSON) and ``unsubscribe`` (the link in each
email, ``?t=<token>``) itself, so no public address appears until the host adds one.
"""
from __future__ import annotations

import csv
import json

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from keel_web.admin_shell.context import render_panel, staff_required
from keel_web.admin_shell.forms import PanelFormMixin

from .models import NewsletterSubscriber, subscribe as add_subscriber


class SubscriberForm(PanelFormMixin, forms.Form):
    """Adding an address already on the list subscribes it again instead of failing."""

    email = forms.EmailField()
    name = forms.CharField(max_length=120, required=False)
    language = forms.CharField(max_length=12, required=False, help_text="The language they signed up in.")
    source = forms.CharField(max_length=120, required=False, help_text="Where they signed up, such as a page or a form.")


def _filtered(request):
    rows = NewsletterSubscriber.objects.all()
    q = request.GET.get("q", "").strip()
    if q:
        rows = rows.filter(Q(email__icontains=q) | Q(name__icontains=q) | Q(source__icontains=q))
    status = request.GET.get("status", "")
    if status in NewsletterSubscriber.Status.values:
        rows = rows.filter(status=status)
    return rows, q, status


@staff_required
def subscriber_list(request):
    rows, q, status = _filtered(request)
    form = SubscriberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        row = add_subscriber(form.cleaned_data["email"], name=form.cleaned_data["name"],
                             language=form.cleaned_data["language"], source=form.cleaned_data["source"] or "panel")
        messages.success(request, f"{row.email} is on the list.")
        return redirect("keel_web_newsletter:list")
    counts = {"active": NewsletterSubscriber.objects.filter(status=NewsletterSubscriber.Status.ACTIVE).count(),
              "unsubscribed": NewsletterSubscriber.objects.filter(status=NewsletterSubscriber.Status.UNSUBSCRIBED).count()}
    query = "&".join(f"{k}={v}" for k, v in (("q", q), ("status", status)) if v)
    return render_panel(request, "keel_web_newsletter/list.html", {
        "page_title": "Newsletter", "page_pretitle": "Audience", "page_obj": Paginator(rows, 50).get_page(request.GET.get("page")),
        "q": q, "status": status, "query": query, "form": form, "counts": counts,
        "statuses": NewsletterSubscriber.Status.choices})


@staff_required
def subscriber_export(request):
    rows, _, _ = _filtered(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="newsletter-{timezone.localdate():%Y-%m-%d}.csv"'
    writer = csv.writer(response)
    writer.writerow(["email", "name", "language", "source", "status", "subscribed_at", "unsubscribed_at"])
    for row in rows.iterator():
        writer.writerow([row.email, row.name, row.language, row.source, row.status,
                         row.created_at.isoformat(), row.unsubscribed_at.isoformat() if row.unsubscribed_at else ""])
    return response


@staff_required
@require_POST
def subscriber_toggle(request, pk):
    row = get_object_or_404(NewsletterSubscriber, pk=pk)
    if row.status == NewsletterSubscriber.Status.ACTIVE:
        row.unsubscribe()
        messages.success(request, f"{row.email} is unsubscribed.")
    else:
        row.resubscribe()
        messages.success(request, f"{row.email} is subscribed again.")
    return redirect(request.POST.get("next") or "keel_web_newsletter:list")


@staff_required
@require_POST
def subscriber_delete(request, pk):
    row = get_object_or_404(NewsletterSubscriber, pk=pk)
    row.delete()
    messages.success(request, f"{row.email} is deleted.")
    return redirect("keel_web_newsletter:list")


@require_POST
def subscribe(request):
    """Public sign-up. Takes ``email`` (and optional ``name``, ``language``, ``source``) as a form or JSON."""
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body or b"{}")
        except ValueError:
            data = {}
    else:
        data = request.POST
    email = str(data.get("email", "")).strip()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"ok": False, "error": "email"}, status=400)
    add_subscriber(email, name=str(data.get("name", ""))[:120], language=str(data.get("language", ""))[:12],
                   source=str(data.get("source", ""))[:120])
    return JsonResponse({"ok": True})


def unsubscribe(request):
    """The link in each email: GET asks to confirm, POST unsubscribes. Unknown tokens see the same page."""
    row = NewsletterSubscriber.objects.filter(token=request.GET.get("t", "")).first()
    done = False
    if request.method == "POST" and row:
        row.unsubscribe()
        done = True
    response = render(request, "keel_web_newsletter/unsubscribe.html", {"row": row, "done": done})
    response["X-Robots-Tag"] = "noindex"
    return response
