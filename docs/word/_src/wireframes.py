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

    def button(self, x, y, w, h, label, fill=RED, color=TXT, outline=None, size=12):
        self.rect(x, y, w, h, fill=fill, outline=outline, r=8, width=1)
        self.text(x + w / 2, y + h / 2, label, size=size, color=color, bold=True, anchor="mm")

    def toolbar(self, title, action=None):
        # 56 dp bar; icon buttons are 28 dp touch areas around 20 dp glyphs.
        self.rect(0, 0, W, 56, fill=BG_SURFACE)
        self.icon(22, 28, "<", 20, TXT)
        self.text(44, 28, title, 17, TXT, True, "lm")
        if action:
            self.icon(W - 22, 28, action, 20, TXT)

    def status_bar(self):
        pass  # omitted: the system bar is not part of the design

    def callout(self, n, x, y):
        self.callouts.append((n, x, y))

    def save(self, name):
        for n, x, y in self.callouts:
            self.circle(x, y, 8, fill=CALLOUT, outline="#FFFFFF", width=1)
            self.text(x, y, str(n), 9, "#FFFFFF", True, "mm")
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
    # title bar (56 dp); right-hand icon buttons are 28 dp
    s.rect(0, 0, W, 56, fill=BG_SURFACE)
    s.rect(12, 14, 28, 28, fill=RED_DARK, r=6)
    s.text(50, 28, "OCR Translator", 17, TXT, True, "lm")
    s.icon(W - 56, 28, "i", 20, TXT2)
    s.icon(W - 22, 28, "=" if not expanded else "«", 20, TXT)
    # Content always leaves room for the collapsed rail (40 dp); the expanded
    # menu (104 dp) is drawn over it with a scrim, exactly as MainActivity does.
    rail = 40
    labels = ["Home", "Image", "PDF", "History", "Settings"]
    glyphs = ["H", "I", "P", "Hi", "S"]
    x0 = rail + 16
    cw = W - x0 - 16
    s.rect(x0, 72, cw, 110, fill="#3A0D14", r=14)
    s.text(x0 + 14, 142, "Scan · Recognize · Translate", 16, TXT, True)
    s.text(x0 + 14, 164, "Break language barriers…", 11, TXT2)
    top, th = 198, 70
    tw = (cw - 12) / 2
    tiles = [("Image OCR", RED, "C", "Capture or select image"), ("PDF OCR", BLUE, "P", "Scan PDF files"),
             ("Image Sequence", GREEN, "I", "Process multiple images"),
             ("History", ORANGE, "Hi", "View translation records")]
    for i, (lab, col, g, sub) in enumerate(tiles):
        tx = x0 + (i % 2) * (tw + 12)
        ty = top + (i // 2) * (th + 12)
        s.rect(tx, ty, tw, th, fill=col, r=12)
        s.icon(tx + 9 + 11, ty + 9 + 11, g, 22, TXT)
        s.text(tx + 9, ty + 38, lab, 14, TXT, True)
        s.text(tx + 9, ty + 56, sub, 10, TXT, anchor="la")
    y = top + 2 * th + 12 + 16
    s.rect(x0, y, cw, 52, fill=BG_SURFACE, r=14)
    s.text(x0 + 12, y + 26, "EN English", 14, TXT, anchor="lm")
    s.text(x0 + cw / 2, y + 26, "<>", 13, RED, True, "mm")
    s.text(x0 + cw - 12, y + 26, "Chinese ZH", 14, TXT, anchor="rm")
    by = y + 64
    s.button(x0, by, cw, 30, "Translation", fill=None, outline=TXT3, size=12)
    if expanded:
        region = (0, 56 * S, W * S, H * S)
        crop = s.img.crop(region)
        dark = Image.new("RGB", crop.size, "#000000")
        s.img.paste(Image.blend(crop, dark, 0.7), region[:2])
        s.dr = ImageDraw.Draw(s.img)
        rail = 104
    s.rect(0, 56, rail, H - 56, fill=BG_SURFACE)
    for i, (lab, g) in enumerate(zip(labels, glyphs)):
        iy = 64 + i * 35
        if i == 0:
            s.rect(4, iy, rail - 8, 32, fill=RED, r=8)
        s.icon(4 + 8 + 7.5, iy + 16, g, 15, TXT if i == 0 else TXT2)
        if expanded:
            s.text(4 + 8 + 15 + 8, iy + 16, lab, 12, TXT if i == 0 else TXT2, True, "lm")
    if expanded:
        s.text(rail + (W - rail) / 2, 420, "tap to collapse", 13, TXT2, anchor="mm")
        s.callout(2, rail + 4, 80); s.callout(8, rail + (W - rail) / 2, 396)
        s.callout(1, W - 22, 48)
    else:
        s.callout(1, W - 22, 48); s.callout(7, W - 56, 48); s.callout(2, rail + 4, 80)
        s.callout(3, x0 + 16, 82); s.callout(4, x0 + tw - 8, top + 8)
        s.callout(5, x0 + cw - 8, y + 6); s.callout(6, x0 + cw - 8, by + 4)
    s.save("02_home_expanded" if expanded else "02_home_collapsed")


def camera():
    s = Screen("Camera")
    s.rect(0, 0, W, H, fill="#20242C")
    s.rect(60, 200, 240, 240, outline=TXT, r=10, width=2)
    s.text(180, 470, "(camera preview)", 12, TXT2, anchor="mm")
    s.icon(24, 30, "<", 20, TXT)
    s.text(46, 30, "Camera OCR", 17, TXT, True, "lm")
    s.icon(W - 56, 30, "F", 20, TXT)
    s.icon(W - 22, 30, "I", 20, TXT)
    s.rect(0, 660, W, 100, fill="#000000")
    s.circle(80, 706, 14, fill="#2A2F3A"); s.text(80, 706, "I", 11, TXT, True, "mm")
    s.circle(180, 706, 22, fill=TXT, outline=RED, width=3)
    s.circle(280, 706, 14, fill="#2A2F3A"); s.text(280, 706, "A", 11, TXT, True, "mm")
    s.callout(1, 24, 52); s.callout(2, W - 56, 52); s.callout(3, W - 22, 52)
    s.callout(4, 60, 200); s.callout(5, 80, 682); s.callout(6, 180, 674); s.callout(7, 280, 682)
    s.save("03_camera")


def image_import():
    s = Screen("Import")
    s.toolbar("Image Import")
    for i in range(12):
        x = 12 + (i % 3) * 114
        y = 66 + (i // 3) * 114
        s.rect(x, y, 108, 108, fill=BG_HIGH, r=8)
        if i in (0, 1, 4):
            s.rect(x, y, 108, 108, outline=RED, r=8, width=3)
            s.circle(x + 92, y + 16, 10, fill=RED); s.text(x + 92, y + 16, "✓", 11, TXT, True, "mm")
    s.rect(0, 710, W, 50, fill=BG_SURFACE)
    s.button(16, 720, 110, 30, "Select images", fill=BG_ELEV)
    s.text(140, 735, "3 images selected", 12, TXT2, anchor="lm")
    s.button(284, 720, 60, 30, "Next")
    s.callout(1, 22, 48); s.callout(2, 110, 72); s.callout(3, 20, 716); s.callout(4, 150, 718); s.callout(5, 340, 716)
    s.save("04_image_import")


def result():
    s = Screen("Result")
    s.toolbar("Translation Result")
    s.rect(0, 56, W, 380, fill="#D8D2C4")
    for i in range(7):
        y = 90 + i * 44
        s.rect(40, y, 260 - (i % 3) * 40, 26, fill="#EEE8DA", r=6)
        s.text(48, y + 13, "Translated text line", 12, "#222222", anchor="lm")
    s.rect(W - 86, 66, 74, 22, fill=BG_SURFACE, r=11)
    s.text(W - 49, 77, "JA → EN", 11, TXT, True, "mm")
    s.text(16, 452, "SOURCE LANGUAGE", 11, TXT2, True)
    s.rect(16, 470, W - 32, 80, fill=BG_SURFACE, r=10)
    s.text(28, 486, "原文テキスト…", 13, TXT)
    s.text(16, 566, "TARGET LANGUAGE", 11, TXT2, True)
    s.rect(16, 584, W - 32, 120, fill=BG_SURFACE, outline=DIVIDER, r=10)
    s.text(28, 600, "Editable translation…", 13, TXT)
    bw = (W - 32 - 16) / 3
    s.button(16, 718, bw, 30, "Speak", fill=BG_ELEV)
    s.button(16 + bw + 8, 718, bw, 30, "Show original", fill=BG_ELEV)
    s.button(16 + 2 * (bw + 8), 718, bw, 30, "Save")
    s.callout(1, 22, 48); s.callout(2, 180, 250); s.callout(3, W - 90, 66); s.callout(4, W - 28, 478)
    s.callout(5, W - 28, 592); s.callout(6, 22, 716); s.callout(7, 136, 716); s.callout(8, 252, 716)
    s.save("05_result")


def language():
    s = Screen("Language")
    s.toolbar("Language Settings")
    s.rect(0, 56, W, 48, fill=BG_SURFACE)
    s.text(90, 80, "Source Language", 14, TXT, True, "mm")
    s.text(270, 80, "Target Language", 14, TXT2, anchor="mm")
    s.rect(0, 100, 180, 4, fill=RED)
    s.rect(16, 118, W - 32, 44, fill=BG_HIGH, r=12)
    s.text(40, 140, "Search language…", 14, TXT3, anchor="lm")
    rows = [("GB", "English", None, True), ("JP", "Japanese (日本語)", None, False),
            ("CN", "Chinese (中文)", "via English — slower, lower quality", False)]
    for i, (f, name, note, sel) in enumerate(rows):
        y = 176 + i * 68
        s.rect(16, y, W - 32, 60, fill=BG_SURFACE, r=12)
        s.text(40, y + 30, f, 16, TXT, True, "lm")
        s.text(84, y + (20 if note else 30), name, 15, TXT, anchor="lm")
        if note:
            s.text(84, y + 42, note, 11, ORANGE, anchor="lm")
        if sel:
            s.circle(W - 44, y + 30, 10, fill=RED); s.text(W - 44, y + 30, "✓", 11, TXT, True, "mm")
    s.callout(1, 20, 66); s.callout(2, 24, 124); s.callout(3, 24, 182); s.callout(4, W - 28, 318); s.callout(5, W - 28, 182)
    s.save("06_language")


def pdf():
    s = Screen("PDF")
    s.toolbar("PDF OCR")
    s.rect(16, 72, W - 32, 76, fill=BG_SURFACE, outline=DIVIDER, r=14)
    s.icon(48, 110, "P", 30, RED)
    s.text(76, 98, "report.pdf", 15, TXT, True)
    s.text(76, 120, "2.4 MB · 12 pages", 12, TXT2)
    s.icon(W - 40, 110, "×", 24, TXT2)
    for i, (k, v) in enumerate([("Page Range", "All Pages"), ("Output Format", "PDF")]):
        y = 162 + i * 40
        s.rect(16, y, W - 32, 34, fill=BG_SURFACE, r=8)
        s.text(30, y + 17, k, 14, TXT, anchor="lm")
        s.text(W - 40, y + 17, v, 13, TXT2, anchor="rm")
    s.rect(16, 252, W - 32, 52, fill=BG_SURFACE, r=14)
    s.text(36, 278, "EN  English", 14, TXT, anchor="lm"); s.text(W - 36, 278, "Chinese  ZH", 14, TXT, anchor="rm")
    s.button(16, 318, W - 32, 30, "Start OCR")
    s.text(180, 366, "Supported formats: PDF, JPG, PNG, BMP…", 11, TXT3, anchor="mm")
    s.rect(16, 384, W - 32, 150, fill=BG_SURFACE, r=10)
    s.text(28, 400, "Saved …/exports/translated_….pdf", 11, TXT2)
    s.callout(1, 22, 78); s.callout(2, W - 24, 96); s.callout(3, 22, 166); s.callout(4, 22, 206)
    s.callout(5, 22, 258); s.callout(6, 22, 322); s.callout(7, 22, 390)
    s.save("07_pdf")


def history():
    s = Screen("History")
    s.toolbar("History", action="Del")
    for i in range(8):
        y = 64 + i * 72
        s.rect(16, y, W - 32, 64, fill=BG_SURFACE, r=12)
        s.icon(44, y + 32, ["I", "P", "T"][i % 3], 22, TXT2)
        s.text(72, y + 20, "First line of recognised text…", 14, TXT)
        s.text(72, y + 44, "JA → EN", 11, RED, True)
        s.text(W - 28, y + 44, "2026-09-25 10:4" + str(i), 11, TXT3, anchor="ra")
    s.callout(1, W - 22, 48); s.callout(2, 22, 70); s.callout(3, 150, 118)
    s.save("08_history")


def settings():
    s = Screen("Settings")
    s.toolbar("Settings")
    y = 68
    groups = [("GENERAL", [("OCR Language", "Auto"), ("Image Quality", "HIGH"), ("Auto Translation", "switch")]),
              ("TRANSLATION", [("Default Source Language", "English"), ("Default Target Language", "Chinese")]),
              ("OTHER", [("Installed Models", "3 / 4"), ("About", "v1.0"), ("Help & Feedback", "")])]
    n = 1
    for g, rows in groups:
        s.text(16, y, g, 11, TXT2, True); y += 20
        for k, v in rows:
            s.rect(0, y, W, 32, fill=BG_SURFACE)
            s.icon(24, y + 16, "•", 14, TXT2)
            s.text(44, y + 16, k, 14, TXT, anchor="lm")
            if v == "switch":
                s.rect(W - 56, y + 7, 34, 18, fill=RED, r=9); s.circle(W - 31, y + 16, 7, fill=TXT)
            else:
                s.text(W - 28, y + 16, v, 12, TXT2, anchor="rm")
            s.callout(n, W - 10, y + 8); n += 1
            y += 33
        y += 12
    s.save("09_settings")


def translate():
    s = Screen("Translate")
    s.toolbar("Translation")
    s.rect(16, 72, W - 32, 52, fill=BG_SURFACE, r=14)
    s.text(36, 98, "EN  English", 14, TXT, anchor="lm"); s.text(W - 36, 98, "Japanese  JA", 14, TXT, anchor="rm")
    s.rect(16, 138, W - 32, 170, fill=BG_SURFACE, outline=DIVIDER, r=12)
    s.text(28, 154, "Enter text to translate", 14, TXT3)
    s.icon(W - 38, 288, "Cp", 20, TXT2)
    s.text(W - 60, 288, "0/500", 11, TXT3, anchor="rm")
    s.button(16, 320, W - 32, 30, "Translate")
    s.rect(16, 364, W - 32, 190, fill=BG_HIGH, r=12)
    s.text(28, 380, "Japanese (日本語)", 12, TXT2, True)
    s.icon(W - 38, 386, "Cp", 20, TXT2)
    s.text(28, 414, "Translated text appears here", 14, TXT)
    s.text(28, 566, "via English — slower, lower quality", 11, ORANGE)
    s.callout(1, 22, 78); s.callout(2, 22, 144); s.callout(3, W - 16, 274); s.callout(4, 22, 324)
    s.callout(5, 22, 370); s.callout(6, W - 16, 372); s.callout(7, 22, 562)
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
