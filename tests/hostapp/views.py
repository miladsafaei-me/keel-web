from django.http import HttpResponse, HttpResponseServerError
from django.shortcuts import render


def csrf_check(request):
    """A plain CSRF-protected POST target -- exercises the deferred-CSRF flow
    end to end: fetch a token from keel_web.csrf_defer, then post here with it.
    """
    return HttpResponse("ok")


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
