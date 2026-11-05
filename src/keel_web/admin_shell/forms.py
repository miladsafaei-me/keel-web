"""Panel form styling: every widget of a ``PanelFormMixin`` form gets the shell's input look.

The classes are TailAdmin's input recipe. A host that builds its own Tailwind bundle
scans this file (``@source``), so the classes are compiled in wherever they are used.
"""
from __future__ import annotations

from django import forms

INPUT = ("panel-input h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 "
         "shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:ring-3 focus:ring-brand-500/10 "
         "focus:outline-hidden dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30")
TEXTAREA = INPUT.replace("h-11 ", "min-h-24 ")
SELECT = INPUT + " appearance-auto pr-8"
CHECK = "panel-check h-5 w-5 rounded border-gray-300 text-brand-500 focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900"
MULTI = "panel-multi grid gap-2 text-sm text-gray-700 dark:text-gray-300"


def style_widget(widget) -> None:
    if isinstance(widget, (forms.CheckboxInput,)):
        css = CHECK
    elif isinstance(widget, (forms.CheckboxSelectMultiple, forms.RadioSelect)):
        css = MULTI
    elif isinstance(widget, forms.Textarea):
        css = TEXTAREA
        widget.attrs.setdefault("rows", 3)
    elif isinstance(widget, forms.Select):
        css = SELECT
    elif isinstance(widget, (forms.ClearableFileInput, forms.FileInput)):
        css = "panel-file text-sm text-gray-700 dark:text-gray-300"
    else:
        css = INPUT
    widget.attrs["class"] = (css + " " + widget.attrs.get("class", "")).strip()
    if css in (INPUT, TEXTAREA):
        widget.attrs.setdefault("dir", "auto")  # a Persian or Arabic translation types right to left


class PanelFormMixin:
    """Mix into a ``Form`` or ``ModelForm`` so its fields render in the panel look."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            style_widget(field.widget)
