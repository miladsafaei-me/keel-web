"""Inline SVG icon system. Replaces the Tabler webfont vendor.

Usage:
    {% load icons %}
    {% icon "dashboard" %}
    {% icon "x" class="text-lg text-gray-500" %}
    {% icon "logout" size=20 %}

The icon set is derived from Tabler Icons v3.30 (outline, MIT). New icons
should be pasted into ``_ICONS`` from https://tabler.io/icons — copy the
inner contents of the ``<svg>`` element only; the outer wrapper is added
by the templatetag.
"""
from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_ICONS: dict[str, str] = {
    "alert-circle": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0' /> <path d='M12 8v4' /> <path d='M12 16h.01' />",
    "alert-triangle": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 9v4' /> <path d='M10.363 3.591l-8.106 13.534a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636 -2.87l-8.106 -13.536a1.914 1.914 0 0 0 -3.274 0z' /> <path d='M12 16h.01' />",
    "arrow-right": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 12l14 0' /> <path d='M13 18l6 -6' /> <path d='M13 6l6 6' />",
    "arrow-up-right": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M17 7l-10 10' /> <path d='M8 7l9 0l0 9' />",
    "bell": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M10 5a2 2 0 1 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3h-16a4 4 0 0 0 2 -3v-3a7 7 0 0 1 4 -6' /> <path d='M9 17v1a3 3 0 0 0 6 0v-1' />",
    "bolt": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M13 3l0 7l6 0l-8 11l0 -7l-6 0l8 -11' />",
    "calendar": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 7a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12z' /> <path d='M16 3v4' /> <path d='M8 3v4' /> <path d='M4 11h16' /> <path d='M11 15h1' /> <path d='M12 15v3' />",
    "camera": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 7h1a2 2 0 0 0 2 -2a1 1 0 0 1 1 -1h6a1 1 0 0 1 1 1a2 2 0 0 0 2 2h1a2 2 0 0 1 2 2v9a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-9a2 2 0 0 1 2 -2' /> <path d='M9 13a3 3 0 1 0 6 0a3 3 0 0 0 -6 0' />",
    "chart-candle": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 6m0 1a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v3a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z' /> <path d='M6 4l0 2' /> <path d='M6 11l0 9' /> <path d='M10 14m0 1a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v3a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z' /> <path d='M12 4l0 10' /> <path d='M12 19l0 1' /> <path d='M16 5m0 1a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v4a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z' /> <path d='M18 4l0 1' /> <path d='M18 11l0 9' />",
    "check": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 12l5 5l10 -10' />",
    "chevron-down": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M6 9l6 6l6 -6' />",
    "circle-check": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0' /> <path d='M9 12l2 2l4 -4' />",
    "coin": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0' /> <path d='M14.8 9a2 2 0 0 0 -1.8 -1h-2a2 2 0 1 0 0 4h2a2 2 0 1 1 0 4h-2a2 2 0 0 1 -1.8 -1' /> <path d='M12 7v10' />",
    "credit-card": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 5m0 3a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v8a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3z' /> <path d='M3 10l18 0' /> <path d='M7 15l.01 0' /> <path d='M11 15l2 0' />",
    "credit-card-off": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 3l18 18' /> <path d='M9 5h9a3 3 0 0 1 3 3v8a3 3 0 0 1 -.128 .87' /> <path d='M18.87 18.872a3 3 0 0 1 -.87 .128h-12a3 3 0 0 1 -3 -3v-8c0 -1.352 .894 -2.495 2.124 -2.87' /> <path d='M3 11l8 0' /> <path d='M15 11l6 0' /> <path d='M7 15l.01 0' /> <path d='M11 15l2 0' />",
    "dashboard": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 13m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0' /> <path d='M13.45 11.55l2.05 -2.05' /> <path d='M6.4 20a9 9 0 1 1 11.2 0z' />",
    "dice-5": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 3m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v14a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z' /> <circle cx='8.5' cy='8.5' r='.5' fill='currentColor' /> <circle cx='15.5' cy='8.5' r='.5' fill='currentColor' /> <circle cx='15.5' cy='15.5' r='.5' fill='currentColor' /> <circle cx='8.5' cy='15.5' r='.5' fill='currentColor' /> <circle cx='12' cy='12' r='.5' fill='currentColor' />",
    "dots": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M19 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' />",
    "download": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2' /> <path d='M7 11l5 5l5 -5' /> <path d='M12 4l0 12' />",
    "edit": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1' /> <path d='M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z' /> <path d='M16 5l3 3' />",
    "external-link": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 6h-6a2 2 0 0 0 -2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-6' /> <path d='M11 13l9 -9' /> <path d='M15 4h5v5' />",
    "flask": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M9 3l6 0' /> <path d='M10 9l4 0' /> <path d='M10 3v6l-4 11a.7 .7 0 0 0 .5 1h11a.7 .7 0 0 0 .5 -1l-4 -11v-6' />",
    "grid-dots": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M12 5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M19 5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M5 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M19 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M5 19m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M12 19m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M19 19m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' />",
    "info-circle": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0' /> <path d='M12 9h.01' /> <path d='M11 12h1v4h1' />",
    "key": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M16.555 3.843l3.602 3.602a2.877 2.877 0 0 1 0 4.069l-2.643 2.643a2.877 2.877 0 0 1 -4.069 0l-.301 -.301l-6.558 6.558a2 2 0 0 1 -1.239 .578l-.175 .008h-1.172a1 1 0 0 1 -.993 -.883l-.007 -.117v-1.172a2 2 0 0 1 .467 -1.284l.119 -.13l.414 -.414h2v-2h2v-2l2.144 -2.144l-.301 -.301a2.877 2.877 0 0 1 0 -4.069l2.643 -2.643a2.877 2.877 0 0 1 4.069 0z' /> <path d='M15 9h.01' />",
    "logout": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M14 8v-2a2 2 0 0 0 -2 -2h-7a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h7a2 2 0 0 0 2 -2v-2' /> <path d='M9 12h12l-3 -3' /> <path d='M18 15l3 -3' />",
    "mail-forward": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 18h-7a2 2 0 0 1 -2 -2v-10a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v7.5' /> <path d='M3 6l9 6l9 -6' /> <path d='M15 18h6' /> <path d='M18 15l3 3l-3 3' />",
    "menu-2": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 6l16 0' /> <path d='M4 12l16 0' /> <path d='M4 18l16 0' />",
    "moon": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1 -8.313 -12.454z' />",
    "palette": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 21a9 9 0 0 1 0 -18c4.97 0 9 3.582 9 8c0 1.06 -.474 2.078 -1.318 2.828c-.844 .75 -1.989 1.172 -3.182 1.172h-2.5a2 2 0 0 0 -1 3.75a1.3 1.3 0 0 1 -1 2.25' /> <path d='M8.5 10.5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M12.5 7.5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M16.5 10.5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' />",
    "photo": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M15 8h.01' /> <path d='M3 6a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v12a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3v-12z' /> <path d='M3 16l5 -5c.928 -.893 2.072 -.893 3 0l5 5' /> <path d='M14 14l1 -1c.928 -.893 2.072 -.893 3 0l3 3' />",
    "plug": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M9.785 6l8.215 8.215l-2.054 2.054a5.81 5.81 0 1 1 -8.215 -8.215l2.054 -2.054z' /> <path d='M4 20l3.5 -3.5' /> <path d='M15 4l-3.5 3.5' /> <path d='M20 9l-3.5 3.5' />",
    "plus": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 5l0 14' /> <path d='M5 12l14 0' />",
    "refresh": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4' /> <path d='M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4' />",
    "robot": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M6 4m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v4a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z' /> <path d='M12 2v2' /> <path d='M9 12v9' /> <path d='M15 12v9' /> <path d='M5 16l4 -2' /> <path d='M15 14l4 2' /> <path d='M9 18h6' /> <path d='M10 8v.01' /> <path d='M14 8v.01' />",
    "sparkles": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M16 18a2 2 0 0 1 2 2a2 2 0 0 1 2 -2a2 2 0 0 1 -2 -2a2 2 0 0 1 -2 2zm0 -12a2 2 0 0 1 2 2a2 2 0 0 1 2 -2a2 2 0 0 1 -2 -2a2 2 0 0 1 -2 2zm-7 12a6 6 0 0 1 6 -6a6 6 0 0 1 -6 -6a6 6 0 0 1 -6 6a6 6 0 0 1 6 6z' />",
    "sun": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 12m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0' /> <path d='M3 12h1m8 -9v1m8 8h1m-9 8v1m-6.4 -15.4l.7 .7m12.1 -.7l-.7 .7m0 11.4l.7 .7m-12.1 -.7l-.7 .7' />",
    "target": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M12 12m-5 0a5 5 0 1 0 10 0a5 5 0 1 0 -10 0' /> <path d='M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0' />",
    "trash": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 7l16 0' /> <path d='M10 11l0 6' /> <path d='M14 11l0 6' /> <path d='M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12' /> <path d='M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3' />",
    "upload": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2' /> <path d='M7 9l5 -5l5 5' /> <path d='M12 4l0 12' />",
    "user-cog": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0' /> <path d='M6 21v-2a4 4 0 0 1 4 -4h2.5' /> <path d='M19.001 19m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0' /> <path d='M19.001 15.5v1.5' /> <path d='M19.001 21v1.5' /> <path d='M22.032 17.25l-1.299 .75' /> <path d='M17.27 20l-1.3 .75' /> <path d='M15.97 17.25l1.3 .75' /> <path d='M20.733 20l1.3 .75' />",
    "x": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M18 6l-12 12' /> <path d='M6 6l12 12' />",
    "arrow-narrow-left": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 12l14 0' /> <path d='M5 12l4 4' /> <path d='M5 12l4 -4' />",
    "arrow-narrow-right": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 12l14 0' /> <path d='M15 16l4 -4' /> <path d='M15 8l4 4' />",
    "arrows-exchange": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M7 10h14l-4 -4' /> <path d='M17 14h-14l4 4' />",
    "chart-line": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 19l16 0' /> <path d='M4 15l4 -6l4 2l4 -5l4 4' />",
    "chevron-left": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M15 6l-6 6l6 6' />",
    "chevron-right": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M9 6l6 6l-6 6' />",
    "exclamation-circle": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0' /> <path d='M12 9v4' /> <path d='M12 16v.01' />",
    "eye": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M10 12a2 2 0 1 0 4 0a2 2 0 0 0 -4 0' /> <path d='M21 12c-2.4 4 -5.4 6 -9 6c-3.6 0 -6.6 -2 -9 -6c2.4 -4 5.4 -6 9 -6c3.6 0 6.6 2 9 6' />",
    "file-export": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M14 3v4a1 1 0 0 0 1 1h4' /> <path d='M11.5 21h-4.5a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v5m-5 6h7m-3 -3l3 3l-3 3' />",
    "file-text": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M14 3v4a1 1 0 0 0 1 1h4' /> <path d='M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z' /> <path d='M9 9l1 0' /> <path d='M9 13l6 0' /> <path d='M9 17l6 0' />",
    "filter": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 4h16v2.172a2 2 0 0 1 -.586 1.414l-4.414 4.414v7l-6 2v-8.5l-4.48 -4.928a2 2 0 0 1 -.52 -1.345v-2.227z' />",
    "folder": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 4h4l3 3h7a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-11a2 2 0 0 1 2 -2' />",
    "folder-open": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 19l2.757 -7.351a1 1 0 0 1 .936 -.649h12.307a1 1 0 0 1 .986 1.164l-.996 5.211a2 2 0 0 1 -1.964 1.625h-14.026a2 2 0 0 1 -2 -2v-11a2 2 0 0 1 2 -2h4l3 3h7a2 2 0 0 1 2 2v2' />",
    "folder-plus": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 19h-7a2 2 0 0 1 -2 -2v-11a2 2 0 0 1 2 -2h4l3 3h7a2 2 0 0 1 2 2v3.5' /> <path d='M16 19h6' /> <path d='M19 16v6' />",
    "globe": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M7 9a4 4 0 1 0 8 0a4 4 0 0 0 -8 0' /> <path d='M5.75 15a8.015 8.015 0 1 0 9.25 -13' /> <path d='M11 17v4' /> <path d='M7 21h8' />",
    "hash": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 9l14 0' /> <path d='M5 15l14 0' /> <path d='M11 4l-4 16' /> <path d='M17 4l-4 16' />",
    "home": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 12l-2 0l9 -9l9 9l-2 0' /> <path d='M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7' /> <path d='M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6' />",
    "link": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M9 15l6 -6' /> <path d='M11 6l.463 -.536a5 5 0 0 1 7.071 7.072l-.534 .464' /> <path d='M13 18l-.397 .534a5.068 5.068 0 0 1 -7.127 0a4.972 4.972 0 0 1 0 -7.071l.524 -.463' />",
    "mail": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 7a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v10a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-10z' /> <path d='M3 7l9 6l9 -6' />",
    "message-circle": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 20l1.3 -3.9c-2.324 -3.437 -1.426 -7.872 2.1 -10.374c3.526 -2.501 8.59 -2.296 11.845 .48c3.255 2.777 3.695 7.266 1.029 10.501c-2.666 3.235 -7.615 4.215 -11.574 2.293l-4.7 1' />",
    "news": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M16 6h3a1 1 0 0 1 1 1v11a2 2 0 0 1 -4 0v-13a1 1 0 0 0 -1 -1h-10a1 1 0 0 0 -1 1v12a3 3 0 0 0 3 3h11' /> <path d='M8 8l4 0' /> <path d='M8 12l4 0' /> <path d='M8 16l4 0' />",
    "pencil": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 20h4l10.5 -10.5a2.828 2.828 0 1 0 -4 -4l-10.5 10.5v4' /> <path d='M13.5 6.5l4 4' />",
    "photo-edit": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M15 8h.01' /> <path d='M11 20h-4a3 3 0 0 1 -3 -3v-10a3 3 0 0 1 3 -3h10a3 3 0 0 1 3 3v4' /> <path d='M4 15l4 -4c.928 -.893 2.072 -.893 3 0l3 3' /> <path d='M14 14l1 -1c.31 -.298 .644 -.497 .987 -.596' /> <path d='M18.42 15.61a2.1 2.1 0 0 1 2.97 2.97l-3.39 3.42h-3v-3l3.42 -3.39z' />",
    "player-play": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M7 4v16l13 -8z' />",
    "puzzle": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 7h3a1 1 0 0 0 1 -1v-1a2 2 0 0 1 4 0v1a1 1 0 0 0 1 1h3a1 1 0 0 1 1 1v3a1 1 0 0 0 1 1h1a2 2 0 0 1 0 4h-1a1 1 0 0 0 -1 1v3a1 1 0 0 1 -1 1h-3a1 1 0 0 1 -1 -1v-1a2 2 0 0 0 -4 0v1a1 1 0 0 1 -1 1h-3a1 1 0 0 1 -1 -1v-3a1 1 0 0 1 1 -1h1a2 2 0 0 0 0 -4h-1a1 1 0 0 1 -1 -1v-3a1 1 0 0 1 1 -1' />",
    "search": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M10 10m-7 0a7 7 0 1 0 14 0a7 7 0 1 0 -14 0' /> <path d='M21 21l-6 -6' />",
    "settings": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 -.94 3.31 .826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0 -2.573 -1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 -.426 -1.756 -2.924 0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 2.37 -2.37c1 .608 2.296 .07 2.572 -1.065z' /> <path d='M9 12a3 3 0 1 0 6 0a3 3 0 0 0 -6 0' />",
    "switch-horizontal": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M16 3l4 4l-4 4' /> <path d='M10 7l10 0' /> <path d='M8 13l-4 4l4 4' /> <path d='M4 17l9 0' />",
    "tag": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M7.5 7.5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M3 6v5.172a2 2 0 0 0 .586 1.414l7.71 7.71a2.41 2.41 0 0 0 3.408 0l5.592 -5.592a2.41 2.41 0 0 0 0 -3.408l-7.71 -7.71a2 2 0 0 0 -1.414 -.586h-5.172a3 3 0 0 0 -3 3z' />",
    "trending-up": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 17l6 -6l4 4l8 -8' /> <path d='M14 7l7 0l0 7' />",
    "user-minus": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0' /> <path d='M6 21v-2a4 4 0 0 1 4 -4h4c.348 0 .686 .045 1.009 .128' /> <path d='M16 19h6' />",
    "users": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M9 7m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0' /> <path d='M3 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2' /> <path d='M16 3.13a4 4 0 0 1 0 7.75' /> <path d='M21 21v-2a4 4 0 0 0 -3 -3.85' />",
    "world": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0' /> <path d='M3.6 9h16.8' /> <path d='M3.6 15h16.8' /> <path d='M11.5 3a17 17 0 0 0 0 18' /> <path d='M12.5 3a17 17 0 0 1 0 18' />",
    "world-www": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M19.5 7a9 9 0 0 0 -7.5 -4a8.991 8.991 0 0 0 -7.484 4' /> <path d='M11.5 3a16.989 16.989 0 0 0 -1.826 4' /> <path d='M12.5 3a16.989 16.989 0 0 1 1.828 4' /> <path d='M19.5 17a9 9 0 0 1 -7.5 4a8.991 8.991 0 0 1 -7.484 -4' /> <path d='M11.5 21a16.989 16.989 0 0 1 -1.826 -4' /> <path d='M12.5 21a16.989 16.989 0 0 0 1.828 -4' />",
    "arrow-left": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 12l14 0' /> <path d='M5 12l6 6' /> <path d='M5 12l6 -6' />",
    "brand-github": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M9 19c-4.3 1.4 -4.3 -2.5 -6 -3m12 5v-3.5c0 -1 .1 -1.4 -.5 -2c2.8 -.3 5.5 -1.4 5.5 -6a4.6 4.6 0 0 0 -1.3 -3.2a4.2 4.2 0 0 0 -.1 -3.2s-1.1 -.3 -3.5 1.3a12.3 12.3 0 0 0 -6.2 0c-2.4 -1.6 -3.5 -1.3 -3.5 -1.3a4.2 4.2 0 0 0 -.1 3.2a4.6 4.6 0 0 0 -1.3 3.2c0 4.6 2.7 5.7 5.5 6c-.6 .6 -.6 1.2 -.5 2v3.5' />",
    "brand-instagram": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 8a4 4 0 0 1 4 -4h8a4 4 0 0 1 4 4v8a4 4 0 0 1 -4 4h-8a4 4 0 0 1 -4 -4z' /> <path d='M9 12a3 3 0 1 0 6 0a3 3 0 0 0 -6 0' /> <path d='M16.5 7.5v.01' />",
    "brand-linkedin": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M8 11v5' /> <path d='M8 8v.01' /> <path d='M12 16v-5' /> <path d='M16 16v-3a2 2 0 1 0 -4 0' /> <path d='M3 7a4 4 0 0 1 4 -4h10a4 4 0 0 1 4 4v10a4 4 0 0 1 -4 4h-10a4 4 0 0 1 -4 -4z' />",
    "brand-telegram": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M15 10l-4 4l6 6l4 -16l-18 7l4 2l2 6l3 -4' />",
    "brand-x": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 4l11.733 16h4.267l-11.733 -16z' /> <path d='M4 20l6.768 -6.768m2.46 -2.46l6.772 -6.772' />",
    "brand-youtube": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M2 8a4 4 0 0 1 4 -4h12a4 4 0 0 1 4 4v8a4 4 0 0 1 -4 4h-12a4 4 0 0 1 -4 -4v-8z' /> <path d='M10 9l5 3l-5 3z' />",
    "circle-dot": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' /> <path d='M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0' />",
    "user-plus": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0' /> <path d='M16 19h6' /> <path d='M19 16v6' /> <path d='M6 21v-2a4 4 0 0 1 4 -4h4' />",
    "copy": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z' /> <path d='M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2' />",
    "player-pause": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M6 5m0 1a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v12a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z' /> <path d='M14 5m0 1a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v12a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z' />",
    "shield-check": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M11.46 20.846a12 12 0 0 1 -7.96 -14.846a12 12 0 0 0 8.5 -3a12 12 0 0 0 8.5 3a12 12 0 0 1 -.09 7.06' /> <path d='M15 19l2 2l4 -4' />",
    "rocket": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M4 13a8 8 0 0 1 7 7a6 6 0 0 0 3 -5a9 9 0 0 0 6 -8a3 3 0 0 0 -3 -3a9 9 0 0 0 -8 6a6 6 0 0 0 -5 3' /> <path d='M7 14a6 6 0 0 0 -3 6a6 6 0 0 0 6 -3' /> <path d='M15 9m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0' />",
    "megaphone": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M18 8a3 3 0 0 1 0 6' /> <path d='M10 8v11a1 1 0 0 1 -1 1h-1a1 1 0 0 1 -1 -1v-5' /> <path d='M12 8h0l4.524 -3.77a.9 .9 0 0 1 1.476 .692v12.156a.9 .9 0 0 1 -1.476 .692l-4.524 -3.77h-8a1 1 0 0 1 -1 -1v-4a1 1 0 0 1 1 -1h8' />",
    "trending-up-2": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 17l6 -6l4 4l8 -8' /> <path d='M14 7l7 0l0 7' />",
    "trending-down": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M3 7l6 6l4 -4l8 8' /> <path d='M21 10l0 7l-7 0' />",
    "lock": "<path stroke='none' d='M0 0h24v24H0z' fill='none'/> <path d='M5 13a2 2 0 0 1 2 -2h10a2 2 0 0 1 2 2v6a2 2 0 0 1 -2 2h-10a2 2 0 0 1 -2 -2z' /> <path d='M11 16a1 1 0 1 0 2 0a1 1 0 0 0 -2 0' /> <path d='M8 11v-4a4 4 0 1 1 8 0v4' />",
}


@register.simple_tag
def icon(name, **kwargs):
    body = _ICONS.get(name)
    if body is None:
        return mark_safe(
            f'<span data-missing-icon="{name}" aria-hidden="true"></span>'
        )
    css_class = kwargs.get("class") or kwargs.get("cls") or ""
    size = int(kwargs.get("size") or 24)
    cls_attr = f' class="{css_class}"' if css_class else ""
    return mark_safe(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f"viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" "
        f"stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\""
        f'{cls_attr} aria-hidden="true">{body}</svg>'
    )
