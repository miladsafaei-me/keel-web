"""Client-panel sidebar navigation: the dataclasses + a resolver.

The ``NavItem`` / ``NavSection`` dataclasses are generic. The *instance* of the
nav (which sections and product routes a given site has) is project-specific, so
the package ships an empty ``CLIENT_NAV`` and the host supplies its own via
``KEEL_WEB["client_nav"]`` (a dotted path to a NavSection tuple, or a callable
returning one).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from django.utils.module_loading import import_string

from ..config import web_setting


@dataclass(frozen=True)
class NavItem:
    label: str
    url_name: str
    icon: str  # Key into the keel_icons {% icon %} set (e.g. "dashboard")
    match_prefix: str  # path prefix used to compute is-active in templates
    exact: bool = False  # When True, only highlight when current path equals match_prefix


@dataclass(frozen=True)
class NavSection:
    label: str
    items: tuple[NavItem, ...] = field(default_factory=tuple)


# Empty by default — the host supplies its own product nav through
# KEEL_WEB["client_nav"]. Kept as a named symbol so a host can import and extend it.
CLIENT_NAV: tuple[NavSection, ...] = ()


def resolve_client_nav() -> tuple[NavSection, ...]:
    """Return the host's configured nav, or the empty default."""
    dotted = web_setting("client_nav")
    if not dotted:
        return CLIENT_NAV
    obj = import_string(dotted)
    return obj() if callable(obj) else obj
