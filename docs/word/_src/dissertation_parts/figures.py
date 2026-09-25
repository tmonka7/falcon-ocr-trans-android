"""Figures for the dissertation, drawn from scratch with matplotlib and PIL.

Every figure here is either a schematic of the system (derived from the source
code) or a synthetic illustration of an algorithm. None of them shows a
measurement; captions in the chapters say so where it matters.
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle, FancyArrowPatch  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

DPI = 200
INK = "#1F232B"
MUTED = "#5F6778"
ACCENT = "#A81515"
BLUE = "#2E5E9E"
GREEN = "#3B7D4F"
ORANGE = "#C0762A"
FILL_A = "#E9ECF2"
FILL_B = "#FBEAEA"
FILL_C = "#E6F0E8"
FILL_D = "#FFF6E5"
FILL_E = "#E4ECF7"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

WINFONTS = Path("C:/Windows/Fonts")


def _font(name: str, size: int):
    for cand in (WINFONTS / name, WINFONTS / "arial.ttf"):
        try:
            return ImageFont.truetype(str(cand), size)
        except OSError:
            continue
    return ImageFont.load_default()


# --------------------------------------------------------------------- helpers

def _canvas(w: float, h: float):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w * 10)
    ax.set_ylim(0, h * 10)
    ax.axis("off")
    return fig, ax


def _box(ax, x, y, w, h, text, fc=FILL_A, ec=MUTED, fs=8.5, bold=False, color=INK, round_=True):
    style = "round,pad=0.02,rounding_size=0.8" if round_ else "square,pad=0.02"
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, fc=fc, ec=ec, lw=0.9))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=color, wrap=True)


def _arrow(ax, p, q, color=MUTED, lw=1.0, style="-|>", ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=9, color=color,
                                 lw=lw, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}"))


def _save(fig, path: Path):
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- chapter 3

def fig_architecture(path: Path):
    fig, ax = _canvas(9, 6.2)
    _box(ax, 2, 52, 86, 8, "ui  —  Splash · Main (home) · Camera · ImageImport · Pdf · Result · Translate · "
         "Language · History · Settings", fc=FILL_E, fs=8)
    _box(ax, 2, 39, 86, 9, "engine  —  Engines (process singleton, one worker thread \"falcon-engine\")\n"
         "TranslationPipeline · ModelValidator · ModelPaths · ScriptDetector · ResultHolder", fc=FILL_B, fs=8)
    xs = [2, 24, 46, 68]
    labels = [("ocr", "PaddleOcrEngine\nDbPostProcessor\nImageOps · CtcDecoder\nCharDict · LineGrouper"),
              ("mt", "PivotTranslator\nMarianTranslator\nSpmEncoder · MtVocab\nMtConfig"),
              ("render", "LayoutRenderer\nTextFitter"),
              ("pdf", "PdfPageSource\nPdfJob · DocxWriter")]
    for x, (name, body) in zip(xs, labels):
        _box(ax, x, 21, 20, 14, f"{name}\n{body}", fc=FILL_C, fs=7.5)
    _box(ax, 2, 10, 42, 7, "core  —  Lang · Quad · TextLine · Paragraph · OcrResult", fc=FILL_A, fs=8)
    _box(ax, 46, 10, 42, 7, "data  —  Prefs (SharedPreferences) · HistoryStore (SQLite)", fc=FILL_A, fs=8)
    _box(ax, 2, 0.5, 42, 6.5, "ONNX Runtime (Java API, native .so from AAR)", fc=FILL_D, fs=8)
    _box(ax, 46, 0.5, 42, 6.5, "assets/model/  (≈230 MB, STORED entries)", fc=FILL_D, fs=8)
    for x in (45, ):
        _arrow(ax, (x, 52), (x, 48.2))
    for x in (12, 34, 56, 78):
        _arrow(ax, (x, 39), (x, 35.2))
    _arrow(ax, (23, 21), (23, 17.2))
    _arrow(ax, (67, 21), (67, 17.2))
    ax.text(90, 56, "presentation", fontsize=7, color=MUTED, rotation=90, va="center")
    ax.text(90, 43.5, "orchestration", fontsize=7, color=MUTED, rotation=90, va="center")
    ax.text(90, 28, "algorithms", fontsize=7, color=MUTED, rotation=90, va="center")
    ax.text(90, 9, "foundation", fontsize=7, color=MUTED, rotation=90, va="center")
    _save(fig, path)


def fig_pipeline(path: Path):
    fig, ax = _canvas(9.5, 3.4)
    stages = [
        ("Input", "camera frame,\nimage, or PDF\npage @200 dpi", FILL_A),
        ("Detection", "resize ≤ L_max,\n×32 · PP-OCRv4\n→ map P", FILL_E),
        ("DB post-proc.", "τ_b=0.3 · 8-conn.\nhull · min-rect\nunclip r=1.6", FILL_E),
        ("Recognition", "crop · 180° cls\nbatch 6 · CTC\nink/paper colour", FILL_E),
        ("Layout", "reading order\nparagraphs\nscript check", FILL_C),
        ("Translation", "SPM Viterbi\nMarian greedy\nCJK via EN", FILL_B),
        ("Re-render", "highlight α\nfit size · halo\n+ ink text", FILL_D),
    ]
    w, gap = 11.6, 1.9
    for i, (t, b, fc) in enumerate(stages):
        x = 1 + i * (w + gap)
        _box(ax, x, 6, w, 20, "", fc=fc)
        ax.text(x + w / 2, 22.5, t, ha="center", va="center", fontsize=8.5, fontweight="bold", color=INK)
        ax.text(x + w / 2, 13, b, ha="center", va="center", fontsize=7, color=INK)
        if i < len(stages) - 1:
            _arrow(ax, (x + w, 16), (x + w + gap, 16))
    ax.text(48, 1.5, "all stages execute on the device, serialised on one background worker thread",
            ha="center", fontsize=7.5, color=MUTED, style="italic")
    _save(fig, path)


def fig_threading(path: Path):
    fig, ax = _canvas(9, 5.2)
    lanes = [("UI (main) thread", 42), ("falcon-engine worker\n(NORM_PRIORITY − 1)", 24), ("ONNX Runtime\nintra-op pool (≤4)", 7)]
    for name, y in lanes:
        ax.add_patch(Rectangle((14, y - 5), 75, 10, fc="#F7F8FA", ec="#D5D9E0", lw=0.8))
        ax.text(1, y, name, fontsize=7.5, va="center", color=INK)
    _box(ax, 16, 39, 12, 6, "tap / capture", fc=FILL_E, fs=7)
    _arrow(ax, (28, 42), (32, 27))
    ax.text(29, 35, "submit()", fontsize=7, color=MUTED)
    _box(ax, 32, 21, 11, 6, "recognize", fc=FILL_C, fs=7)
    _box(ax, 45, 21, 11, 6, "translate", fc=FILL_B, fs=7)
    _box(ax, 58, 21, 11, 6, "render", fc=FILL_D, fs=7)
    _arrow(ax, (43, 24), (45, 24))
    _arrow(ax, (56, 24), (58, 24))
    for x in (37.5, 50.5):
        _arrow(ax, (x, 21), (x, 10.5), style="<|-|>")
    _box(ax, 33, 4, 22, 6, "session.run() fan-out", fc=FILL_A, fs=7)
    _arrow(ax, (69, 24), (74, 39))
    ax.text(70, 33, "Handler.post()", fontsize=7, color=MUTED)
    _box(ax, 73, 39, 14, 6, "show result", fc=FILL_E, fs=7)
    _box(ax, 16, 47.5, 30, 3.8, "UI stays responsive: no inference on this thread", fc="white", ec="white", fs=6.8,
         color=MUTED)
    _save(fig, path)


def fig_dataflow(path: Path):
    fig, ax = _canvas(9.5, 4.6)
    items = [
        (1, 30, "Bitmap I\nW×H ARGB", FILL_A),
        (17, 30, "float[] P\nh×w map", FILL_E),
        (33, 30, "List<Quad> q_i\n(tl,tr,br,bl)", FILL_E),
        (49, 30, "crops +\nDecoded(x_i,c_i)", FILL_E),
        (65, 30, "TextLine\nq_i,x_i,c_i,κ_i,π_i", FILL_C),
        (81, 30, "Paragraph P_j\nsource text", FILL_C),
        (81, 8, "translated\ntext y_j", FILL_B),
        (65, 8, "Block\n(y, T, θ, κ, π, {q_i})", FILL_D),
        (49, 8, "StaticLayout\n@ fitted size s*", FILL_D),
        (33, 8, "rendered Î\n(new bitmap)", FILL_A),
        (17, 8, "history row /\nPDF · DOCX · TXT", FILL_A),
    ]
    for x, y, t, fc in items:
        _box(ax, x, y, 13.5, 9, t, fc=fc, fs=7)
    for i in range(5):
        x = 1 + i * 16 + 13.5
        _arrow(ax, (x, 34.5), (x + 2.5, 34.5))
    _arrow(ax, (87.7, 30), (87.7, 17.2))
    for x in (81, 65, 49, 33):
        _arrow(ax, (x, 12.5), (x - 2.5, 12.5))
    ax.text(48, 44, "OCR domain (page pixels)", ha="center", fontsize=8, color=BLUE)
    ax.text(48, 2, "rendering / output domain", ha="center", fontsize=8, color=ORANGE)
    _save(fig, path)


def fig_model_tree(path: Path):
    fig, ax = _canvas(9, 5.0)
    _box(ax, 38, 42, 16, 6, "assets/model/", fc=FILL_D, fs=8, bold=True)
    _box(ax, 10, 30, 22, 6, "ocr/  (≈40 MB)", fc=FILL_E, fs=8)
    _box(ax, 60, 30, 22, 6, "mt/  (≈190 MB)", fc=FILL_B, fs=8)
    _arrow(ax, (42, 42), (24, 36.2))
    _arrow(ax, (50, 42), (68, 36.2))
    ocr = ["det/det.onnx\nPP-OCRv4 det", "cls/cls.onnx\nv2.0 (optional)",
           "rec/english\nen PP-OCRv4", "rec/korean\nPP-OCRv3", "rec/japan\nPP-OCRv3", "rec/chinese\nch PP-OCRv4"]
    for i, t in enumerate(ocr):
        x = 0.5 + (i % 3) * 14.5
        y = 17 - (i // 3) * 11
        _box(ax, x, y, 13.5, 8.5, t, fc="white", fs=6.5)
    _arrow(ax, (21, 30), (21, 25.7))
    mt = ["en-ko (tc-big)", "ko-en", "en-ja", "ja-en", "en-zh", "zh-en"]
    for i, t in enumerate(mt):
        x = 47 + (i % 3) * 14.5
        y = 19.5 - (i // 3) * 7
        _box(ax, x, y, 13.5, 5.5, t, fc="white", fs=7)
    _arrow(ax, (71, 30), (71, 25.2))
    ax.text(47, 3.0, "each pair: encoder.int8.onnx · decoder.int8.onnx · source.spm.tsv · vocab.tsv · config.json",
            fontsize=6.4, color=MUTED)
    ax.text(47, 0.2, "no CJK↔CJK directories: those six directions are pivoted through English",
            fontsize=6.4, color=MUTED, style="italic")
    _save(fig, path)


# ---------------------------------------------------------------- chapter 4

def _flood(mask: np.ndarray):
    h, w = mask.shape
    lab = np.zeros((h, w), dtype=int)
    n = 0
    for y in range(h):
        for x in range(w):
            if mask[y, x] and lab[y, x] == 0:
                n += 1
                stack = [(y, x)]
                lab[y, x] = n
                while stack:
                    cy, cx = stack.pop()
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and lab[ny, nx] == 0:
                                lab[ny, nx] = n
                                stack.append((ny, nx))
    return lab, n


def _hull(pts):
    pts = sorted(set(map(tuple, pts)))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _min_rect(hull):
    best = None
    n = len(hull)
    for i in range(n):
        a, b = np.array(hull[i], float), np.array(hull[(i + 1) % n], float)
        e = b - a
        L = np.hypot(*e)
        if L < 1e-9:
            continue
        u = e / L
        v = np.array([-u[1], u[0]])
        P = np.array(hull, float)
        pu, pv = P @ u, P @ v
        area = (pu.max() - pu.min()) * (pv.max() - pv.min())
        if best is None or area < best[0]:
            cu, cv = (pu.max() + pu.min()) / 2, (pv.max() + pv.min()) / 2
            c = cu * u + cv * v
            best = (area, c, (pu.max() - pu.min()) / 2, (pv.max() - pv.min()) / 2, u, v)
    return best


def _rect_corners(c, a, b, u, v):
    return np.array([c - a * u - b * v, c + a * u - b * v, c + a * u + b * v, c - a * u + b * v])


def _synthetic_prob_map(seed=7):
    rng = np.random.default_rng(seed)
    h, w = 90, 160
    yy, xx = np.mgrid[0:h, 0:w]
    P = np.zeros((h, w))

    def band(cx, cy, hw, hh, ang):
        t = math.radians(ang)
        u = (xx - cx) * math.cos(t) + (yy - cy) * math.sin(t)
        v = -(xx - cx) * math.sin(t) + (yy - cy) * math.cos(t)
        return np.clip(1.2 - np.maximum(np.abs(u) / hw, np.abs(v) / hh) ** 6, 0, 1)

    P = np.maximum(P, band(52, 22, 38, 6, 0) * 0.95)
    P = np.maximum(P, band(105, 60, 36, 6, -24) * 0.9)
    P = np.maximum(P, band(35, 66, 16, 5, 0) * 0.5)   # low-confidence blob, rejected by score
    P += rng.normal(0, 0.05, P.shape)
    P[5:7, 140:142] = 0.9  # speck, rejected by area
    return np.clip(P, 0, 1)


def fig_db_steps(path: Path):
    P = _synthetic_prob_map()
    B = P >= 0.3
    lab, n = _flood(B)
    fig, axs = plt.subplots(1, 4, figsize=(10, 2.6))
    axs[0].imshow(P, cmap="magma", vmin=0, vmax=1)
    axs[0].set_title("(a) probability map P", fontsize=8.5)
    cm = plt.get_cmap("tab10")
    col = np.ones(B.shape + (3,))
    kept = []
    for k in range(1, n + 1):
        m = lab == k
        area = int(m.sum())
        score = float(P[m].mean())
        if area < 12:
            col[m] = (0.75, 0.75, 0.75)
            continue
        if score < 0.6:
            col[m] = (0.85, 0.6, 0.6)
            continue
        col[m] = cm(len(kept) % 10)[:3]
        kept.append(m)
    axs[1].imshow(col)
    axs[1].set_title("(b) P ≥ 0.3, 8-conn. comps;\nred: S(C)<0.6, grey: <12 px", fontsize=8)
    axs[2].imshow(B, cmap="Greys", alpha=0.25)
    axs[3].imshow(P, cmap="Greys", alpha=0.35)
    for m in kept:
        ys, xs = np.nonzero(m)
        ext = []
        for y in np.unique(ys):
            row = xs[ys == y]
            ext.append((row.min(), y))
            if row.max() != row.min():
                ext.append((row.max(), y))
        ext = np.array(ext)
        axs[2].plot(ext[:, 0], ext[:, 1], ".", ms=1.5, color=ACCENT)
        hull = _hull(ext)
        H = np.array(hull + [hull[0]])
        axs[2].plot(H[:, 0], H[:, 1], "-", lw=0.9, color=BLUE)
        area, c, a, b, u, v = _min_rect(hull)
        R = _rect_corners(c, a, b, u, v)
        axs[3].add_patch(Polygon(R, fill=False, ec=BLUE, lw=0.9, ls="--"))
        bw, bh = 2 * a, 2 * b
        d = bw * bh * 1.6 / (2 * (bw + bh))
        R2 = _rect_corners(c, a + d, b + d, u, v)
        axs[3].add_patch(Polygon(R2, fill=False, ec=ACCENT, lw=1.2))
    axs[2].set_title("(c) row extremes R(C) and\nconvex hull (monotone chain)", fontsize=8)
    axs[3].set_title("(d) min-area rectangle (dashed)\nand unclipped quad (solid)", fontsize=8)
    for a_ in axs:
        a_.set_xticks([])
        a_.set_yticks([])
        for s in a_.spines.values():
            s.set_visible(True)
            s.set_color("#D5D9E0")
    fig.tight_layout()
    _save(fig, path)


def fig_hull_geometry(path: Path):
    rng = np.random.default_rng(3)
    # A slanted, ragged component on the integer grid.
    pts = []
    for y in range(0, 14):
        x0 = int(4 + 0.9 * y + rng.integers(0, 3))
        x1 = int(30 + 0.9 * y - rng.integers(0, 3))
        for x in range(x0, x1 + 1):
            pts.append((x, y))
    pts = np.array(pts)
    ext = []
    for y in np.unique(pts[:, 1]):
        row = pts[pts[:, 1] == y][:, 0]
        ext += [(row.min(), y), (row.max(), y)]
    ext = np.array(ext)
    hull = _hull(ext)
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.2))
    ax = axs[0]
    ax.plot(pts[:, 0], pts[:, 1], "s", ms=2.2, color="#C9CED8")
    ax.plot(ext[:, 0], ext[:, 1], "s", ms=3.0, color=ACCENT, label="row extremes R(C)")
    H = np.array(hull + [hull[0]])
    ax.plot(H[:, 0], H[:, 1], "-", color=BLUE, lw=1.2, label="conv(R(C)) = conv(C)")
    # Interior point that is a strict convex combination of row extremes.
    y0 = 6
    row = pts[pts[:, 1] == y0][:, 0]
    mid = (row.min() + row.max()) // 2
    ax.annotate("v: strict convex combination\nof a and b ⇒ not extreme", xy=(mid, y0), xytext=(mid - 4, y0 + 9.5),
                fontsize=7, arrowprops=dict(arrowstyle="->", color=MUTED), color=INK)
    ax.plot([row.min(), row.max()], [y0, y0], "-", color=GREEN, lw=1.0)
    ax.text(row.min() - 2.2, y0 - 0.3, "a", fontsize=8, color=GREEN)
    ax.text(row.max() + 0.6, y0 - 0.3, "b", fontsize=8, color=GREEN)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.legend(fontsize=7, loc="lower right", frameon=False)
    ax.set_title("(a) Lemma 4.1: only row extremes can be hull vertices", fontsize=8.5)
    ax.set_xticks([])
    ax.set_yticks([])
    ax = axs[1]
    ax.plot(H[:, 0], H[:, 1], "-", color=BLUE, lw=1.2)
    best = _min_rect(hull)
    n = len(hull)
    for i in range(n):
        a_, b_ = np.array(hull[i], float), np.array(hull[(i + 1) % n], float)
        e = b_ - a_
        L = np.hypot(*e)
        if L < 1e-9:
            continue
        u = e / L
        v = np.array([-u[1], u[0]])
        P = np.array(hull, float)
        pu, pv = P @ u, P @ v
        c = (pu.max() + pu.min()) / 2 * u + (pv.max() + pv.min()) / 2 * v
        R = _rect_corners(c, (pu.max() - pu.min()) / 2, (pv.max() - pv.min()) / 2, u, v)
        ax.add_patch(Polygon(R, fill=False, ec="#C9CED8", lw=0.6))
    area, c, a, b, u, v = best
    R = _rect_corners(c, a, b, u, v)
    ax.add_patch(Polygon(R, fill=False, ec=ACCENT, lw=1.5))
    ax.annotate("", xy=c + 6 * u, xytext=c, arrowprops=dict(arrowstyle="->", color=INK))
    ax.text(*(c + 6.5 * u), " u (baseline)", fontsize=7, color=INK)
    ax.plot(*c, "o", ms=3, color=INK)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_title("(b) candidate rectangles flush with each hull edge;\nminimum-area choice in red", fontsize=8.5)
    ax.set_xticks([])
    ax.set_yticks([])
    for a_ in axs:
        for s in a_.spines.values():
            s.set_visible(False)
    fig.tight_layout()
    _save(fig, path)


def fig_unclip(path: Path):
    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    ws = np.linspace(4, 200, 300)
    for h, colr in ((8, BLUE), (16, GREEN), (32, ORANGE), (64, ACCENT)):
        d = ws * h * 1.6 / (2 * (ws + h))
        ax.plot(ws, d, color=colr, lw=1.3, label=f"h = {h} px")
        ax.axhline(0.8 * h, color=colr, lw=0.6, ls=":")
    ax.set_xlabel("rectangle width w (px, detector map)")
    ax.set_ylabel("unclip offset d (px)")
    ax.set_title("Closed-form unclip d = w·h·r / (2(w+h)), r = 1.6 (analytical; dotted: limit r·h/2 as w → ∞)",
                 fontsize=8.5)
    ax.legend(fontsize=7, frameon=False, ncol=4)
    _save(fig, path)


def fig_batching(path: Path):
    rng = np.random.default_rng(11)
    ratios = np.concatenate([rng.uniform(1.2, 4, 7), rng.uniform(6, 14, 7), rng.uniform(16, 24, 4)])
    rng.shuffle(ratios)
    H = 48

    def pads(order):
        rows = []
        for s in range(0, len(order), 6):
            grp = order[s:s + 6]
            padw = min(1200, max(16, int(math.ceil(max(ratios[grp]) * H / 8) * 8)))
            for i in grp:
                rows.append((min(padw, ratios[i] * H), padw))
        return rows

    un = pads(np.arange(len(ratios)))
    so = pads(np.argsort(ratios))
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.2), sharey=True)
    for ax, rows, title in ((axs[0], un, "(a) arrival order"), (axs[1], so, "(b) sorted by aspect ratio")):
        for k, (used, padw) in enumerate(rows):
            ax.barh(k, used, color=BLUE, height=0.75)
            ax.barh(k, padw - used, left=used, color="#E3C3C3", height=0.75)
            if k % 6 == 0 and k:
                ax.axhline(k - 0.5, color=MUTED, lw=0.6, ls="--")
        total = sum(p for _, p in rows)
        waste = sum(p - u for u, p in rows)
        ax.set_title(title, fontsize=8.5)
        ax.set_xlabel("tensor width (px) at height 48")
        ax.invert_yaxis()
        ax.set_yticks([])
    axs[0].set_ylabel("crop (batches of 6)")
    fig.suptitle("Synthetic illustration: blue = image content, pink = zero padding", fontsize=8.5, color=MUTED)
    fig.tight_layout()
    _save(fig, path)


def fig_paragraph_rules(path: Path):
    fig, ax = _canvas(9, 3.6)
    ax.add_patch(Rectangle((8, 22), 46, 6, fc=FILL_E, ec=BLUE))
    ax.text(31, 25, "line m  (height h_m, angle θ_m)", ha="center", va="center", fontsize=7.5)
    ax.add_patch(Rectangle((14, 11), 52, 6, fc=FILL_C, ec=GREEN))
    ax.text(40, 14, "line n  (height h_n, angle θ_n)", ha="center", va="center", fontsize=7.5)
    ax.annotate("", xy=(58, 22), xytext=(58, 17), arrowprops=dict(arrowstyle="<->", color=ACCENT))
    ax.text(59, 19.2, "gap", fontsize=7, color=ACCENT)
    ax.plot([14, 14], [8, 31], ":", color=MUTED)
    ax.plot([54, 54], [8, 31], ":", color=MUTED)
    ax.annotate("", xy=(14, 7), xytext=(54, 7), arrowprops=dict(arrowstyle="<->", color=INK))
    ax.text(34, 4.2, "overlap_x / min(w_m, w_n) ≥ 0.25", ha="center", fontsize=7)
    ax.text(66, 30, "continue paragraph iff all hold:", fontsize=7.5, fontweight="bold")
    rules = ["max(h)/min(h) ≤ 1.7", "|θ_m − θ_n| ≤ 8°", "gap ≤ 1.6·max(h_m, h_n)", "cy_n ≥ cy_m",
             "horizontal overlap ≥ 0.25"]
    for i, r in enumerate(rules):
        ax.text(67, 26 - i * 3.6, "• " + r, fontsize=7.2)
    _save(fig, path)


# ---------------------------------------------------------------- chapter 5

def fig_viterbi(path: Path):
    s = "▁unhappy"
    vocab = {"▁un": -3.0, "▁u": -6.0, "n": -5.0, "happy": -4.0, "▁unh": -9.0, "app": -6.5, "y": -4.5,
             "h": -5.5, "ha": -6.0, "ppy": -7.0, "▁": -2.5, "un": -4.0, "hap": -6.0, "py": -6.2}
    n = len(s)
    best = [-1e9] * (n + 1)
    back = [0] * (n + 1)
    best[0] = 0
    edges = []
    for e in range(1, n + 1):
        for st in range(max(0, e - 5), e):
            piece = s[st:e]
            if piece in vocab:
                edges.append((st, e, piece))
                if best[st] + vocab[piece] > best[e]:
                    best[e] = best[st] + vocab[piece]
                    back[e] = st
    path_ = []
    p = n
    while p > 0:
        path_.append((back[p], p))
        p = back[p]
    fig, ax = plt.subplots(figsize=(9.5, 3.3))
    for i in range(n + 1):
        ax.plot(i, 0, "o", color=INK, ms=4)
        ax.text(i, -0.35, str(i), ha="center", fontsize=7, color=MUTED)
        if i < n:
            ax.text(i + 0.5, -0.8, s[i], ha="center", fontsize=10, color=INK)
    for st, e, piece in edges:
        on = (st, e) in path_
        h = 0.25 * (e - st)
        xs = np.linspace(st, e, 40)
        ys = h * np.sin(np.pi * (xs - st) / (e - st))
        ax.plot(xs, ys, color=ACCENT if on else "#C9CED8", lw=1.8 if on else 0.8)
        ax.text((st + e) / 2, h + 0.06, f"{piece} ({vocab[piece]:g})", ha="center", fontsize=6.3,
                color=ACCENT if on else MUTED)
    ax.set_ylim(-1.1, 1.6)
    ax.set_xlim(-0.5, n + 0.5)
    ax.axis("off")
    ax.set_title("Toy unigram lattice (illustrative scores): Viterbi path in red, total "
                 f"{best[n]:.1f} = best Σ log p", fontsize=8.5)
    _save(fig, path)


def fig_decoder_cost(path: Path):
    n = np.arange(1, 129)
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.0))
    axs[0].plot(n, n * (n + 1) / 2, color=ACCENT, lw=1.4, label="cacheless: n(n+1)/2")
    axs[0].plot(n, n, color=BLUE, lw=1.4, label="with KV cache: n")
    axs[0].set_xlabel("generated tokens n")
    axs[0].set_ylabel("decoder positions processed")
    axs[0].legend(fontsize=7, frameon=False)
    axs[0].set_title("(a) positions evaluated (analytical)", fontsize=8.5)
    axs[1].plot(n, (n + 1) / 2, color=INK, lw=1.4)
    for k in (8, 16, 32, 64):
        axs[1].plot(k, (k + 1) / 2, "o", color=ACCENT, ms=3)
        axs[1].text(k + 2, (k + 1) / 2 - 2.5, f"n={k}: {(k + 1) / 2:g}×", fontsize=7)
    axs[1].set_xlabel("generated tokens n")
    axs[1].set_ylabel("overhead factor (n+1)/2")
    axs[1].set_title("(b) position-count ratio (analytical)", fontsize=8.5)
    fig.tight_layout()
    _save(fig, path)


def fig_pivot(path: Path):
    fig, ax = _canvas(8, 5.0)
    ax.set_ylim(-4, 56)
    pos = {"EN": (40, 25), "KO": (12, 42), "JA": (68, 42), "ZH": (40, 4)}
    for k, (x, y) in pos.items():
        ax.add_patch(plt.Circle((x, y), 5.2, fc=FILL_B if k == "EN" else FILL_E, ec=MUTED))
        ax.text(x, y, k, ha="center", va="center", fontsize=10, fontweight="bold")
    for k in ("KO", "JA", "ZH"):
        (x1, y1), (x2, y2) = pos["EN"], pos[k]
        d = np.array([x2 - x1, y2 - y1])
        d = d / np.linalg.norm(d)
        _arrow(ax, (x1 + 5.6 * d[0], y1 + 5.6 * d[1]), (x2 - 5.6 * d[0], y2 - 5.6 * d[1]), color=INK, lw=1.3,
               style="<|-|>")
    _arrow(ax, (17.5, 43), (62.5, 43), color=ACCENT, lw=1.0, ls="--", style="<|-|>", rad=-0.25)
    _arrow(ax, (10, 36.8), (35, 5), color=ACCENT, lw=1.0, ls="--", style="<|-|>", rad=0.3)
    _arrow(ax, (70, 36.8), (45, 5), color=ACCENT, lw=1.0, ls="--", style="<|-|>", rad=-0.3)
    ax.text(55, 52, "no OPUS-MT model: served as ℓ_s → EN → ℓ_t", ha="center", fontsize=7.5, color=ACCENT)
    ax.text(0, -3, "solid: 6 direct int8 pairs\n(one pair resident at a time)", fontsize=7.5, color=INK)
    ax.text(0, 52, "dashed: 6 pivoted directions\n(two legs, each a whole-page batch)", fontsize=7.5, color=ACCENT)
    _save(fig, path)


# ---------------------------------------------------------------- chapter 6

def fig_highlight_union(path: Path):
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.2))
    quads = [np.array([[10, 10], [90, 10], [90, 22], [10, 22]], float),
             np.array([[10, 24], [80, 24], [80, 36], [10, 36]], float),
             np.array([[10, 38], [60, 38], [60, 50], [10, 50]], float)]

    def grow(q, g=0.06):
        c = q.mean(axis=0)
        return c + (q - c) * (1 + g)

    target = np.array([[10, 10], [90, 10], [90, 50], [10, 50]], float)
    for ax, union in ((axs[0], False), (axs[1], True)):
        img = np.ones((60, 100, 3))
        img[:, :] = (0.93, 0.90, 0.84)
        acc = np.zeros((60, 100))
        yy, xx = np.mgrid[0:60, 0:100]
        from matplotlib.path import Path as MPath
        masks = [MPath(grow(q)).contains_points(np.c_[xx.ravel() + .5, yy.ravel() + .5]).reshape(60, 100)
                 for q in quads + [target]]
        alpha = 150 / 255
        if union:
            m = np.any(masks, axis=0)
            acc = m * alpha
        else:
            acc = np.zeros((60, 100))
            for m in masks:
                acc = acc + m * alpha * (1 - acc)
        paper = np.array([1.0, 1.0, 1.0])
        img = img * (1 - acc[..., None]) + paper * acc[..., None]
        img[img < 0] = 0
        # darken for visibility of stacking
        ax.imshow(img ** 2.2, interpolation="nearest")
        for q in quads:
            ax.add_patch(Polygon(grow(q), fill=False, ec=BLUE, lw=0.6, ls=":"))
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title("(b) geometric union, then one fill: uniform α" if union else
                     "(a) shapes filled one by one: α compounds in overlaps", fontsize=8.5)
    fig.tight_layout()
    _save(fig, path)


def _textured_patch(w=420, h=180, seed=5):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    base = np.zeros((h, w, 3))
    grad = xx / w
    base[..., 0] = 0.86 - 0.22 * grad
    base[..., 1] = 0.80 - 0.10 * grad
    base[..., 2] = 0.68 + 0.12 * grad
    fibre = rng.normal(0, 1, (h // 3 + 1, w // 3 + 1))
    fibre = np.kron(fibre, np.ones((3, 3)))[:h, :w]
    stripes = 0.035 * np.sin(xx / 7.0 + yy / 23.0)
    base += (0.045 * fibre + stripes)[..., None]
    return (np.clip(base, 0, 1) * 255).astype(np.uint8)


def fig_compositing(path: Path):
    """Synthetic illustration: opaque erase vs translucent highlight + halo."""
    W, H = 420, 180
    base = Image.fromarray(_textured_patch(W, H))
    f_src = _font("georgiab.ttf", 44)
    f_new = _font("arial.ttf", 34)
    ink = (38, 32, 30)
    orig = base.copy()
    d = ImageDraw.Draw(orig)
    d.text((34, 40), "Notice to", font=f_src, fill=ink)
    d.text((34, 92), "all visitors", font=f_src, fill=ink)
    arr = np.asarray(orig).astype(float)
    # paper estimate: mean of the lighter half of the text region
    region = arr[35:150, 25:395]
    lum = region @ np.array([0.299, 0.587, 0.114])
    mid = (lum.min() + lum.max()) / 2
    paper = region[lum >= mid].mean(axis=0)
    paper_t = tuple(int(v) for v in paper)
    box = (22, 32, 400, 152)

    def with_new_text(img, halo):
        dd = ImageDraw.Draw(img)
        for (x, y, t) in ((34, 50, "Hinweis an"), (34, 96, "alle Besucher")):
            if halo:
                dd.text((x, y), t, font=f_new, fill=ink, stroke_width=max(1, round(0.16 * 34 / 2)),
                        stroke_fill=paper_t)
            else:
                dd.text((x, y), t, font=f_new, fill=ink)
        return img

    opaque = orig.copy()
    ImageDraw.Draw(opaque).rectangle(box, fill=paper_t)
    opaque = with_new_text(opaque, halo=False)

    def translucent(halo):
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).rounded_rectangle(box, radius=int(0.18 * 52), fill=150)
        mask = mask.filter(ImageFilter.GaussianBlur(0.06 * 52))
        solid = Image.new("RGB", (W, H), paper_t)
        out = Image.composite(solid, orig, mask)
        return with_new_text(out, halo=halo)

    tr_nohalo = translucent(False)
    tr_halo = translucent(True)
    panels = [(orig, "(a) synthetic original"), (opaque, "(b) opaque fill, α = 255"),
              (tr_nohalo, "(c) translucent α = 150, no halo"), (tr_halo, "(d) translucent α = 150 + halo")]
    fig, axs = plt.subplots(2, 2, figsize=(9.5, 4.6))
    for ax, (im, t) in zip(axs.ravel(), panels):
        ax.imshow(im)
        ax.set_title(t, fontsize=8.5)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Synthetic illustration of the compositing rule (generated patch and text; not an experimental result)",
                 fontsize=8.5, color=MUTED)
    fig.tight_layout()
    _save(fig, path)
    # Return a measured property of the *synthetic* illustration for the caption check only.
    return None


def fig_attenuation(path: Path):
    a = np.linspace(0, 255, 256)
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    ax.plot(a, 1 - a / 255, color=INK, lw=1.4)
    for v, lab in ((90, "90"), (150, "150 (default)"), (200, "200"), (255, "255 (opaque)")):
        ax.plot(v, 1 - v / 255, "o", color=ACCENT, ms=4)
        ax.text(v + 3, 1 - v / 255 + 0.04, f"α={lab}: 1−α = {1 - v / 255:.2f}", fontsize=7)
    ax.set_xlabel("highlight alpha (0–255)")
    ax.set_ylabel("retained fraction 1 − α")
    ax.set_title("Ghost contrast and texture amplitude inside Ω (Proposition 6.1, analytical)", fontsize=8.5)
    ax.set_ylim(-0.05, 1.1)
    _save(fig, path)


def fig_textfit(path: Path):
    words = ("Please scan the code at the entrance to register your visit and receive "
             "the building information leaflet").split()
    width = 300.0
    box_h = 96.0

    def height(s):
        adv = 0.52 * s
        lines, cur = 1, 0.0
        for w_ in words:
            wl = len(w_) * adv
            need = wl if cur == 0 else cur + adv + wl
            if need > width and cur > 0:
                lines += 1
                cur = wl
            else:
                cur = need
        return lines * 1.17 * s

    p = 24.0
    lo, hi = max(4, 0.45 * p), 1.15 * p
    ss = np.linspace(lo - 1, hi + 1, 800)
    hs = [height(s) for s in ss]
    fig, ax = plt.subplots(figsize=(8.5, 3.2))
    ax.plot(ss, hs, color=INK, lw=1.2, label="layout height H(s)")
    ax.axhline(box_h, color=ACCENT, ls="--", lw=1, label="target height |T|_h")
    ax.axvspan(lo, hi, color=FILL_E, alpha=0.6, label="search interval [0.45p, 1.15p]")
    it = 0
    a, b = lo, hi
    while b - a > 0.25:
        m = (a + b) / 2
        it += 1
        ok = height(m) <= box_h
        ax.plot(m, height(m), "o", ms=4, color=GREEN if ok else ACCENT)
        ax.text(m, height(m) + 4, str(it), fontsize=6.5, ha="center")
        if ok:
            a = m
        else:
            b = m
    ax.set_xlabel("font size s (px), anchor p = 24 px")
    ax.set_ylabel("height (px)")
    ax.set_title(f"Synthetic illustration: bisection to ε = 0.25 px takes {it} layouts after the "
                 "feasibility check; green = fits", fontsize=8.5)
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    _save(fig, path)
    return it


# ---------------------------------------------------------------- chapter 7

def fig_ui_flow(path: Path):
    fig, ax = _canvas(9.5, 5.2)
    _box(ax, 1, 22, 11, 7, "Splash\n(model scan)", fc=FILL_A, fs=7)
    _box(ax, 16, 20, 14, 11, "Main (home)\ntiles · language bar\nside menu", fc=FILL_B, fs=7, bold=True)
    _arrow(ax, (12, 25.5), (16, 25.5))
    targets = [(36, 44, "Camera"), (36, 35, "ImageImport\n(batch)"), (36, 26, "Pdf\n(range, format)"),
               (36, 17, "History"), (36, 8, "Settings\n(model report)"), (36, -1, "Translate\n(typed text)")]
    for x, y, t in targets:
        _box(ax, x, y, 14, 7, t, fc=FILL_E, fs=7)
        _arrow(ax, (30, 25.5), (36, y + 3.5), lw=0.8)
    _box(ax, 56, 40, 14, 7, "Processing\n(busy overlay)", fc=FILL_C, fs=7)
    _arrow(ax, (50, 47.5), (56, 43.5))
    _arrow(ax, (50, 38.5), (56, 43.5))
    _box(ax, 76, 40, 14, 7, "Result\nimage · text · TTS", fc=FILL_D, fs=7)
    _arrow(ax, (70, 43.5), (76, 43.5))
    _box(ax, 56, 26, 14, 7, "PdfJob\n(page loop)", fc=FILL_C, fs=7)
    _arrow(ax, (50, 29.5), (56, 29.5))
    _box(ax, 76, 26, 14, 7, "exports/\nPDF · DOCX · TXT", fc=FILL_D, fs=7)
    _arrow(ax, (70, 29.5), (76, 29.5))
    _box(ax, 56, 11, 14, 7, "Language\npicker (EN/JA/ZH)", fc=FILL_A, fs=7)
    _arrow(ax, (30, 21), (56, 14.5), ls="--", lw=0.8)
    _arrow(ax, (50, 20.5), (76, 40), ls="--", lw=0.8)
    ax.text(58, 20, "history item reopens result", fontsize=6.5, color=MUTED)
    _save(fig, path)


def fig_nav_menu(path: Path):
    fig, axs = plt.subplots(1, 2, figsize=(8.8, 5.0))
    W, H = 360, 640   # dp, a typical phone portrait viewport
    TB = 56           # toolbar_height
    RAIL, RAIL_X = 40, 104
    for ax, expanded in ((axs[0], False), (axs[1], True)):
        ax.set_xlim(0, W)
        ax.set_ylim(0, H)
        ax.invert_yaxis()
        ax.set_aspect("equal")
        ax.axis("off")
        ax.add_patch(Rectangle((0, 0), W, H, fc="#F4F5F8", ec=INK, lw=1.2))
        ax.add_patch(Rectangle((0, 0), W, TB, fc="white", ec="#D5D9E0"))
        ax.text(12, TB / 2, "falcon", va="center", fontsize=8, fontweight="bold")
        ax.add_patch(Rectangle((W - 4 - 28 - 28, TB / 2 - 14), 28, 28, fc="#EEF0F4", ec="#D5D9E0"))
        ax.text(W - 4 - 28 - 14, TB / 2, "i", ha="center", va="center", fontsize=8)
        ax.add_patch(Rectangle((W - 4 - 28, TB / 2 - 14), 28, 28, fc=FILL_B, ec=ACCENT))
        ax.text(W - 4 - 14, TB / 2, "≡" if not expanded else "⇤", ha="center", va="center", fontsize=10,
                color=ACCENT)
        cx0 = RAIL + 16
        cw = W - cx0 - 16
        ax.add_patch(Rectangle((cx0, TB + 16), cw, 110, fc=FILL_A, ec="#D5D9E0"))
        ax.text(cx0 + 8, TB + 16 + 100, "banner (110dp)", fontsize=6.5, color=MUTED)
        tw = (cw - 12) / 2
        y0 = TB + 16 + 110 + 16
        for r in range(2):
            for c_ in range(2):
                x = cx0 + c_ * (tw + 12)
                y = y0 + r * (70 + 12)
                colr = [FILL_B, FILL_E, FILL_C, FILL_D][r * 2 + c_]
                ax.add_patch(Rectangle((x, y), tw, 70, fc=colr, ec="#D5D9E0"))
                ax.text(x + tw / 2, y + 35, "tile ≥70dp", ha="center", va="center", fontsize=6.3, color=MUTED)
        yl = y0 + 2 * 82 + 4
        ax.add_patch(Rectangle((cx0, yl), cw, 44, fc="white", ec="#D5D9E0"))
        ax.text(cx0 + cw / 2, yl + 22, "language bar", ha="center", va="center", fontsize=6.5, color=MUTED)
        ax.text(cx0, yl + 70, "tiles wrap to compact height",
                fontsize=6.2, color=MUTED, va="top")
        rail_w = RAIL_X if expanded else RAIL
        if expanded:
            ax.add_patch(Rectangle((0, TB), W, H - TB, fc="black", alpha=0.70 * 0.55, ec="none", zorder=4))
        ax.add_patch(Rectangle((0, TB), rail_w, H - TB, fc="white", ec="#C9CED8", lw=1.0, zorder=5))
        names = ["Home", "Image", "PDF", "History", "Settings"]
        for i, nm in enumerate(names):
            y = TB + 8 + i * 32
            ax.add_patch(Rectangle((4, y + 1), rail_w - 8, 30, fc=FILL_B if i == 0 else "white", ec="none", zorder=6))
            ax.add_patch(plt.Circle((4 + 8 + 7.5, y + 16), 7.5, fc="#C9CED8", ec="none", zorder=7))
            if expanded:
                ax.text(4 + 8 + 15 + 8, y + 16, nm, va="center", fontsize=6.5, zorder=7)
        ax.annotate("", xy=(0, H - 20), xytext=(rail_w, H - 20), arrowprops=dict(arrowstyle="<->", color=ACCENT), zorder=8)
        ax.text(rail_w / 2, H - 28, f"{rail_w}dp", ha="center", fontsize=7, color=ACCENT, zorder=8)
        ax.set_title("(a) collapsed (initial state): icon rail, tooltips" if not expanded
                     else "(b) expanded over content with scrim;\nscrim tap, toggle or Back collapses", fontsize=8.5)
    fig.suptitle("Schematic of the home screen at 360×640 dp (phone tokens; tablet rail 52/140 dp)",
                 fontsize=8.5, color=MUTED)
    fig.tight_layout()
    _save(fig, path)


def fig_touch_tokens(path: Path):
    names = ["icon_button_small", "icon_button", "button_height", "row_min_height", "nav_item_height",
             "shutter_size", "tile_min_height"]
    phone = [24, 28, 30, 32, 32, 44, 70]
    tablet = [28, 32, 36, 38, 40, 54, 100]
    fig, ax = plt.subplots(figsize=(8.5, 3.0))
    y = np.arange(len(names))
    ax.barh(y - 0.18, phone, height=0.34, color=BLUE, label="values/ (phone)")
    ax.barh(y + 0.18, tablet, height=0.34, color=ORANGE, label="values-sw600dp/ (tablet)")
    ax.axvline(48, color=ACCENT, ls="--", lw=1)
    ax.text(49, len(names) - 0.4, "48dp platform guidance", fontsize=7, color=ACCENT)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7.5)
    ax.set_xlabel("dp (dimension tokens from the resource files)")
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    ax.set_title("Compact control tokens vs. 48 dp guidance (configuration values, not measurements)",
                 fontsize=8.5)
    _save(fig, path)


# ---------------------------------------------------------------- chapter 8

def fig_exp_design(path: Path):
    fig, ax = _canvas(9.5, 5.6)
    rqs = [("RQ1 Detection\nfaithfulness", "ICDAR 2015\nMLT-2019 zh/ja/ko", "P / R / H-mean\n@ IoU 0.5 · by angle",
            "TOST equivalence\npaired bootstrap"),
           ("RQ2 Recognition", "cropped words\n(same sets)", "word acc.\n1 − NED", "McNemar · bootstrap\n± classifier"),
           ("RQ3 Translation", "FLORES-200\ndevtest, 12 dirs", "BLEU · chrF\nCOMET", "paired bootstrap\nint8/fp32 · greedy/beam"),
           ("RQ4 Efficiency", "N pages ×\n3 quality levels", "p50/p90 latency\npeak PSS · load", "3 device tiers\nmedians + CIs"),
           ("RQ5 Rendering", "M images ×\n3 content types", "legibility · natural.\npreference · ρ", "CLMM (participant,\nimage random)")]
    heads = ["question", "data", "measures", "analysis"]
    for j, h in enumerate(heads):
        ax.text(8 + j * 22 + 9, 54, h, ha="center", fontsize=8, fontweight="bold", color=MUTED)
    fills = [FILL_B, FILL_E, FILL_C, FILL_D]
    for i, row in enumerate(rqs):
        y = 43 - i * 10.5
        for j, t in enumerate(row):
            _box(ax, 8 + j * 22, y, 18, 8.5, t, fc=fills[j], fs=6.8)
            if j < 3:
                _arrow(ax, (26 + j * 22, y + 4.25), (30 + j * 22, y + 4.25))
    _save(fig, path)


def fig_user_study(path: Path):
    fig, ax = _canvas(9.5, 4.0)
    conds = ["α=255\n(opaque)", "α=200\n+halo", "α=150\n+halo", "α=150\nno halo", "α=90\n+halo",
             "LaMa\n(off-device)"]
    for i, c in enumerate(conds):
        _box(ax, 2 + i * 15.5, 26, 13.5, 9, c, fc=FILL_D if i != 5 else FILL_A, fs=7)
    ax.text(48, 38.5, "rendering conditions (within subjects; full 4×2 grid available, core set shown)",
            ha="center", fontsize=7.5, color=MUTED)
    steps = ["consent +\ndemographics", "practice\n(2 images)", "rating block\nrandomised order", "pairwise\npreferences",
             "debrief +\nSUS / comments"]
    for i, s in enumerate(steps):
        _box(ax, 2 + i * 19, 5, 16, 9, s, fc=FILL_E, fs=7)
        if i < len(steps) - 1:
            _arrow(ax, (18 + i * 19, 9.5), (21 + i * 19, 9.5))
    ax.text(48, 17.5, "session flow per participant", ha="center", fontsize=7.5, color=MUTED)
    _save(fig, path)


# ------------------------------------------------------------------ driver

def build_all(out: Path) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    jobs = {
        "architecture": fig_architecture, "pipeline": fig_pipeline, "threading": fig_threading,
        "dataflow": fig_dataflow, "model_tree": fig_model_tree, "db_steps": fig_db_steps,
        "hull": fig_hull_geometry, "unclip": fig_unclip, "batching": fig_batching,
        "paragraph": fig_paragraph_rules, "viterbi": fig_viterbi, "decoder_cost": fig_decoder_cost,
        "pivot": fig_pivot, "highlight_union": fig_highlight_union, "compositing": fig_compositing,
        "attenuation": fig_attenuation, "textfit": fig_textfit, "ui_flow": fig_ui_flow,
        "nav_menu": fig_nav_menu, "touch_tokens": fig_touch_tokens, "exp_design": fig_exp_design,
        "user_study": fig_user_study,
    }
    paths = {}
    for name, fn in jobs.items():
        p = out / f"{name}.png"
        fn(p)
        paths[name] = p
    return paths
