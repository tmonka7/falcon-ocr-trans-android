"""Builds the Screen Design Specification as .docx."""
from __future__ import annotations

from pathlib import Path

from docgen import Doc
from spec_data import DATE, DOC_IDS, PRODUCT, SCREENS, VERSION

HERE = Path(__file__).resolve().parent
SCR = HERE / "figures" / "screens"
OUT = HERE.parent / "03_Screen_Design_Specification.docx"


def build() -> Path:
    d = Doc(title="Screen Design Specification", subtitle=PRODUCT, doc_id=DOC_IDS["sds"],
            version=VERSION, status="Baseline draft", date=DATE)
    d.cover()
    d.revision_history([
        ("1.0", DATE, "[Author]", "All ten screens; large screen-relative controls; collapsible side menu "
                                  "with right-hand toggle; Korean removed from language lists."),
    ])
    d.toc()

    d.h(1, "1. Introduction")
    d.p("This document specifies every screen of the application: layout, components, sizes, "
        "behaviour, navigation and messages. Requirement IDs refer to FOT-SRS-001. Wireframes are "
        "schematic: they show structure, proportion and numbering on a 360 × 760 dp phone in the "
        "app's dark theme, not final artwork. Red numbered markers match the component tables.")
    d.note("Sizes are written *phone / tablet*. Tablet values apply when the smallest screen width is at "
           "least 600 dp (resource qualifier sw600dp).")

    d.h(1, "2. Common Design Rules")
    d.h(2, "2.1 Screen flow")
    d.figure(SCR / "00_screen_flow.png", "Screen flow", 16)
    d.h(2, "2.2 Colour palette")
    d.table(["Token", "Value", "Use"], [
        ("bg_base", "#070A12", "Window background"),
        ("bg_surface", "#101726", "Toolbars, side menu, cards"),
        ("bg_surface_high / bg_elevated", "#18202F / #1E2838", "Search field, tonal buttons"),
        ("divider", "#26314A", "Outlines, separators"),
        ("brand_red / brand_red_dark", "#E02020 / #A81515", "Primary buttons, selected menu item, accents"),
        ("tile_red / blue / green / orange", "#DC2626 / #1D6FE0 / #10A45B / #E8880C", "Home tiles"),
        ("text_primary / secondary / tertiary", "#FFFFFF / #9BA6BD / #66738C", "Text hierarchy"),
        ("status_warn", "#E8880C", "Model warning, pivot notes"),
        ("scrim", "#B3000000 (70 % black)", "Dims content behind the expanded side menu"),
    ], widths_cm=[5.2, 5.2, 5.9], caption="Colour tokens")
    d.h(2, "2.3 Size tokens")
    d.p("Controls are deliberately large and scale with the screen (FR-22). The home tiles also stretch "
        "to share the free height.")
    d.table(["Token", "Phone", "Tablet", "Applies to"], [
        ("button_height", "60 dp", "72 dp", "Primary (red), tonal and outlined buttons"),
        ("button_text", "18 sp", "22 sp", "Button labels"),
        ("icon_button", "56 dp", "64 dp", "Toolbar back/action, camera top bar, gallery/auto, menu toggle, model status"),
        ("icon_button_small", "48 dp", "56 dp", "Copy, clear, swap (minimum touch target)"),
        ("shutter_size", "88 dp", "108 dp", "Camera shutter"),
        ("row_min_height", "64 dp", "76 dp", "Settings and PDF option rows"),
        ("toolbar_height", "64 dp", "72 dp", "All toolbars"),
        ("tile_min_height", "140 dp", "200 dp", "Home tiles (grow to fill)"),
        ("tile_icon / tile_title / tile_subtitle", "44 dp / 20 sp / 13 sp", "64 dp / 28 sp / 17 sp", "Home tile content"),
        ("banner_height", "110 dp", "150 dp", "Home banner"),
        ("nav_rail_width", "80 dp", "104 dp", "Side menu, collapsed"),
        ("nav_rail_expanded_width", "208 dp", "280 dp", "Side menu, expanded"),
        ("nav_item_height / nav_icon / nav_label", "64 dp / 30 dp / 16 sp", "80 dp / 38 dp / 20 sp", "Side-menu items"),
        ("gutter / gutter_small", "16 / 12 dp", "24 / 16 dp", "Spacing"),
    ], widths_cm=[4.8, 3.2, 3.2, 5.1], caption="Size tokens", font_size=8.5)
    d.h(2, "2.4 Interaction rules")
    d.table(["Pattern", "Rule"], [
        ("Long operations", "Blocking overlay 'Working…' with optional detail ('Page i of n'); input ignored while shown."),
        ("Errors", "Toast with the underlying message, or 'Something went wrong'; no crash."),
        ("Destructive actions", "Confirmation dialog with Cancel / Delete."),
        ("Choices from a short list", "Alert dialog list (image quality, page range, output format)."),
        ("Back", "Closes the screen; on Home with the menu expanded it collapses the menu first; during a PDF job it cancels the job."),
        ("Icons without text", "Content description always; tooltip for collapsed side-menu items."),
        ("Languages shown", "English, Japanese, Chinese only (Korean is withheld, FR-21)."),
    ], widths_cm=[4.3, 12], caption="Interaction rules")

    d.h(1, "3. Screen Specifications")
    for scr in SCREENS:
        d.h(2, f"{scr['id']} {scr['name']}")
        d.kv_table([
            ("Screen ID", scr["id"]),
            ("Activity / layout", f"{scr['activity']} / {scr['layout']}"),
            ("Purpose", scr["purpose"]),
            ("Entry", scr["entry"]),
            ("Exit", scr["exit"]),
            ("Requirements", ", ".join(scr["reqs"])),
        ], widths_cm=(3.4, 12.9))
        if "image2" in scr:
            d.figure(SCR / scr["image"], f"{scr['name']} — side menu collapsed (default)", 6.8)
            d.figure(SCR / scr["image2"], f"{scr['name']} — side menu expanded over the content", 6.8)
        else:
            d.figure(SCR / scr["image"], f"{scr['name']} wireframe", 6.8)
        d.table(["No.", "Component", "Widget", "View ID", "Size (phone / tablet)", "Behaviour"],
                [(str(n), name, w, vid, size, beh) for n, name, w, vid, size, beh in scr["components"]],
                widths_cm=[1, 2.8, 2.6, 3.1, 2.7, 4.1], caption=f"{scr['id']} components", font_size=8)
        if scr["id"] == "SCR-02":
            d.h(3, "Side-menu behaviour")
            d.steps([
                "At launch the menu is collapsed: an 80 dp (104 dp) rail of 30 dp (38 dp) icons; Home is highlighted in red.",
                "The **right-hand button** at the end of the title bar (callout 1) expands the menu to 208 dp (280 dp) "
                "in 220 ms. The menu slides **over** the content, which dims behind a 70 % scrim; labels fade in near the end.",
                "The same button (now showing the 'menu open' icon), a tap on the dimmed area, or the Back key collapses it.",
                "Choosing an item opens its screen whether the menu is collapsed or expanded.",
                "Collapsed icons show their label as a tooltip on long-press and are announced by TalkBack.",
            ])
            d.h(3, "Large-button layout")
            d.p("Banner, tile rows, language bar and the Translation button are stacked in a column that is at least "
                "as tall as the screen. The two tile rows take equal shares of the remaining height, so on a tall "
                "phone the tiles are much larger than their 140 dp minimum; on a short or landscape screen they "
                "keep the minimum and the column scrolls.")
        if scr["id"] == "SCR-05":
            d.h(3, "Rendered page appearance")
            d.p("Each translated paragraph sits on a faint, soft-edged highlight in the paper colour sampled from the "
                "page (alpha 150/255): the paper texture remains visible and the original text shows only as a faint "
                "ghost. The translation has no opaque background of its own; it is drawn in the sampled ink colour "
                "with a thin paper-coloured halo, at the largest size that fits, rotated to the paragraph's angle.")

    d.h(1, "4. Message Catalogue")
    d.table(["String resource", "Text", "Where"], [
        ("working", "Working…", "Busy overlay, splash"),
        ("result_saved", "Saved to history", "SCR-05 toast"),
        ("result_no_text", "No text found in this image", "SCR-05"),
        ("import_none_selected", "Select at least one image", "SCR-04 toast"),
        ("pdf_progress", "Page %1$d of %2$d", "Overlay detail (SCR-04, SCR-07)"),
        ("pdf_done", "Saved %1$s", "SCR-07 result"),
        ("lang_pivoted", "via English — slower, lower quality", "SCR-06, SCR-10"),
        ("lang_unavailable", "Model not installed", "SCR-06"),
        ("history_clear_confirm", "Delete all saved translations? This cannot be undone.", "SCR-08 dialog"),
        ("history_cleared", "History cleared", "SCR-08 toast"),
        ("translate_copied", "Copied to clipboard", "SCR-10 toast"),
        ("camera_permission_rationale", "Camera access is needed to scan text…", "SCR-03 toast"),
        ("camera_unavailable", "Camera unavailable on this device", "SCR-03 toast"),
        ("error_models_missing (+ _hint)", "Models are not installed / Run tools/fetch_models.sh…", "SCR-01, SCR-02, SCR-09"),
        ("error_generic", "Something went wrong", "Anywhere"),
        ("nav_expand / nav_collapse", "Expand menu / Collapse menu", "SCR-02 toggle description"),
    ], widths_cm=[4.6, 7.4, 4.3], caption="User-visible messages", font_size=8.5)
    return d.save(OUT)


if __name__ == "__main__":
    print(build())
