#!/usr/bin/env python3
"""Downloads, cleans and splits English-Korean parallel data for fine-tuning.

    python tools/mt_train/prepare_data.py                      # core profile
    python tools/mt_train/prepare_data.py --profile large
    python tools/mt_train/prepare_data.py --max-per-corpus 2000   # quick smoke run

Output (default ``tools/mt_train/data/en-ko``), one JSON object per line with
keys ``en``, ``ko`` and ``src`` (origin):

    train.jsonl            cleaned, deduplicated, decontaminated training pairs
    dev.jsonl, test.jsonl  held-out slices of the same mix (hash split)
    tatoeba_dev.jsonl      Tatoeba-Challenge eng-kor dev   (official)
    tatoeba_test.jsonl     Tatoeba-Challenge eng-kor test  (official)
    flores_dev.jsonl       FLORES-200 dev      (eng_Latn / kor_Hang)
    flores_devtest.jsonl   FLORES-200 devtest
    app_domain.jsonl       hand-written signs/menus/UI/forms set (eval/app_domain.tsv)
    manifest.json          resolved corpus versions and URLs, counts, reject reasons

The same files serve both directions; ``train.py --direction`` picks which side
is the source.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tarfile
import time
import urllib.request
import zipfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Iterator

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import corpora  # noqa: E402
from textnorm import FilterConfig, REASONS, check_pair, dedup_key, normalize, strip_artifacts  # noqa: E402

USER_AGENT = "falcon-ocr-trans-mt-train/1.0"


# ------------------------------------------------------------------ download

def http_get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download(url: str, dest: Path, offline: bool) -> Path:
    """Downloads ``url`` to ``dest`` once; later runs reuse the cached file."""
    if dest.is_file() and dest.stat().st_size > 0:
        return dest
    if offline:
        raise SystemExit(f"--offline but {dest} is not cached")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    print(f"  downloading {url}")
    started = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp, tmp.open("wb") as fh:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            if total and sys.stdout.isatty():
                print(f"\r    {done / 1e6:7.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    if sys.stdout.isatty():
        print()
    tmp.replace(dest)
    print(f"    {dest.stat().st_size / 1e6:.1f} MB in {time.time() - started:.0f} s")
    return dest


def resolve_opus(cache: Path, offline: bool) -> dict[str, dict]:
    """Maps OPUS corpus id -> {version, url, pairs} for the latest en-ko release."""
    cached = cache / "opus_api.json"
    if offline or cached.is_file():
        if not cached.is_file():
            raise SystemExit("--offline but the OPUS API response is not cached")
        data = json.loads(cached.read_text(encoding="utf-8"))
    else:
        print("resolving corpus versions via the OPUS API")
        data = json.loads(http_get(corpora.OPUS_API))
        cache.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps(data, indent=1), encoding="utf-8")
    out = {}
    for c in data["corpora"]:
        out[c["corpus"]] = {"version": c["version"], "url": c["url"],
                            "pairs": int(c.get("alignment_pairs") or 0)}
    return out


# ------------------------------------------------------------------- readers

def read_moses_zip(path: Path) -> Iterator[tuple[str, str]]:
    """Yields (en, ko) line pairs from an OPUS moses zip."""
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        en_name = next((n for n in names if n.endswith(".en")), None)
        ko_name = next((n for n in names if n.endswith(".ko")), None)
        if not en_name or not ko_name:
            raise SystemExit(f"{path.name}: no .en/.ko members in {names}")
        with zf.open(en_name) as fe, zf.open(ko_name) as fk:
            en_lines = io.TextIOWrapper(fe, encoding="utf-8", errors="replace")
            ko_lines = io.TextIOWrapper(fk, encoding="utf-8", errors="replace")
            for en, ko in zip(en_lines, ko_lines):
                yield en.rstrip("\n"), ko.rstrip("\n")


def read_tatoeba(text: str) -> list[tuple[str, str]]:
    pairs = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[0] == "eng" and parts[1].startswith("kor"):
            pairs.append((parts[2], parts[3]))
    return pairs


def read_flores(path: Path, split: str) -> list[tuple[str, str]]:
    with tarfile.open(path, "r:gz") as tf:
        def lines(lang: str) -> list[str]:
            member = next(m for m in tf.getmembers()
                          if m.name.endswith(f"{split}/{lang}.{split}"))
            return tf.extractfile(member).read().decode("utf-8").splitlines()
        en, ko = lines("eng_Latn"), lines("kor_Hang")
    if len(en) != len(ko):
        raise SystemExit(f"FLORES {split}: {len(en)} English vs {len(ko)} Korean lines")
    return list(zip(en, ko))


def read_app_domain(path: Path) -> list[tuple[str, str, str]]:
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if i == 0 or not line.strip() or line.startswith("#"):
            continue
        en, ko, cat = (line.split("\t") + ["", ""])[:3]
        rows.append((en, ko, cat))
    return rows


# ------------------------------------------------------------------- helpers

def h64(text: str) -> int:
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big")


def keep_by_rate(key: str, rate: float, seed: int) -> bool:
    """Deterministic Bernoulli(rate) sampling keyed on the pair itself."""
    if rate >= 1.0:
        return True
    return (h64(f"{seed}:{key}") % 1_000_000) < rate * 1_000_000


def side_key(text: str) -> int:
    return h64(normalize(text).casefold())


def write_jsonl(path: Path, rows) -> int:
    n = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------- main

def main() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", choices=("core", "large"), default="core")
    ap.add_argument("--corpus", action="append", help="use only these OPUS corpora (repeatable)")
    ap.add_argument("--out", type=Path, default=HERE / "data" / "en-ko")
    ap.add_argument("--cache", type=Path, default=HERE / "data" / "raw")
    ap.add_argument("--max-per-corpus", type=int, default=None,
                    help="cap raw pairs per corpus (for smoke runs); overrides catalogue caps downward")
    ap.add_argument("--dev-size", type=int, default=2000)
    ap.add_argument("--test-size", type=int, default=2000)
    ap.add_argument("--no-flores", action="store_true", help="skip the FLORES-200 download (25 MB)")
    ap.add_argument("--offline", action="store_true", help="use cached downloads only")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    cfg = FilterConfig()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"profile": args.profile, "seed": args.seed, "filter": asdict(cfg),
                      "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "corpora": {}, "eval": {}}

    # ---- evaluation sets first: training is decontaminated against them ----
    print("== evaluation sets")
    eval_sets: dict[str, list[tuple[str, str]]] = {}
    tat_test = download(corpora.TATOEBA_TEST_URL, args.cache / "tatoeba_eng-kor_test.txt", args.offline)
    tat_dev = download(corpora.TATOEBA_DEV_URL, args.cache / "tatoeba_eng-kor_dev.txt", args.offline)
    eval_sets["tatoeba_test"] = read_tatoeba(tat_test.read_text(encoding="utf-8"))
    eval_sets["tatoeba_dev"] = read_tatoeba(tat_dev.read_text(encoding="utf-8"))
    if not args.no_flores:
        flores = download(corpora.FLORES200_URL, args.cache / "flores200_dataset.tar.gz", args.offline)
        eval_sets["flores_dev"] = read_flores(flores, "dev")
        eval_sets["flores_devtest"] = read_flores(flores, "devtest")
    app_rows = read_app_domain(HERE / "eval" / "app_domain.tsv")
    eval_sets["app_domain"] = [(en, ko) for en, ko, _ in app_rows]

    held_en: set[int] = set()
    held_ko: set[int] = set()
    for name, pairs in eval_sets.items():
        for en, ko in pairs:
            held_en.add(side_key(en))
            held_ko.add(side_key(ko))
        if name == "app_domain":
            rows = ({"en": normalize(en), "ko": normalize(ko), "src": "app_domain", "category": cat}
                    for en, ko, cat in app_rows)
        else:
            rows = ({"en": normalize(en), "ko": normalize(ko), "src": name} for en, ko in pairs)
        n = write_jsonl(args.out / f"{name}.jsonl", rows)
        manifest["eval"][name] = n
        print(f"  {name}: {n} pairs")

    # ---- training corpora ----
    opus = resolve_opus(args.cache, args.offline)
    selected = corpora.for_profile(args.profile)
    if args.corpus:
        wanted = set(args.corpus)
        selected = [c for c in corpora.CORPORA if c.name in wanted]
        missing = wanted - {c.name for c in selected}
        if missing:
            raise SystemExit(f"unknown corpus id(s): {sorted(missing)}")

    seen: set[int] = set()
    kept_rows: list[dict] = []
    totals = Counter()
    for corpus in selected:
        if corpus.name in corpora.EXCLUDED_FROM_TRAINING:
            continue
        info = opus.get(corpus.name)
        if info is None:
            print(f"== {corpus.name}: not offered by OPUS for en-ko; skipped")
            manifest["corpora"][corpus.name] = {"status": "not available"}
            continue
        # Full runs sample uniformly across the corpus up to its cap. Smoke runs
        # (--max-per-corpus) just take the first N lines, which is fast.
        if args.max_per_corpus is not None:
            rate, head = 1.0, args.max_per_corpus
        else:
            rate = 1.0 if not corpus.cap or not info["pairs"] else min(1.0, corpus.cap / info["pairs"])
            head = None
        print(f"== {corpus.name} {info['version']} ({info['pairs']:,} pairs, "
              + (f"first {head:,}" if head else f"sampling {rate:.3f}") + ")")
        path = download(info["url"], args.cache / f"{corpus.name}-{info['version']}.en-ko.zip", args.offline)

        stats = Counter()
        for en_raw, ko_raw in read_moses_zip(path):
            if head is not None and stats["read"] >= head:
                break
            stats["read"] += 1
            if not keep_by_rate(en_raw + "\t" + ko_raw, rate, args.seed):
                continue
            stats["sampled"] += 1
            en, ko = strip_artifacts(normalize(en_raw)), strip_artifacts(normalize(ko_raw))
            reason = check_pair(en, ko, cfg)
            if reason:
                stats[reason] += 1
                continue
            if side_key(en) in held_en or side_key(ko) in held_ko:
                stats["in_eval_set"] += 1
                continue
            k = h64(dedup_key(en, ko))
            if k in seen:
                stats["duplicate"] += 1
                continue
            seen.add(k)
            stats["kept"] += 1
            kept_rows.append({"en": en, "ko": ko, "src": corpus.name})
        totals.update(stats)
        manifest["corpora"][corpus.name] = {
            "version": info["version"], "url": info["url"], "opus_pairs": info["pairs"],
            "sample_rate": round(rate, 6), "domain": corpus.domain, "licence": corpus.licence,
            **dict(stats)}
        rejected = {r: stats[r] for r in (*REASONS, "in_eval_set", "duplicate") if stats[r]}
        print(f"   kept {stats['kept']:,} of {stats['sampled']:,} sampled  rejected {rejected}")

    if not kept_rows:
        raise SystemExit("no training pairs survived; check the corpus list and filters")

    # ---- held-out dev/test from the same mix (deterministic hash split) ----
    n = len(kept_rows)
    dev_rate = min(0.5, args.dev_size / n)
    test_rate = min(0.5, args.test_size / n)
    train, dev, test = [], [], []
    for row in kept_rows:
        u = (h64(f"split:{args.seed}:{row['en']}\t{row['ko']}") % 1_000_000) / 1_000_000
        if u < dev_rate:
            dev.append(row)
        elif u < dev_rate + test_rate:
            test.append(row)
        else:
            train.append(row)

    # Shuffle training data once, reproducibly, so corpora are interleaved on disk.
    train.sort(key=lambda r: h64(f"order:{args.seed}:{r['en']}"))
    counts = {"train": write_jsonl(args.out / "train.jsonl", train),
              "dev": write_jsonl(args.out / "dev.jsonl", dev),
              "test": write_jsonl(args.out / "test.jsonl", test)}
    manifest["splits"] = counts
    manifest["totals"] = dict(totals)
    manifest["sha256"] = {p.name: sha256(p) for p in sorted(args.out.glob("*.jsonl"))}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                            encoding="utf-8")
    print(f"\ntrain {counts['train']:,}  dev {counts['dev']:,}  test {counts['test']:,}  -> {args.out}")


if __name__ == "__main__":
    main()
