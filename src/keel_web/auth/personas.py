"""
Persona avatar configuration.

Layer SVGs are vendored at static/keel_web_client/img/personas/<Folder>/<file>.svg.
Each user's selection is stored as JSON in User.avatar_config with the eight
keys below. ``PERSONA_PRESETS`` defines the ready-made personas shown in the
"Presets" tab; ``PERSONA_CHOICES`` is the catalogue used by the live customizer.
"""
from __future__ import annotations


# Catalogue of every available SVG per layer (filenames, no folder prefix).
# These must match the files present under static/keel_web_client/img/personas/.
PERSONA_CHOICES: dict[str, list[str]] = {
    "bg": [
        "blue.svg", "dark.svg", "green.svg", "grey.svg", "pink.svg",
        "purple.svg", "red.svg", "teal.svg", "white.svg", "yellow.svg",
    ],
    "body": [
        "oval.svg", "round.svg", "square.svg", "small.svg", "checkered.svg",
    ],
    "skin": [
        "head-skin1.svg", "head-skin2.svg", "head-skin3.svg",
        "head-skin4.svg", "head-skin5.svg", "head-skin6.svg",
    ],
    "hair": [
        "bald.svg", "balding.svg", "beanie.svg", "bigcurls.svg",
        "bobbangs.svg", "bobcut.svg", "buncurls-black.svg", "bunundercut.svg",
        "buzz.svg", "buzzcut.svg", "curlybun.svg", "curlyhightop.svg",
        "extralong.svg", "fade.svg", "hat.svg", "hightopcurly-black.svg",
        "long.svg", "mohawk.svg", "pigtails.svg", "shortcombover.svg",
        "shortcomboverchops.svg", "sidebuzz.svg", "straightbun.svg",
    ],
    "eyes": [
        "open.svg", "happy.svg", "wink.svg", "sleepy.svg",
        "glasses.svg", "sunglasses.svg",
    ],
    "mouth": [
        "smile.svg", "bigsmile.svg", "smirk.svg", "lips.svg",
        "frown.svg", "pacifier.svg",
    ],
    "nose": [
        "smallround.svg", "mediumround.svg", "wrinkles.svg",
    ],
    "facialHair": [
        "",  # No facial hair (sentinel)
        "shadow.svg", "soulpatch.svg", "goatee.svg", "walrus.svg",
        "mustache-black.svg", "mustache-brunette.svg", "mustache-copper.svg",
        "mustache-grey.svg", "mustache-blonde.svg",
        "beardmustache-black.svg", "beardmustache-brunette.svg",
        "beardmustache-copper.svg", "beardmustache-grey.svg",
        "beardmustache-blonde.svg", "beardmustache-red.svg",
        "beardmustache-pink.svg", "beardmustache-teal.svg",
    ],
}


PERSONA_LAYER_ORDER = ("bg", "body", "skin", "hair", "facialHair", "mouth", "nose", "eyes")


# Hand-picked diverse personas surfaced in the "Presets" grid.
PERSONA_PRESETS: list[dict[str, str]] = [
    {
        "key": "alex",
        "bg": "blue.svg", "body": "round.svg", "skin": "head-skin2.svg",
        "hair": "long.svg", "eyes": "happy.svg", "mouth": "smile.svg",
        "nose": "smallround.svg", "facialHair": "",
    },
    {
        "key": "kai",
        "bg": "purple.svg", "body": "oval.svg", "skin": "head-skin5.svg",
        "hair": "buzz.svg", "eyes": "sunglasses.svg", "mouth": "smirk.svg",
        "nose": "mediumround.svg", "facialHair": "beardmustache-black.svg",
    },
    {
        "key": "mia",
        "bg": "pink.svg", "body": "round.svg", "skin": "head-skin1.svg",
        "hair": "curlybun.svg", "eyes": "happy.svg", "mouth": "bigsmile.svg",
        "nose": "smallround.svg", "facialHair": "",
    },
    {
        "key": "sam",
        "bg": "green.svg", "body": "square.svg", "skin": "head-skin4.svg",
        "hair": "shortcombover.svg", "eyes": "glasses.svg", "mouth": "smile.svg",
        "nose": "mediumround.svg", "facialHair": "shadow.svg",
    },
    {
        "key": "rae",
        "bg": "yellow.svg", "body": "oval.svg", "skin": "head-skin3.svg",
        "hair": "pigtails.svg", "eyes": "wink.svg", "mouth": "smirk.svg",
        "nose": "smallround.svg", "facialHair": "",
    },
    {
        "key": "leo",
        "bg": "teal.svg", "body": "round.svg", "skin": "head-skin6.svg",
        "hair": "fade.svg", "eyes": "open.svg", "mouth": "smile.svg",
        "nose": "mediumround.svg", "facialHair": "goatee.svg",
    },
    {
        "key": "noa",
        "bg": "red.svg", "body": "small.svg", "skin": "head-skin2.svg",
        "hair": "bobbangs.svg", "eyes": "sleepy.svg", "mouth": "lips.svg",
        "nose": "smallround.svg", "facialHair": "",
    },
    {
        "key": "rex",
        "bg": "dark.svg", "body": "square.svg", "skin": "head-skin5.svg",
        "hair": "mohawk.svg", "eyes": "open.svg", "mouth": "smirk.svg",
        "nose": "wrinkles.svg", "facialHair": "walrus.svg",
    },
]


def preset_config(key: str) -> dict[str, str] | None:
    for p in PERSONA_PRESETS:
        if p["key"] == key:
            return {k: v for k, v in p.items() if k != "key"}
    return None


def is_valid_config(cfg: dict) -> bool:
    """Validates that every layer value (when set) exists in PERSONA_CHOICES."""
    if not isinstance(cfg, dict):
        return False
    for key in PERSONA_LAYER_ORDER:
        value = cfg.get(key, "")
        if value and value not in PERSONA_CHOICES.get(key, []):
            return False
    # Required layers (everything except facialHair must have a value)
    required = ("bg", "body", "skin", "hair", "eyes", "mouth", "nose")
    return all(cfg.get(k) for k in required)
