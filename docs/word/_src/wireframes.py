"""Schematic wireframes of every screen, for the Screen Design Specification.

Coordinates are in dp on a 360 x 760 dp phone (tablet sizes differ only in the
dimension tokens). Numbered red callouts match the component tables in
build_screen_design.py. Colours are the app's own tokens from colors.xml.

    python docs/word/_src/wireframes.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "figures" / "screens"
S = 2                        # pixels per dp in the output image
W, H = 360, 760

BG_BASE = "#070A12"
BG_SURFACE = "#101726"
BG_HIGH = "#18202F"
BG_ELEV = "#1E2838"
DIVIDER = "#26314A"
RED = "#E02020"
RED_DARK = "#A81515"
BLUE = "#1D6FE0"
GREEN = "#10A45B"
ORANGE = "#E8880C"
TXT = "#FFFFFF"
TXT2 = "#9BA6BD"
TXT3 = "#66738C"
CALLOUT = "#FF3B30"

FONT_DIR = Path("C:/Windows/Fonts")


def font(size: float, bold: bool = False, cjk: bool = False) -> ImageFont.FreeTypeFont:
    name = ("YuGothB.ttc" if bold else "YuGothM.ttc") if cjk else ("arialbd.ttf" if bold else "arial.ttf")
    try:
        return ImageFont.truetype(str(FONT_DIR / name), int(size * S))
    except OSError:
        return ImageFont.load_default()


class Screen:
    def __init__(self, title: str):
        self.title = title
        self.img = Image.new("RGB", (W * S, H * S), BG_BASE)
        self.dr = ImageDraw.Draw(self.img)
        self.callouts: list[tuple[int, float, float]] = []

    # primitives, all in dp
    def rect(self, x, y, w, h, fill=None, outline=None, r=0, width=1):
        box = [x * S, y * S, (x + w) * S, (y + h) * S]
        if r:
            self.dr.rounded_rectangle(box, radius=r * S, fill=fill, outline=outline, width=width * S)
        else:
            self.dr.rectangle(box, fill=fill, outline=outline, width=width * S)

    def circle(self, cx, cy, rad, fill=None, outline=None, width=1):
        self.dr.ellipse([(cx - rad) * S, (cy - rad) * S, (cx + rad) * S, (cy + rad) * S],
                        fill=fill, outline=outline, width=width * S)

    def text(self, x, y, s, size=13, color=TXT, bold=False, anchor="la"):
        cjk = any(ord(ch) > 0x2E80 or ch == "✓" for ch in s)
        self.dr.text((x * S, y * S), s, fill=color, font=font(size, bold, cjk), anchor=anchor)

    def icon(self, cx, cy, glyph, size=24, color=TXT2):
        """An icon stand-in: a glyph in a faint square the icon's size."""
        self.rect(cx - size / 2, cy - size / 2, size, size, outline=color, r=4, width=1)
        self.text(cx, cy, glyph, size=size * 0.5, color=color, bold=True, anchor="mm")

    def button(self, x, y, w, h, label, fill=RED, color=TXT, outline=None, size=16):
        self.rect(x, y, w, h, fill=fill, outline=outline, r=14, width=1)
        self.text(x + w / 2, y + h / 2, label, size=size, color=color, bold=True, anchor="mm")

    def toolbar(self, title, action=None):
        self.rect(0, 0, W, 64, fill=BG_SURFACE)
        self.icon(32, 32, "<", 24, TXT)
        self.text(64, 32, title, 17, TXT, True, "lm")
        if action:
            self.icon(W - 32, 32, action, 24, TXT)

    def status_bar(self):
        pass  # omitted: the system bar is not part of the design

    def callout(self, n, x, y):
        self.callouts.append((n, x, y))

    def save(self, name):
        for n, x, y in self.callouts:
            self.circle(x, y, 10, fill=CALLOUT, outline="#FFFFFF", width=1)
            self.text(x, y, str(n), 11, "#FFFFFF", True, "mm")
        # thin device frame
        framed = Image.new("RGB", (W * S + 24, H * S + 24), "#C9CED8")
        framed.paste(self.img, (12, 12))
        OUT.mkdir(parents=True, exist_ok=True)
        framed.save(OUT / f"{name}.png", optimize=True)


# --------------------------------------------------------------------- screens

def splash():
    s = Screen("Splash")
    s.rect(140, 250, 80, 80, fill=RED_DARK, r=18)
    s.text(180, 290, "OCR", 20, TXT, True, "mm")
    s.text(180, 360, "OCR Translator", 22, TXT, True, "mm")
    s.text(180, 390, "Capture · Recognize · Translate", 13, TXT2, anchor="mm")
    s.circle(180, 470, 16, outline=RED, width=3)
    s.text(180, 510, "Working…", 12, TXT3, anchor="mm")
    s.callout(1, 120, 260); s.callout(2, 90, 360); s.callout(3, 150, 470); s.callout(4, 120, 510)
    s.save("01_splash")


def home(expanded: bool):
    s = Screen("Home")
    # title bar
    s.rect(0, 0, W, 64, fill=BG_SURFACE)
    s.rect(12, 18, 28, 28, fill=RED_DARK, r=6)
    s.text(50, 32, "OCR Translator", 17, TXT, True, "lm")
    s.icon(W - 84, 32, "i", 24, TXT2)
    s.icon(W - 28, 32, "=" if not expanded else "«", 24, TXT)
    # Content always leaves room for the collapsed rail; the expanded menu is
    # drawn over it with a scrim, exactly as MainActivity does.
    rail = 80
    labels = ["Home", "Image", "PDF", "History", "Settings"]
    glyphs = ["H", "I", "P", "Hi", "S"]
    x0 = rail + 16
    cw = W - x0 - 16
    s.rect(x0, 80, cw, 110, fill="#3A0D14", r=14)
    s.text(x0 + 14, 150, "Scan · Recognize · Translate", 15, TXT, True)
    s.text(x0 + 14, 172, "Break language barriers…", 11, TXT2)
    top, bottom = 206, 590
    th = (bottom - top - 12) / 2
    tw = (cw - 12) / 2
    tiles = [("Image OCR", RED, "C"), ("PDF OCR", BLUE, "P"),
             ("Sequence", GREEN, "I"), ("History", ORANGE, "Hi")]
    for i, (lab, col, g) in enumerate(tiles):
        tx = x0 + (i % 2) * (tw + 12)
        ty = top + (i // 2) * (th + 12)
        s.rect(tx, ty, tw, th, fill=col, r=14)
        s.icon(tx + 18 + 22, ty + th / 2 - 26, g, 44, TXT)
        s.text(tx + 18, ty + th / 2 + 16, lab, 16, TXT, True)
    s.rect(x0, 606, cw, 64, fill=BG_SURFACE, r=14)
    s.text(x0 + 12, 638, "EN English", 14, TXT, anchor="lm")
    s.text(x0 + cw / 2, 638, "<>", 15, RED, True, "mm")
    s.text(x0 + cw - 12, 638, "Chinese ZH", 14, TXT, anchor="rm")
    s.button(x0, 682, cw, 60, "Translation", fill=None, outline=TXT3, size=16)
    if expanded:
        # scrim over everything below the title bar
        region = (0, 64 * S, W * S, H * S)
        crop = s.img.crop(region)
        dark = Image.new("RGB", crop.size, "#000000")
        s.img.paste(Image.blend(crop, dark, 0.7), region[:2])
        s.dr = ImageDraw.Draw(s.img)
        rail = 208
    s.rect(0, 64, rail, H - 64, fill=BG_SURFACE)
    for i, (lab, g) in enumerate(zip(labels, glyphs)):
        y = 72 + i * 70
        if i == 0:
            s.rect(8, y, rail - 16, 64, fill=RED, r=12)
        s.icon(8 + 17 + 15, y + 32, g, 30, TXT if i == 0 else TXT2)
        if expanded:
            s.text(8 + 17 + 30 + 16, y + 32, lab, 16, TXT if i == 0 else TXT2, True, "lm")
    if expanded:
        s.text(rail + (W - rail) / 2, 420, "tap to collapse", 13, TXT2, anchor="mm")
        s.callout(2, rail - 6, 110); s.callout(8, rail + (W - rail) / 2, 390)
        s.callout(1, W - 28, 60)
    else:
        s.callout(1, W - 28, 60); s.callout(2, rail - 6, 110); s.callout(3, x0 + 20, 90)
        s.callout(4, x0 + tw - 10, top + 14); s.callout(5, x0 + cw - 10, 612)
        s.callout(6, x0 + cw - 10, 690); s.callout(7, W - 84, 60)
    s.save("02_home_expanded" if expanded else "02_home_collapsed")


def camera():
    s = Screen("Camera")
    s.rect(0, 0, W, H, fill="#20242C")
    s.rect(60, 200, 240, 240, outline=TXT, r=10, width=2)
    s.text(180, 470, "(camera preview)", 12, TXT2, anchor="mm")
    s.icon(32, 36, "<", 24, TXT)
    s.text(64, 36, "Camera OCR", 17, TXT, True, "lm")
    s.icon(W - 88, 36, "F", 24, TXT)
    s.icon(W - 32, 36, "I", 24, TXT)
    s.rect(0, 610, W, 150, fill="#000000")
    s.circle(70, 685, 28, fill="#2A2F3A"); s.text(70, 685, "I", 16, TXT, True, "mm")
    s.circle(180, 685, 44, fill=TXT, outline=RED, width=4)
    s.circle(290, 685, 28, fill="#2A2F3A"); s.text(290, 685, "A", 16, TXT, True, "mm")
    s.callout(1, 32, 60); s.callout(2, W - 88, 60); s.callout(3, W - 32, 60)
    s.callout(4, 60, 250); s.callout(5, 70, 650); s.callout(6, 180, 630); s.callout(7, 290, 650)
    s.save("03_camera")


def image_import():
    s = Screen("Import")
    s.toolbar("Image Import")
    for i in range(9):
        x = 12 + (i % 3) * 114
        y = 76 + (i // 3) * 114
        s.rect(x, y, 108, 108, fill=BG_HIGH, r=8)
        if i in (0, 1, 4):
            s.rect(x, y, 108, 108, outline=RED, r=8, width=3)
            s.circle(x + 92, y + 16, 10, fill=RED); s.text(x + 92, y + 16, "✓", 11, TXT, True, "mm")
    s.rect(0, 660, W, 100, fill=BG_SURFACE)
    s.button(16, 680, 150, 60, "Select images", fill=BG_ELEV, size=15)
    s.text(180, 710, "3 images selected", 12, TXT2, anchor="lm")
    s.button(262, 680, 82, 60, "Next", size=16)
    s.callout(1, 20, 84); s.callout(2, 110, 90); s.callout(3, 30, 676); s.callout(4, 180, 690); s.callout(5, 330, 676)
    s.save("04_image_import")


def result():
    s = Screen("Result")
    s.toolbar("Translation Result")
    s.rect(0, 64, W, 330, fill="#D8D2C4")
    for i in range(6):
        y = 100 + i * 42
        s.rect(40, y, 260 - (i % 3) * 40, 26, fill="#EEE8DA", r=6)
        s.text(48, y + 13, "Translated text line", 12, "#222222", anchor="lm")
    s.rect(W - 86, 76, 74, 24, fill=BG_SURFACE, r=12)
    s.text(W - 49, 88, "JA → EN", 11, TXT, True, "mm")
    s.text(16, 412, "SOURCE LANGUAGE", 11, TXT2, True)
    s.rect(16, 430, W - 32, 70, fill=BG_SURFACE, r=10)
    s.text(28, 446, "原文テキスト…", 13, TXT)
    s.text(16, 516, "TARGET LANGUAGE", 11, TXT2, True)
    s.rect(16, 534, W - 32, 110, fill=BG_SURFACE, outline=DIVIDER, r=10)
    s.text(28, 550, "Editable translation…", 13, TXT)
    bw = (W - 32 - 16) / 3
    s.button(16, 684, bw, 60, "Speak", fill=BG_ELEV, size=15)
    s.button(16 + bw + 8, 684, bw, 60, "Original", fill=BG_ELEV, size=15)
    s.button(16 + 2 * (bw + 8), 684, bw, 60, "Save", size=15)
    s.callout(1, 30, 80); s.callout(2, 180, 230); s.callout(3, W - 90, 76); s.callout(4, W - 30, 440)
    s.callout(5, W - 30, 544); s.callout(6, 40, 680); s.callout(7, 150, 680); s.callout(8, 270, 680)
    s.save("05_result")


def language():
    s = Screen("Language")
    s.toolbar("Language Settings")
    s.rect(0, 64, W, 52, fill=BG_SURFACE)
    s.text(90, 90, "Source Language", 14, TXT, True, "mm")
    s.text(270, 90, "Target Language", 14, TXT2, anchor="mm")
    s.rect(0, 112, 180, 4, fill=RED)
    s.rect(16, 132, W - 32, 52, fill=BG_HIGH, r=12)
    s.text(48, 158, "Search language…", 14, TXT3, anchor="lm")
    rows = [("GB", "English", None, True), ("JP", "Japanese (日本語)", None, False),
            ("CN", "Chinese (中文)", "via English — slower, lower quality", False)]
    for i, (f, name, note, sel) in enumerate(rows):
        y = 200 + i * 76
        s.rect(16, y, W - 32, 68, fill=BG_SURFACE, r=12)
        s.text(40, y + 34, f, 16, TXT, True, "lm")
        s.text(84, y + (24 if note else 34), name, 15, TXT, anchor="lm")
        if note:
            s.text(84, y + 48, note, 11, ORANGE, anchor="lm")
        if sel:
            s.circle(W - 44, y + 34, 12, fill=RED); s.text(W - 44, y + 34, "✓", 12, TXT, True, "mm")
    s.callout(1, 20, 76); s.callout(2, 24, 140); s.callout(3, 24, 206); s.callout(4, W - 30, 356); s.callout(5, W - 30, 206)
    s.save("06_language")


def pdf():
    s = Screen("PDF")
    s.toolbar("PDF OCR")
    s.rect(16, 80, W - 32, 90, fill=BG_SURFACE, outline=DIVIDER, r=14)
    s.icon(56, 125, "P", 36, RED)
    s.text(90, 112, "report.pdf", 15, TXT, True)
    s.text(90, 136, "2.4 MB · 12 pages", 12, TXT2)
    s.icon(W - 48, 125, "×", 32, TXT2)
    for i, (k, v) in enumerate([("Page Range", "All Pages"), ("Output Format", "PDF")]):
        y = 186 + i * 68
        s.rect(16, y, W - 32, 64, fill=BG_SURFACE, r=12)
        s.text(32, y + 32, k, 15, TXT, anchor="lm")
        s.text(W - 50, y + 32, v, 14, TXT2, anchor="rm")
    s.rect(16, 330, W - 32, 64, fill=BG_SURFACE, r=14)
    s.text(40, 362, "EN  English", 15, TXT, anchor="lm"); s.text(W - 40, 362, "Chinese  ZH", 15, TXT, anchor="rm")
    s.button(16, 412, W - 32, 60, "Start OCR")
    s.text(180, 494, "Supported formats: PDF, JPG, PNG, BMP…", 11, TXT3, anchor="mm")
    s.rect(16, 516, W - 32, 150, fill=BG_SURFACE, r=10)
    s.text(28, 532, "Saved …/exports/translated_….pdf", 11, TXT2)
    s.callout(1, 24, 86); s.callout(2, W - 30, 100); s.callout(3, 24, 192); s.callout(4, 24, 260)
    s.callout(5, 24, 336); s.callout(6, 24, 418); s.callout(7, 24, 522)
    s.save("07_pdf")


def history():
    s = Screen("History")
    s.toolbar("History", action="Del")
    for i in range(6):
        y = 72 + i * 80
        s.rect(16, y, W - 32, 72, fill=BG_SURFACE, r=12)
        s.icon(48, y + 36, ["I", "P", "T"][i % 3], 28, TXT2)
        s.text(80, y + 24, "First line of recognised text…", 14, TXT)
        s.text(80, y + 50, "JA → EN", 11, RED, True)
        s.text(W - 32, y + 50, "2026-09-25 10:4" + str(i), 11, TXT3, anchor="ra")
    s.callout(1, W - 32, 58); s.callout(2, 24, 78); s.callout(3, 150, 128)
    s.save("08_history")


def settings():
    s = Screen("Settings")
    s.toolbar("Settings")
    y = 76
    groups = [("GENERAL", [("OCR Language", "Auto"), ("Image Quality", "HIGH"), ("Auto Translation", "switch")]),
              ("TRANSLATION", [("Default Source Language", "English"), ("Default Target Language", "Chinese")]),
              ("OTHER", [("Installed Models", "3 / 4"), ("About", "v1.0"), ("Help & Feedback", "")])]
    n = 1
    for g, rows in groups:
        s.text(16, y, g, 11, TXT2, True); y += 22
        for k, v in rows:
            s.rect(0, y, W, 64, fill=BG_SURFACE)
            s.icon(32, y + 32, "•", 20, TXT2)
            s.text(60, y + 32, k, 15, TXT, anchor="lm")
            if v == "switch":
                s.rect(W - 64, y + 20, 44, 24, fill=RED, r=12); s.circle(W - 32, y + 32, 10, fill=TXT)
            else:
                s.text(W - 36, y + 32, v, 13, TXT2, anchor="rm")
            s.callout(n, W - 12, y + 10); n += 1
            y += 65
        y += 12
    s.save("09_settings")


def translate():
    s = Screen("Translate")
    s.toolbar("Translation")
    s.rect(16, 80, W - 32, 64, fill=BG_SURFACE, r=14)
    s.text(40, 112, "EN  English", 15, TXT, anchor="lm"); s.text(W - 40, 112, "Japanese  JA", 15, TXT, anchor="rm")
    s.rect(16, 158, W - 32, 170, fill=BG_SURFACE, outline=DIVIDER, r=12)
    s.text(28, 174, "Enter text to translate", 14, TXT3)
    s.icon(W - 44, 300, "Cp", 28, TXT2)
    s.text(W - 80, 300, "0/500", 11, TXT3, anchor="rm")
    s.button(16, 342, W - 32, 60, "Translate")
    s.rect(16, 418, W - 32, 190, fill=BG_HIGH, r=12)
    s.text(28, 434, "Japanese (日本語)", 12, TXT2, True)
    s.icon(W - 44, 440, "Cp", 28, TXT2)
    s.text(28, 470, "Translated text appears here", 14, TXT)
    s.text(28, 620, "via English — slower, lower quality", 11, ORANGE)
    s.callout(1, 24, 86); s.callout(2, 24, 166); s.callout(3, W - 20, 286); s.callout(4, 24, 348)
    s.callout(5, 24, 424); s.callout(6, W - 20, 426); s.callout(7, 24, 616)
    s.save("10_translate")


def screen_flow():
    """Navigation map between screens."""
    img = Image.new("RGB", (1500, 900), "#FFFFFF")
    dr = ImageDraw.Draw(img)
    f = ImageFont.truetype(str(FONT_DIR / "arialbd.ttf"), 22)
    f2 = ImageFont.truetype(str(FONT_DIR / "arial.ttf"), 17)
    boxes = {
        "SCR-01\nSplash": (60, 400), "SCR-02\nHome": (360, 400),
        "SCR-03\nCamera": (700, 90), "SCR-04\nImage Import": (700, 250),
        "SCR-07\nPDF OCR": (700, 410), "SCR-08\nHistory": (700, 570),
        "SCR-09\nSettings": (700, 730), "SCR-05\nResult": (1080, 170),
        "SCR-06\nLanguage": (1080, 480), "SCR-10\nTranslation": (1080, 730),
    }
    bw, bh = 230, 90
    centers = {}
    for label, (x, y) in boxes.items():
        dr.rounded_rectangle([x, y, x + bw, y + bh], 14, fill="#F4F5F8", outline="#A81515", width=3)
        a, b = label.split("\n")
        dr.text((x + bw / 2, y + 30), a, fill="#A81515", font=f2, anchor="mm")
        dr.text((x + bw / 2, y + 60), b, fill="#1F232B", font=f, anchor="mm")
        centers[label.split("\n")[0]] = (x, y)

    def arrow(a, b, text=""):
        (ax, ay), (bx, by) = centers[a], centers[b]
        x1, y1 = ax + bw, ay + bh / 2
        x2, y2 = bx, by + bh / 2
        if bx < ax:
            x1, x2 = ax, bx + bw
        dr.line([x1, y1, x2, y2], fill="#5F6778", width=3)
        import math
        ang = math.atan2(y2 - y1, x2 - x1)
        for d in (2.6, -2.6):
            dr.line([x2, y2, x2 - 16 * math.cos(ang + d / 6), y2 - 16 * math.sin(ang + d / 6)],
                    fill="#5F6778", width=3)
        if text:
            dr.text(((x1 + x2) / 2, (y1 + y2) / 2 - 14), text, fill="#5F6778", font=f2, anchor="mm")

    arrow("SCR-01", "SCR-02", "auto")
    for t in ("SCR-03", "SCR-04", "SCR-07", "SCR-08", "SCR-09"):
        arrow("SCR-02", t)
    arrow("SCR-03", "SCR-05", "capture")
    arrow("SCR-04", "SCR-05", "Next")
    arrow("SCR-07", "SCR-06")
    arrow("SCR-09", "SCR-06")
    # Translation is reached from Home's Translation button, drawn as a routed line
    # under the middle column so it does not cross the other boxes.
    hx, hy = centers["SCR-02"]
    tx, ty = centers["SCR-10"]
    dr.line([hx + bw / 2, hy + bh, hx + bw / 2, 870, tx - 40, 870, tx - 40, ty + bh / 2, tx, ty + bh / 2],
            fill="#A81515", width=3, joint="curve")
    dr.text((hx + bw / 2 + 10, 850), "Translation button", fill="#A81515", font=f2, anchor="lm")
    dr.text((360 + bw / 2, 520), "tiles · side menu ·\nlanguage bar · Translation",
            fill="#5F6778", font=f2, anchor="ma", align="center")
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / "00_screen_flow.png", optimize=True)


if __name__ == "__main__":
    splash(); home(False); home(True); camera(); image_import(); result()
    language(); pdf(); history(); settings(); translate(); screen_flow()
    print("wrote", len(list(OUT.glob("*.png"))), "images to", OUT)
