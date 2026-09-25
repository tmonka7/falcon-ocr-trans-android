"""Unit tests for the data filters and the OCR-noise augmentation.

    python -m pytest tools/mt_train/tests -q
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ocr_noise  # noqa: E402
from textnorm import FilterConfig, check_pair, dedup_key, normalize, profile, strip_artifacts  # noqa: E402

CFG = FilterConfig()


# ------------------------------------------------------------------ normalise

def test_normalize_nfkc_and_whitespace():
    # Full-width Latin and an ideographic space fold to ASCII, as SpmEncoder does.
    assert normalize("Ｈｅｌｌｏ　 world ") == "Hello world"


def test_normalize_strips_zero_width_and_controls():
    assert normalize("a​b\u0007c﻿") == "abc"


def test_profile_counts_scripts():
    p = profile("한국어 abc 123")
    assert p.hangul == 3 and p.latin == 3 and p.digits_punct == 3


# -------------------------------------------------------------------- filters

def test_good_pair_passes():
    assert check_pair("The next stop is City Hall.", "다음 역은 시청입니다.", CFG) is None


def test_short_label_pair_passes_despite_ratio():
    assert check_pair("Exit", "출구", CFG) is None


def test_identical_rejected():
    assert check_pair("iPhone", "iPhone", CFG) == "identical"


def test_korean_side_without_hangul_rejected():
    assert check_pair("Good morning everyone.", "Good morning everyone!", CFG) == "ko_script"


def test_hangul_on_english_side_rejected():
    assert check_pair("다음 역은 시청입니다 next stop", "다음 역은 시청입니다.", CFG) == "en_script"


def test_ratio_rejects_misalignment():
    en = "This is a very long English sentence that clearly does not match the short Korean side at all."
    assert check_pair(en, "안녕하세요 여러분 반갑", CFG) == "ratio"


def test_numbers_only_rejected():
    assert check_pair("12,345.67 - 89", "12,345.67 - 89원", CFG) in ("not_text", "ko_script")


def test_urls_rejected():
    assert check_pair("See https://example.com/page", "https://example.com/page 참조", CFG) == "url"


def test_copied_product_names_do_not_fail_script_check():
    assert check_pair("Please enable Konqueror's Adblock", "Konqueror의 Adblock을 켜십시오", CFG) is None


def test_untranslated_copy_still_fails():
    assert check_pair("Adblock settings", "Adblock settings!", CFG) == "ko_script"


def test_glued_desktop_keys_are_stripped():
    assert strip_artifacts("파일 크기 뷰어Comment") == "파일 크기 뷰어"
    assert strip_artifacts("번역Name") == "번역"
    assert strip_artifacts("User Name") == "User Name"      # not glued to Hangul: untouched


def test_docbook_entities_rejected():
    assert check_pair("An Introduction to & kde;", "& kde; 소개", CFG) == "markup"


def test_dedup_key_ignores_case_and_punctuation():
    assert dedup_key("Hello, World!", "안녕, 세상!") == dedup_key("hello world", "안녕 세상")


# ---------------------------------------------------------------------- noise

def _is_syllable(ch: str) -> bool:
    return 0xAC00 <= ord(ch) <= 0xD7A3


def test_hangul_confusion_yields_valid_syllables():
    rng = random.Random(0)
    for _ in range(300):
        out = ocr_noise.hangul_confusion("다음 역은 시청입니다", rng)
        assert all(_is_syllable(c) or c == " " for c in out)
        assert len(out) == len("다음 역은 시청입니다")


def test_hangul_decompose_compose_roundtrip():
    for ch in "가힣한국어읽":
        l, v, t = ocr_noise._decompose(ch)
        assert ocr_noise._compose(l, v, t) == ch


def test_fuse_spaces_always_removes_at_least_one():
    rng = random.Random(1)
    for _ in range(50):
        assert ocr_noise.fuse_spaces("a b c d", rng, rate=0.0).count(" ") == 2


def test_hyphen_break_inserts_hyphen_and_space():
    out = ocr_noise.hyphen_break("please translation now", random.Random(3))
    assert "- " in out and out.replace("- ", "") == "please translation now"


def test_noise_is_reproducible_per_seed():
    a = [ocr_noise.add_noise("Keep refrigerated after opening.", "en", random.Random(9)) for _ in range(3)]
    b = [ocr_noise.add_noise("Keep refrigerated after opening.", "en", random.Random(9)) for _ in range(3)]
    assert a == b


def test_noiser_probability_zero_is_identity():
    n = ocr_noise.SourceNoiser("ko", 0.0)
    assert n("냉장 보관하세요.") == "냉장 보관하세요."


def test_noiser_changes_roughly_prob_fraction():
    n = ocr_noise.SourceNoiser("en", 0.3, seed=5)
    text = "Please turn off your mobile phone during the performance."
    changed = sum(n(text) != text for _ in range(2000))
    assert 450 < changed < 750   # ~600 expected; a few ops can be no-ops


def test_citation_boilerplate_rejected():
    assert check_pair("Retrieved 2018-11-27. ↑ See it at the channel.",
                      "2018년 11월 27일에 확인함. ↑ 채널 참조", CFG) == "boilerplate"
