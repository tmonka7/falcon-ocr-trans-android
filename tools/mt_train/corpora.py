"""Catalogue of English-Korean corpora and evaluation sets.

Training corpora come from OPUS (https://opus.nlpl.eu). Versions and download
URLs are resolved at run time through the OPUS API and recorded in the data
manifest, so a preparation run is reproducible even as OPUS publishes newer
releases.

``cap`` bounds how many *raw* pairs are drawn from a corpus (deterministic
hash sampling), so one huge web corpus cannot swamp the mix. Profiles:

* ``core``  - curated, mostly human-translated or software-localisation text,
              plus capped short-string sources (entities, titles) that resemble
              signs and labels. Roughly 1.5 M raw pairs; fits a single GPU day.
* ``large`` - ``core`` plus capped slices of large web-mined and subtitle
              corpora. Noisier; use for longer runs.

Licence notes are what we are confident of; ``see OPUS`` means check the
corpus page before any redistribution or commercial use. The fine-tuned
weights inherit obligations from the data (and from the base model:
opus-mt-ko-en is Apache-2.0, opus-mt-tc-big-en-ko is CC-BY 4.0).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Corpus:
    name: str          # OPUS corpus id
    domain: str
    licence: str
    cap: int | None    # max raw pairs drawn; None = all
    profiles: tuple[str, ...]


CORPORA: list[Corpus] = [
    # --- human translation, general / spoken ---------------------------------
    Corpus("TED2020", "talks (spoken, general)", "CC BY-NC-ND 4.0 (TED)", None, ("core", "large")),
    Corpus("NeuLab-TedTalks", "talks (spoken, general)", "CC BY-NC-ND 4.0 (TED)", None, ("core", "large")),
    Corpus("QED", "educational subtitles", "see OPUS", None, ("core", "large")),
    Corpus("GlobalVoices", "news / citizen media", "CC BY 3.0", None, ("core", "large")),
    Corpus("ELRC-wikipedia_health", "health encyclopedia", "see OPUS", None, ("core", "large")),
    # --- encyclopedic, comparable/mined but clean-ish ------------------------
    # Mined by sentence-embedding similarity; OPUS's moses release carries no
    # scores, and spot checks show misaligned pairs, so it is capped.
    Corpus("WikiMatrix", "encyclopedic (mined)", "CC BY-SA", 150_000, ("core", "large")),
    Corpus("wikimedia", "encyclopedic (translated)", "CC BY-SA", None, ("core", "large")),
    # --- software UI and docs: short imperative strings, like on-screen text ---
    Corpus("KDE4", "software UI strings", "see OPUS (open-source licences)", None, ("core", "large")),
    Corpus("GNOME", "software UI strings", "see OPUS (open-source licences)", None, ("core", "large")),
    Corpus("Ubuntu", "software UI strings", "see OPUS (open-source licences)", None, ("core", "large")),
    Corpus("PHP", "software documentation", "see OPUS", None, ("core", "large")),
    Corpus("translatewiki", "software UI strings", "see OPUS", None, ("core", "large")),
    Corpus("tldr-pages", "command help pages", "CC BY 4.0", None, ("core", "large")),
    Corpus("MDN_Web_Docs", "web documentation", "CC BY-SA 2.5", None, ("core", "large")),
    # --- short strings: entities and titles resemble signs and labels ----------
    # Automatically aligned and noticeably noisy ("Richard of Conisburgh" ->
    # "리처드 케임브리지"); kept small so they add short-string variety only.
    Corpus("XLEnt", "named entities (short)", "see OPUS", 50_000, ("core", "large")),
    Corpus("LinguaTools-WikiTitles", "titles (short)", "see OPUS", 50_000, ("core", "large")),
    # --- large, noisier -------------------------------------------------------
    Corpus("ParaCrawl", "web (mined)", "CC0", 1_500_000, ("large",)),
    Corpus("OpenSubtitles", "film subtitles", "see OPUS (research use)", 1_000_000, ("large",)),
    Corpus("CCMatrix", "web (mined)", "see OPUS", 1_500_000, ("large",)),
]

# Official held-out sets. These are never mixed into training, and any training
# pair that also appears in them is removed (decontamination).
TATOEBA_TEST_URL = ("https://raw.githubusercontent.com/Helsinki-NLP/Tatoeba-Challenge/"
                    "master/data/test/eng-kor/test.txt")
TATOEBA_DEV_URL = ("https://raw.githubusercontent.com/Helsinki-NLP/Tatoeba-Challenge/"
                   "master/data/dev/eng-kor/dev.txt")
FLORES200_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"   # CC BY-SA 4.0

# OPUS's own Tatoeba corpus overlaps the Tatoeba-Challenge test set, so it is
# excluded from training even though it is small and clean.
EXCLUDED_FROM_TRAINING = {"Tatoeba"}

OPUS_API = "https://opus.nlpl.eu/opusapi/?source=en&target=ko&preprocessing=moses&version=latest"


def for_profile(profile: str) -> list[Corpus]:
    return [c for c in CORPORA if profile in c.profiles]
