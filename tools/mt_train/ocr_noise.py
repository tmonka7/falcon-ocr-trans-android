"""Source-side noise that imitates what the app's OCR stage feeds the translator.

The translator never sees clean text on the phone. It sees PP-OCR output, which
has recognition errors (look-alike characters), lost or extra spaces, text set
in capitals on signs, and paragraphs reassembled from wrapped lines. A model
fine-tuned only on clean parallel text is brittle against all of these, so the
training loop can apply this module to the *source* side of a fraction of
examples. The target side is never touched: the model learns to produce the
clean translation from noisy input.

One effect is specific to this app: ``Paragraph.buildSourceText`` joins wrapped
lines without a space when both neighbouring characters are CJK, and Hangul
counts as CJK there. A Korean sentence that wraps between two words therefore
reaches the translator with those words fused. ``fuse_spaces`` reproduces that.

Everything is driven by an explicit ``random.Random`` so augmentation is
reproducible per seed.
"""
from __future__ import annotations

import random

# --------------------------------------------------------------------- Latin

# Look-alike substitutions typical of OCR on printed Latin text.
_LATIN_CONFUSIONS = [
    ("rn", "m"), ("m", "rn"), ("cl", "d"), ("d", "cl"), ("vv", "w"),
    ("l", "1"), ("1", "l"), ("I", "l"), ("l", "I"), ("O", "0"), ("0", "O"),
    ("S", "5"), ("5", "S"), ("B", "8"), ("e", "c"), ("c", "e"), ("h", "b"),
    ("i", "l"), ("t", "f"), (",", "."), (".", ","),
]

# ------------------------------------------------------------------- Hangul

_S_BASE, _L_COUNT, _V_COUNT, _T_COUNT = 0xAC00, 19, 21, 28

# Indices into the initial (L), medial (V) and final (T) jamo tables.
# Groups of shapes PP-OCR's Korean head is known to confuse on small or blurred
# print: vowels differing by one short stroke, and aspirated/plain consonants.
_V_GROUPS = [(0, 2), (4, 6), (8, 12), (13, 17), (1, 5), (3, 7), (18, 20)]   # ㅏㅑ ㅓㅕ ㅗㅛ ㅜㅠ ㅐㅔ ㅒㅖ ㅡㅣ
_L_GROUPS = [(0, 15), (3, 16), (7, 17), (12, 14), (11, 18)]                  # ㄱㅋ ㄷㅌ ㅂㅍ ㅈㅊ ㅇㅎ
_T_DROPPABLE = {4, 8, 16, 21}                                                # ㄴ ㄹ ㅁ ㅇ finals


def _decompose(ch: str) -> tuple[int, int, int] | None:
    cp = ord(ch) - _S_BASE
    if not 0 <= cp < _L_COUNT * _V_COUNT * _T_COUNT:
        return None
    return cp // (_V_COUNT * _T_COUNT), (cp % (_V_COUNT * _T_COUNT)) // _T_COUNT, cp % _T_COUNT


def _compose(l: int, v: int, t: int) -> str:
    return chr(_S_BASE + (l * _V_COUNT + v) * _T_COUNT + t)


def _swap_in_groups(index: int, groups: list[tuple[int, int]]) -> int | None:
    for a, b in groups:
        if index == a:
            return b
        if index == b:
            return a
    return None


def hangul_confusion(text: str, rng: random.Random) -> str:
    """Replaces one Hangul syllable with a visually similar one."""
    positions = [i for i, ch in enumerate(text) if _decompose(ch)]
    if not positions:
        return text
    i = rng.choice(positions)
    l, v, t = _decompose(text[i])
    choice = rng.random()
    if choice < 0.5:
        nv = _swap_in_groups(v, _V_GROUPS)
        if nv is not None:
            v = nv
    elif choice < 0.8:
        nl = _swap_in_groups(l, _L_GROUPS)
        if nl is not None:
            l = nl
    elif t in _T_DROPPABLE:
        t = 0
    return text[:i] + _compose(l, v, t) + text[i + 1:]


# ------------------------------------------------------------------ generic

def latin_confusion(text: str, rng: random.Random) -> str:
    """Applies one look-alike substitution at a random matching position."""
    options = [(src, dst) for src, dst in _LATIN_CONFUSIONS if src in text]
    if not options:
        return text
    src, dst = rng.choice(options)
    starts = [i for i in range(len(text)) if text.startswith(src, i)]
    i = rng.choice(starts)
    return text[:i] + dst + text[i + len(src):]


def fuse_spaces(text: str, rng: random.Random, rate: float = 0.15) -> str:
    """Deletes some spaces, as when wrapped lines are rejoined without one."""
    out = []
    removed = False
    for ch in text:
        if ch == " " and rng.random() < rate:
            removed = True
            continue
        out.append(ch)
    if not removed and " " in text:
        spaces = [i for i, ch in enumerate(text) if ch == " "]
        i = rng.choice(spaces)
        return text[:i] + text[i + 1:]
    return "".join(out)


def split_word(text: str, rng: random.Random) -> str:
    """Inserts a spurious space inside a word (a broken glyph gap)."""
    candidates = [i for i in range(1, len(text)) if text[i - 1].isalnum() and text[i].isalnum()]
    if not candidates:
        return text
    i = rng.choice(candidates)
    return text[:i] + " " + text[i:]


def hyphen_break(text: str, rng: random.Random) -> str:
    """Leaves an end-of-line hyphenation artefact inside a long word: 'transla- tion'."""
    words = [(m, w) for m, w in enumerate(text.split(" ")) if len(w) >= 8 and w.isalpha()]
    if not words:
        return text
    idx, word = rng.choice(words)
    cut = rng.randint(3, len(word) - 3)
    parts = text.split(" ")
    parts[idx] = word[:cut] + "- " + word[cut:]
    return " ".join(parts)


def drop_final_punct(text: str, rng: random.Random) -> str:
    return text[:-1] if text and text[-1] in ".!?。" else text


def upper_case(text: str, rng: random.Random) -> str:
    """Signage and headings are often set in capitals."""
    return text.upper()


_EN_OPS = [(latin_confusion, 0.45), (fuse_spaces, 0.15), (split_word, 0.1),
           (hyphen_break, 0.1), (drop_final_punct, 0.1), (upper_case, 0.1)]
_KO_OPS = [(hangul_confusion, 0.4), (fuse_spaces, 0.35), (latin_confusion, 0.05),
           (split_word, 0.1), (drop_final_punct, 0.1)]


def add_noise(text: str, lang: str, rng: random.Random, max_ops: int = 2) -> str:
    """Applies between one and ``max_ops`` noise operations for ``lang`` ('en' or 'ko')."""
    ops = _EN_OPS if lang == "en" else _KO_OPS
    funcs = [f for f, _ in ops]
    weights = [w for _, w in ops]
    n = rng.randint(1, max_ops)
    for f in rng.choices(funcs, weights=weights, k=n):
        text = f(text, rng)
    return text


class SourceNoiser:
    """Callable used by the training loop: noises a fraction ``prob`` of sources."""

    def __init__(self, lang: str, prob: float, seed: int = 0):
        self.lang = lang
        self.prob = prob
        self.rng = random.Random(seed)

    def __call__(self, text: str) -> str:
        if self.prob <= 0 or self.rng.random() >= self.prob:
            return text
        return add_noise(text, self.lang, self.rng)
