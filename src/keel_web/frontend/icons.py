"""A Font Awesome subset holding only the icons a site's own source names.

Stock Font Awesome 6 ships about 2,450 icons: a 100 KB stylesheet whose rules are
nearly all for icons a page never draws, and three webfonts of 150, 110 and 25 KB with
``font-display: block``. Lighthouse reports all three costs at once ("Reduce unused CSS",
"Font display", and the fonts in "Improve image delivery"'s neighbour, the network tree).

``build()`` scans the host's source for every ``fa-<name>`` token, then writes into
``<output_dir>/<bundle_dir>/icons/``:

* ``fa-subset.css`` -- the stock stylesheet with every rule that names an unused
  ``fa-*`` class removed (icon glyph rules, sizes, animations and their keyframes), and
  its ``@font-face`` rules cut to the Font Awesome 6 families actually used, pointed at
  the subset files, with ``font-display: swap``;
* ``<family>.subset.woff2`` -- each family's font cut to the glyphs used, typically a
  few kilobytes.

**What it cannot see.** An icon class assembled at runtime from pieces, or one stored
in database content, never appears as a token and will render as nothing. Keep icon
names literal in templates, Python and JavaScript; the scan covers all three.

Subsetting needs ``fonttools`` with WOFF2 support (the ``frontend`` extra). The
stylesheet half is pure text and is what the tests exercise.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

TOKEN_RE = re.compile(r"\bfa-[a-z0-9]+(?:-[a-z0-9]+)*\b")
SCAN_EXTS = (".html", ".txt", ".py", ".js", ".css", ".json", ".md")
DEFAULT_SKIP = (
    ".git", "__pycache__", "node_modules", "staticfiles", "media", "var", ".venv",
    "font-awesome", "keel_frontend",
)
# Rules on these classes carry the family, weight and display every icon needs.
CORE_CLASSES = frozenset({
    "fa", "fas", "far", "fab", "fa-solid", "fa-regular", "fa-brands", "fa-classic", "fa-sharp",
})
FAMILY_FILES = {
    "fa-solid-900": "Font Awesome 6 Free",
    "fa-regular-400": "Font Awesome 6 Free",
    "fa-brands-400": "Font Awesome 6 Brands",
}
SUBSET_DIR = "icons"
SUBSET_CSS = "fa-subset.css"

_ICON_RULE_RE = re.compile(r'((?:\.fa-[a-z0-9-]+:+before,?)+)\{content:"\\([0-9a-f]+)"\}')
_CLASS_RE = re.compile(r"\.(fa[a-z0-9-]*)")


def scan_tokens(roots, skip=DEFAULT_SKIP) -> set[str]:
    tokens: set[str] = set()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
            for filename in filenames:
                if not filename.endswith(SCAN_EXTS):
                    continue
                try:
                    text = Path(dirpath, filename).read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if "fa-" in text:
                    tokens.update(TOKEN_RE.findall(text))
    return tokens


def icon_codepoints(css: str) -> dict[str, int]:
    table: dict[str, int] = {}
    for selector, code in _ICON_RULE_RE.findall(css):
        for name in re.findall(r"\.(fa-[a-z0-9-]+):+before", selector):
            table[name] = int(code, 16)
    return table


def _top_level_rules(css: str):
    """Yield ``(prelude, body)`` for each top-level rule of a (minified) stylesheet."""
    i, n = 0, len(css)
    while i < n:
        if css.startswith("/*", i):
            end = css.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        brace = css.find("{", i)
        if brace < 0:
            break
        depth, j = 1, brace + 1
        while j < n and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        yield css[i:brace].strip(), css[brace + 1:j - 1]
        i = j


def _selector_kept(selector: str, used: set[str]) -> bool:
    classes = [c for c in _CLASS_RE.findall(selector) if c.startswith("fa")]
    return all(c in used or c in CORE_CLASSES for c in classes)


def prune_css(css: str, used: set[str], families: dict[str, str]) -> str:
    """Keep only what the used icons need; ``families`` maps a font stem to its subset file."""
    out = []
    for prelude, body in _top_level_rules(css):
        if prelude.startswith("@font-face"):
            stem = next((s for s in FAMILY_FILES if f"{s}." in body), None)
            if stem not in families or f'"{FAMILY_FILES[stem]}"' not in body:
                continue
            body = re.sub(r"src:[^;}]*", f'src:url({families[stem]}) format("woff2")', body)
            body = re.sub(r"font-display:[a-z]+", "font-display:swap", body)
            out.append(f"@font-face{{{body}}}")
        elif prelude.startswith("@keyframes"):
            if prelude.split()[-1] in used:
                out.append(f"{prelude}{{{body}}}")
        elif prelude.startswith("@"):
            inner = prune_css(body, used, families)
            if inner:
                out.append(f"{prelude}{{{inner}}}")
        else:
            kept = [s for s in prelude.split(",") if s.strip() and _selector_kept(s, used)]
            if kept:
                out.append(f"{','.join(kept)}{{{body}}}")
    return "".join(out)


def _font_source(webfonts: Path, stem: str) -> Path:
    # fontTools cannot decompile every stock woff2 (fa-regular-400 fails on its glyf
    # table); the shipped .ttf carries identical outlines.
    ttf = webfonts / f"{stem}.ttf"
    return ttf if ttf.exists() else webfonts / f"{stem}.woff2"


def build(stock_css: Path, out_dir: Path, tokens: set[str]) -> dict:
    from fontTools import subset
    from fontTools.ttLib import TTFont

    css = stock_css.read_text(encoding="utf-8")
    table = icon_codepoints(css)
    used_icons = {name: cp for name, cp in table.items() if name in tokens}
    if not used_icons:
        raise ValueError("no Font Awesome icon names found in the scanned source")
    webfonts = stock_css.parent.parent / "webfonts"
    target = out_dir / SUBSET_DIR
    target.mkdir(parents=True, exist_ok=True)

    families, report = {}, {"icons": len(used_icons), "fonts": {}}
    wanted = set(used_icons.values())
    for stem in FAMILY_FILES:
        source = _font_source(webfonts, stem)
        if not source.exists():
            continue
        font = TTFont(source)
        carried = wanted & set(font.getBestCmap())
        font.close()
        if not carried:
            continue
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = []
        options.name_IDs = []
        options.notdef_outline = True
        subsetter_font = subset.load_font(str(source), options)
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(unicodes=carried)
        subsetter.subset(subsetter_font)
        filename = f"{stem}.subset.woff2"
        subset.save_font(subsetter_font, str(target / filename), options)
        subsetter_font.close()
        families[stem] = filename
        report["fonts"][stem] = (len(carried), (target / filename).stat().st_size)

    pruned = prune_css(css, set(tokens), families)
    (target / SUBSET_CSS).write_text(pruned, encoding="utf-8")
    report["css_bytes"] = len(pruned.encode("utf-8"))
    return report
