"""Concrete drop-in user for fresh projects.

The reusable field set + helpers live in ``base.AbstractKeelUser`` (a module that
defines no concrete model, so hosts can subclass it without installing this app —
see ``base.py``). This module adds the one concrete ``User`` a fresh project can
adopt directly by pointing ``AUTH_USER_MODEL`` at ``keel_web_auth.User``.

``AbstractKeelUser`` is re-exported here for backward compatibility, so both
``from keel_web.auth.base import AbstractKeelUser`` (the subclass-adoption path)
and ``from keel_web.auth.models import AbstractKeelUser`` keep working.
"""
from .base import AbstractKeelUser  # noqa: F401  (re-exported)
from ..config import web_setting


class User(AbstractKeelUser):
    """Concrete drop-in user. Point ``AUTH_USER_MODEL`` at ``keel_web_auth.User``.

    The table name is a config seam: set ``KEEL_WEB["user_db_table"]`` to an
    existing table (e.g. ``"users_user"``) to adopt this model into a project
    that already has a user table, with only a metadata-level migration.
    """

    class Meta(AbstractKeelUser.Meta):
        abstract = False
        db_table = web_setting("user_db_table")
