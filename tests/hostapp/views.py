from django.http import HttpResponseServerError
from django.shortcuts import render


def public_page(request):
    return render(request, "hostapp/page.html", {})


def form_page(request):
    return render(request, "hostapp/form_page.html", {})


def explicit_no_store(request):
    response = render(request, "hostapp/page.html", {})
    response["Cache-Control"] = "no-store"
    return response


def vary_page(request):
    response = render(request, "hostapp/page.html", {})
    response["Vary"] = "Accept-Language, X-Custom-Header"
    return response


def broken(request):
    return HttpResponseServerError("boom")
