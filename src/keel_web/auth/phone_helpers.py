"""Country list + per-region phone parsing/validation for client profile fields."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import phonenumbers
import pycountry
from django.core.exceptions import ValidationError
from phonenumbers import NumberParseException, PhoneNumberFormat
from phonenumbers.phonenumberutil import region_code_for_country_code

DEFAULT_REGION = "US"


def _flag_emoji(alpha2: str) -> str:
    if len(alpha2) != 2:
        return ""
    base = 0x1F1E6
    return "".join(chr(base + (ord(c) - ord("A"))) for c in alpha2.upper())


def _format_significant(parsed) -> str:
    """Format a PhoneNumber as international-without-country-code: dial-prefix-free, no trunk 0."""
    sig = phonenumbers.national_significant_number(parsed)
    intl = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
    parts = intl.split(" ", 1)
    if len(parts) == 2 and parts[1]:
        return parts[1]
    return sig


@lru_cache(maxsize=1)
def country_data() -> list[dict]:
    """One row per supported region: alpha2, name, dial_code, flag, sample national digits."""
    rows: list[dict] = []
    for region in phonenumbers.SUPPORTED_REGIONS:
        country = pycountry.countries.get(alpha_2=region)
        if not country:
            continue
        dial = phonenumbers.country_code_for_region(region)
        if not dial:
            continue
        sample = phonenumbers.example_number(region)
        if sample:
            sample_digits = phonenumbers.national_significant_number(sample)
            sample_national = _format_significant(sample)
        else:
            sample_digits = ""
            sample_national = ""
        rows.append({
            "alpha2": region,
            "name": country.name,
            "dial": f"+{dial}",
            "dial_code": dial,
            "flag": _flag_emoji(region),
            "sample_digits": sample_digits,
            "sample_national": sample_national,
        })
    rows.sort(key=lambda r: r["name"])
    return rows


@lru_cache(maxsize=512)
def country_meta(alpha2: str) -> Optional[dict]:
    if not alpha2:
        return None
    alpha2 = alpha2.upper()
    for row in country_data():
        if row["alpha2"] == alpha2:
            return row
    return None


def parse_e164(value: str) -> tuple[Optional[str], str]:
    """Split a stored E.164 string into (region, significant national digits without trunk prefix)."""
    if not value:
        return None, ""
    try:
        parsed = phonenumbers.parse(value, None)
    except NumberParseException:
        return None, value
    region = phonenumbers.region_code_for_number(parsed)
    if not region:
        cc = parsed.country_code
        region = region_code_for_country_code(cc) if cc else None
    return region, phonenumbers.national_significant_number(parsed)


def normalize_to_e164(region: str, national_digits: str) -> str:
    """Combine (region, national digits) into a validated E.164 string.

    Raises ValidationError on bad region, non-digits, or invalid number for the region.
    """
    if not national_digits:
        return ""
    if not region:
        raise ValidationError("Select a country before entering a phone number.")
    region = region.upper()
    if region not in phonenumbers.SUPPORTED_REGIONS:
        raise ValidationError("Unsupported country.")
    if not national_digits.isdigit():
        raise ValidationError("Enter digits only, no spaces or symbols.")
    try:
        parsed = phonenumbers.parse(national_digits, region)
    except NumberParseException:
        raise ValidationError(_format_help_text(region))
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError(_format_help_text(region))
    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


def _format_help_text(region: str) -> str:
    meta = country_meta(region)
    if not meta:
        return "Enter a valid phone number."
    if meta["sample_digits"]:
        return (
            f"Invalid number for {meta['name']}. Expected {len(meta['sample_digits'])} "
            f"digits, e.g. {meta['sample_national']}."
        )
    return f"Invalid phone number for {meta['name']}."
