"""Normalisation and filtering for English-Korean sentence pairs.

Normalisation mirrors what the app does before tokenising (``SpmEncoder``
applies NFKC and collapses whitespace), so the model is trained on text in the
same form it will see on the phone.

The filters are deliberately simple, cheap and explainable. Web-mined corpora
(WikiMatrix, CCMatrix, ParaCrawl) contain a steady fraction of misaligned or
wrong-language pairs, and a handful of rules removes most of them:

* both sides non-empty after normalisation, and not identical;
* length within bounds on both sides;
* character-length ratio within bounds (Korean is denser than English, so the
  expected English/Korean ratio is roughly 1.5-3.5);
* the Korean side is mostly Hangul, the English side mostly Latin and free of
  Hangul;
* no side is mostly digits/punctuation (tables of numbers, URLs, markup).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_WS = re.compile(r"\s+")
_URLISH = re.compile(r"https?://|www\.|\.(com|org|net|kr)/", re.IGNORECASE)
_CONTROL = re.compile(r"[\u0000-\u0008\u000B-\u001F\u007F​-‏  ﻿]")
# KDE4 (and some other localisation dumps) glue desktop-file keys onto the end
# of a translation: "번역Comment", "파일 크기 뷰어Name".
_GLUED_KEY = re.compile(r"(?<=[가-힣)\].!?])(Comment|GenericName|Name|Keywords)$")
# DocBook/XML entities such as "&kde;" or "& kde;".
_ENTITY = re.compile(r"&\s?[A-Za-z][\w.-]*;")
_LATIN_WORD = re.compile(r"[A-Za-z]+")
# Reference-list debris from wiki dumps: "Retrieved 2018-11-27. ↑ See ...".
_BOILERPLATE = re.compile(r"↑|\bRetrieved\s+\d|\bArchived from the original\b|\bISBN\b|확인함\.")


def normalize(text: str) -> str:
    """NFKC, strip control/zero-width characters, collapse whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL.sub("", text)
    return _WS.sub(" ", text).strip()


def strip_artifacts(text: str) -> str:
    """Removes corpus-specific debris that normalisation cannot know about."""
    return _GLUED_KEY.sub("", text)


def is_hangul(ch: str) -> bool:
    cp = ord(ch)
    return (0xAC00 <= cp <= 0xD7A3      # syllables
            or 0x1100 <= cp <= 0x11FF   # jamo
            or 0x3130 <= cp <= 0x318F)  # compatibility jamo


def is_latin_letter(ch: str) -> bool:
    return ch.isascii() and ch.isalpha()


@dataclass
class ScriptProfile:
    letters: int
    hangul: int
    latin: int
    han: int
    other_letters: int
    digits_punct: int
    length: int

    @property
    def hangul_share(self) -> float:
        return self.hangul / self.letters if self.letters else 0.0

    @property
    def latin_share(self) -> float:
        return self.latin / self.letters if self.letters else 0.0

    @property
    def letter_share(self) -> float:
        return self.letters / self.length if self.length else 0.0


def profile(text: str) -> ScriptProfile:
    letters = hangul = latin = han = other = dp = 0
    nonspace = 0
    for ch in text:
        if ch.isspace():
            continue
        nonspace += 1
        if is_hangul(ch):
            hangul += 1
            letters += 1
        elif is_latin_letter(ch):
            latin += 1
            letters += 1
        elif "一" <= ch <= "鿿":
            han += 1
            letters += 1
        elif ch.isalpha():
            other += 1
            letters += 1
        else:
            dp += 1
    return ScriptProfile(letters, hangul, latin, han, other, dp, nonspace)


@dataclass(frozen=True)
class FilterConfig:
    min_chars: int = 1
    max_chars_en: int = 400
    max_chars_ko: int = 250
    # English chars per Korean char. Short strings (labels, titles) vary a lot,
    # so the ratio is only enforced once both sides are this long.
    ratio_min: float = 0.7
    ratio_max: float = 6.0
    ratio_min_len: int = 12
    min_hangul_share: float = 0.5
    min_latin_share_en: float = 0.7
    min_letter_share: float = 0.3
    drop_urls: bool = True


# Reason codes, counted in the preparation report.
REASONS = ("empty", "identical", "too_long", "ratio", "ko_script", "en_script",
           "not_text", "url", "markup", "boilerplate")


def check_pair(en: str, ko: str, cfg: FilterConfig) -> str | None:
    """Returns ``None`` if the (already normalised) pair passes, else a reason code."""
    if len(en) < cfg.min_chars or len(ko) < cfg.min_chars:
        return "empty"
    if en == ko:
        return "identical"
    if len(en) > cfg.max_chars_en or len(ko) > cfg.max_chars_ko:
        return "too_long"
    if cfg.drop_urls and (_URLISH.search(en) or _URLISH.search(ko)):
        return "url"
    if _ENTITY.search(en) or _ENTITY.search(ko):
        return "markup"
    if _BOILERPLATE.search(en) or _BOILERPLATE.search(ko):
        return "boilerplate"
    if len(en) >= cfg.ratio_min_len and len(ko) >= cfg.ratio_min_len:
        ratio = len(en) / len(ko)
        if not cfg.ratio_min <= ratio <= cfg.ratio_max:
            return "ratio"
    pe, pk = profile(en), profile(ko)
    if pk.letter_share < cfg.min_letter_share or pe.letter_share < cfg.min_letter_share:
        return "not_text"
    # Latin words copied verbatim from the English side (product names, as in
    # "Konqueror의 Adblock을 켜십시오") are legitimate in Korean text, so they do
    # not count against the Hangul share. An untranslated copy still fails,
    # because it has no Hangul at all.
    en_words = {w.lower() for w in _LATIN_WORD.findall(en)}
    copied = sum(len(w) for w in _LATIN_WORD.findall(ko) if w.lower() in en_words)
    effective = pk.letters - copied
    if pk.hangul == 0 or (effective > 0 and pk.hangul / effective < cfg.min_hangul_share):
        return "ko_script"
    if pe.hangul > 0 or pe.latin_share < cfg.min_latin_share_en:
        return "en_script"
    return None


def dedup_key(en: str, ko: str) -> str:
    """Case- and punctuation-insensitive key, so trivially different copies collapse."""
    def squash(s: str) -> str:
        return re.sub(r"[\W_]+", "", s.casefold())
    return squash(en) + "\t" + squash(ko)
