"""Generic sidebar active-state resolver for the staff panel.

The SignalBots ``_build_admin_nav`` mixed two concerns: *assembling* the nav data
(which sections/items/URLs exist — 100% project-specific) and *computing* which
item is active for the current path (fully generic). Only the second half is
here. The host builds its own ``sections`` structure (a list of
``{"label", "items": [...]}`` where each item is either a leaf with a
``match_prefix`` or an accordion with ``children``) and calls ``resolve_nav_active``
before rendering it with the shared sidebar template.
"""
from __future__ import annotations


def resolve_nav_active(sections, current_path, force_open_labels=frozenset()):
    """Annotate ``sections`` in place with ``active`` / ``open`` / ``any_active``.

    Longest matching ``match_prefix`` wins, so a broad parent prefix does not
    stay active when the user is actually on a more specific child route.
    Returns the same ``sections`` list for convenience.
    """
    candidates: list[str] = []
    for section in sections:
        for item in section["items"]:
            if item.get("accordion"):
                candidates.extend(c["match_prefix"] for c in item["children"])
            else:
                candidates.append(item["match_prefix"])

    matching = [p for p in candidates if current_path.startswith(p)]
    active_prefix = max(matching, key=len) if matching else ""

    for section in sections:
        for item in section["items"]:
            if item.get("accordion"):
                any_active = False
                for child in item["children"]:
                    child["active"] = child["match_prefix"] == active_prefix
                    any_active = any_active or child["active"]
                item["any_active"] = any_active
                item["open"] = any_active or item["label"] in force_open_labels
            else:
                item["active"] = item["match_prefix"] == active_prefix

    return sections
