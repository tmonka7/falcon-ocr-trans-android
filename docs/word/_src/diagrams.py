"""Box-and-arrow diagrams for the System Design Document.

    python docs/word/_src/diagrams.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "figures" / "design"
FONTS = Path("C:/Windows/Fonts")
RED = "#A81515"
INK = "#1F232B"
MUTED = "#5F6778"
FILL = "#F4F5F8"
FILL2 = "#FBEAEA"
FILL3 = "#EAF1FB"


def f(size, bold=False):
    return ImageFont.truetype(str(FONTS / ("arialbd.ttf" if bold else "arial.ttf")), size)


class Canvas:
    def __init__(self, w, h):
        self.img = Image.new("RGB", (w, h), "#FFFFFF")
        self.d = ImageDraw.Draw(self.img)

    def box(self, x, y, w, h, title, lines=(), fill=FILL, edge=RED, tsize=22):
        self.d.rounded_rectangle([x, y, x + w, y + h], 12, fill=fill, outline=edge, width=3)
        self.d.text((x + w / 2, y + 14), title, fill=INK, font=f(tsize, True), anchor="ma")
        for i, line in enumerate(lines):
            self.d.text((x + w / 2, y + 22 + tsize + i * 22), line, fill=MUTED, font=f(17), anchor="ma")
        return (x, y, w, h)

    def arrow(self, x1, y1, x2, y2, label="", color=MUTED, width=3, dashed=False):
        if dashed:
            n = int(math.hypot(x2 - x1, y2 - y1) // 14)
            for i in range(0, n, 2):
                a, b = i / n, min(1, (i + 1) / n)
                self.d.line([x1 + (x2 - x1) * a, y1 + (y2 - y1) * a, x1 + (x2 - x1) * b, y1 + (y2 - y1) * b],
                            fill=color, width=width)
        else:
            self.d.line([x1, y1, x2, y2], fill=color, width=width)
        ang = math.atan2(y2 - y1, x2 - x1)
        for s in (0.45, -0.45):
            self.d.line([x2, y2, x2 - 16 * math.cos(ang + s), y2 - 16 * math.sin(ang + s)], fill=color, width=width)
        if label:
            self.d.text(((x1 + x2) / 2 + 6, (y1 + y2) / 2 - 22), label, fill=color, font=f(16), anchor="la")

    def text(self, x, y, s, size=18, color=INK, bold=False, anchor="la"):
        self.d.text((x, y), s, fill=color, font=f(size, bold), anchor=anchor)

    def save(self, name):
        OUT.mkdir(parents=True, exist_ok=True)
        self.img.save(OUT / f"{name}.png", optimize=True)


def architecture():
    c = Canvas(1600, 1000)
    c.text(800, 20, "Layered architecture (packages under com.falcon.ocrtrans)", 26, INK, True, "ma")
    c.box(60, 80, 1480, 150, "ui  —  Activities and widgets", [
        "Splash · Main (tiles, collapsible side menu) · Camera · ImageImport · Pdf · Result · Language · History · Settings · Translate",
        "BaseActivity (toolbar, busy overlay, runInBackground)  ·  LanguageBar  ·  OptionRow  ·  Flags"], fill=FILL3)
    c.box(60, 290, 1480, 130, "engine  —  orchestration", [
        "Engines (singleton, one worker thread)  ·  TranslationPipeline  ·  ModelValidator / ModelPaths  ·  ScriptDetector  ·  ResultHolder"])
    xs = [60, 440, 820, 1200]
    c.box(xs[0], 480, 340, 210, "ocr", ["PaddleOcrEngine", "DbPostProcessor", "CtcDecoder · CharDict", "ImageOps · LineGrouper"], fill=FILL2)
    c.box(xs[1], 480, 340, 210, "mt", ["PivotTranslator", "MarianTranslator", "SpmEncoder · MtVocab", "MtConfig"], fill=FILL2)
    c.box(xs[2], 480, 340, 210, "render", ["LayoutRenderer", "(highlight + halo)", "TextFitter"], fill=FILL2)
    c.box(xs[3], 480, 340, 210, "pdf / data", ["PdfPageSource · PdfJob", "DocxWriter", "Prefs · HistoryStore"], fill=FILL2)
    c.box(60, 750, 1480, 90, "core  —  Lang (USER_FACING) · Quad · TextLine · Paragraph · OcrResult", [], fill=FILL)
    c.box(60, 880, 700, 90, "ONNX Runtime · CameraX · PdfRenderer", [], fill="#FFFFFF", edge=MUTED, tsize=20)
    c.box(840, 880, 700, 90, "assets/model (PP-OCR, OPUS-MT int8)", [], fill="#FFFFFF", edge=MUTED, tsize=20)
    for x in (230, 610, 990, 1370):
        c.arrow(x, 420, x, 480)
    c.arrow(800, 230, 800, 290)
    c.save("arch_layers")


def pipeline():
    c = Canvas(1700, 520)
    c.text(850, 16, "Per-page processing pipeline (TranslationPipeline.process)", 26, INK, True, "ma")
    steps = [("Detect", ["resize ≤ 640/960/1280", "DB map → boxes"]),
             ("Crop + cls", ["perspective crop", "flip if p>0.9"]),
             ("Recognise", ["batches of 6", "CTC, conf ≥ 0.5"]),
             ("Group", ["reading order", "paragraphs"]),
             ("Verify script", ["Auto mode only", "user-facing guess"]),
             ("Translate", ["OPUS-MT greedy", "pivot via EN"]),
             ("Render", ["highlight α=150", "fit + halo"])]
    w, gap = 205, 30
    for i, (t, lines) in enumerate(steps):
        x = 40 + i * (w + gap)
        c.box(x, 110, w, 170, t, lines, fill=FILL2 if i in (0, 1, 2) else FILL3 if i in (5,) else FILL)
        if i:
            c.arrow(x - gap, 195, x, 195)
    c.text(40, 330, "Inputs: bitmap, source, target, Options{translate, render, autoDetectSource, renderOptions}", 18, MUTED)
    c.text(40, 362, "Output: Result{ocr (lines, paragraphs, translations), rendered bitmap, detectedSource, elapsedMillis}", 18, MUTED)
    c.text(40, 410, "Re-recognition: if the script guess differs from the source AND is user-facing, recognise again with the guessed model.", 18, RED)
    c.text(40, 442, "Translate is skipped when Options.translate is false or source == target; render is skipped for DOCX/TXT PDF jobs.", 18, RED)
    c.save("pipeline")


def sequence_capture():
    c = Canvas(1600, 900)
    c.text(800, 16, "Sequence: capture → result → save", 26, INK, True, "ma")
    lanes = ["User", "CameraActivity", "Engines worker", "TranslationPipeline", "ResultActivity", "HistoryStore"]
    xs = [120 + i * 270 for i in range(len(lanes))]
    for x, name in zip(xs, lanes):
        c.box(x - 110, 60, 220, 60, name, [], tsize=19)
        c.d.line([x, 120, x, 870], fill="#C9CED8", width=2)
    msgs = [(0, 1, "tap shutter", 160), (1, 1, "takePicture → rotate", 210),
            (1, 2, "runInBackground(process)", 260), (2, 3, "process(bitmap, src, tgt)", 310),
            (3, 3, "detect · recognise · group", 360), (3, 3, "translate · render", 410),
            (3, 2, "Result", 460), (2, 1, "postToMain → onSuccess", 510),
            (1, 4, "ResultHolder.put; startActivity", 560), (0, 4, "edit · Save", 640),
            (4, 2, "runInBackground(save)", 690), (2, 5, "saveToAppStorage; insert", 740),
            (2, 4, "id → toast 'Saved to history'", 790)]
    RETURNS = {"Result", "postToMain → onSuccess", "id → toast 'Saved to history'"}
    for a, b, label, y in msgs:
        if a == b:
            c.d.rectangle([xs[a] - 8, y - 12, xs[a] + 8, y + 22], fill=FILL2, outline=RED)
            c.text(xs[a] + 16, y - 6, label, 16, MUTED)
        else:
            ret = label in RETURNS
            c.arrow(xs[a], y, xs[b], y, "", color=MUTED if ret else RED, dashed=ret)
            c.text(min(xs[a], xs[b]) + 14, y - 26, label, 16, INK)
    c.save("seq_capture")


def nav_state():
    c = Canvas(1500, 620)
    c.text(750, 16, "Side menu state machine (MainActivity)", 26, INK, True, "ma")
    c.box(120, 180, 420, 200, "COLLAPSED", ["rail 80 / 104 dp, icons only", "tooltips + content descriptions",
                                            "scrim GONE, Back callback off", "icon: menu"], fill=FILL3)
    c.box(960, 180, 420, 200, "EXPANDED", ["rail 208 / 280 dp over content", "labels visible, scrim shown",
                                           "Back callback on", "icon: menu_open"], fill=FILL2)
    c.arrow(540, 230, 960, 230, "")
    c.text(750, 196, "right-hand toggle", 18, RED, True, "ma")
    c.arrow(960, 330, 540, 330, "")
    c.text(750, 346, "toggle · tap scrim · Back", 18, MUTED, True, "ma")
    c.text(120, 440, "Animation: ValueAnimator on the rail width, 220 ms, decelerate; scrim alpha follows the width;", 18, MUTED)
    c.text(120, 470, "labels fade in over the last 40 % of an expansion and hide before a collapse starts.", 18, MUTED)
    c.text(120, 510, "Initial state: always COLLAPSED (not persisted), so the menu never covers Home on launch.", 18, RED)
    c.arrow(60, 280, 120, 280)
    c.d.ellipse([34, 268, 58, 292], fill=INK)
    c.save("nav_state")


if __name__ == "__main__":
    architecture(); pipeline(); sequence_capture(); nav_state()
    print("wrote", len(list(OUT.glob("*.png"))), "diagrams to", OUT)
