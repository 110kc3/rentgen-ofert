"""Shared address normalization and contradictions in photo-based identity.

Compatibility is a veto, never positive identity evidence. Missing attributes
are unknown; normalized but different known towns, streets, rooms or floors
must not be overruled by a reused photo. Exact portal IDs are handled by callers.
"""
from __future__ import annotations

import re
import unicodedata


def fold(s):
    """lowercase, strip diacritics (incl. ł) and punctuation, collapse spaces —
    'Bielsko - Biała' and 'Bielsko-Biała' must fold to the same key."""
    if not s:
        return ""
    s = s.replace("ł", "l").replace("Ł", "L")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())


_STREET_NOISE = {"ul", "ulica", "al", "aleja", "pl", "plac", "os", "osiedle", "gen",
                 "sw", "ks", "dr", "prof", "mjr", "kpt", "im"}


def _street_tokens(s):
    return [t for t in fold(s).split() if t not in _STREET_NOISE and not t.isdigit()]


# folded (ASCII) declension endings a street-name token may gain/swap; a suffix
# outside this set means a DIFFERENT word ('gorna' vs 'gornika'), not a case form
_DECL_SUFFIX = {"", "a", "e", "i", "y", "ej", "iej", "ego", "iego",
                "emu", "iemu", "ym", "im", "ymi", "imi", "ach", "iach"}


def _tok_eq(a, b):
    """Token equality tolerant of Polish declension: 'gdanska' == 'gdanskiej',
    'polna' == 'polnej', but 'kwiatowa' != 'kwiatkowskiego' and
    'gorna' != 'gornika' (an agent noun, not a case of 'gorna')."""
    if a == b:
        return True
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    common = 0
    for x, y in zip(short, long_):
        if x != y:
            break
        common += 1
    return (common >= 4 and common >= len(short) - 1
            and long_[common:] in _DECL_SUFFIX)


def street_match(a, b):
    """True when two street names plausibly refer to the same street.

    Compares the significant last token (surname) with declension tolerance
    and requires any remaining tokens of the shorter name to appear in the
    longer one, so 'Asnyka' == 'Adama Asnyka', 'ul. Gdanskiej' == 'Gdanska',
    but 'Polna' != 'Lipowa'.
    """
    ta, tb = _street_tokens(a), _street_tokens(b)
    if not ta or not tb:
        return False
    if not _tok_eq(ta[-1], tb[-1]):
        return False
    small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return all(any(_tok_eq(t, u) for u in big) for t in small[:-1])


def _known_int(value):
    text = str(value).strip() if value is not None else ""
    return int(text) if re.fullmatch(r"-?\d+", text) else None


def known_floor(value):
    word = fold(value) if isinstance(value, str) else ""
    if word in ("parter", "ground floor"):
        return 0
    if word == "suterena":
        return -1
    # Ranges such as "> 10" and attic labels do not identify an exact floor.
    return _known_int(value)


def compatible(a, b):
    for field in ("type", "locality"):
        left, right = fold(a.get(field)), fold(b.get(field))
        if left and right and left != right:
            return False
    left, right = a.get("street"), b.get("street")
    if left and right and not street_match(left, right):
        return False
    if a.get("type") == "flat" or b.get("type") == "flat":
        for field, parse in (("rooms", _known_int), ("floor", known_floor)):
            left, right = parse(a.get(field)), parse(b.get(field))
            if left is not None and right is not None and left != right:
                return False
    return True
