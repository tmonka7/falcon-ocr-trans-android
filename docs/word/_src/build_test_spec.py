"""Builds the Test Case Specification as .docx."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from docgen import Doc
from spec_data import (DATE, DOC_IDS, FR, KNOWN_ISSUES, NFR, PRODUCT, TC, UNIT_TESTS, VERSION,
                       req_title, tests_for)

OUT = Path(__file__).resolve().parents[1] / "04_Test_Case_Specification.docx"


def build() -> Path:
    d = Doc(title="Test Case Specification", subtitle=PRODUCT, doc_id=DOC_IDS["tcs"],
            version=VERSION, status="Ready for execution", date=DATE)
    d.cover()
    d.revision_history([
        ("1.0", DATE, "[Author]", f"{len(TC)} test cases covering every functional and non-functional requirement; "
                                  f"inventory of the {sum(len(v) for v in UNIT_TESTS.values())} JVM unit tests."),
    ])
    d.toc()

    d.h(1, "1. Introduction")
    d.p("This document specifies how the application is verified against FOT-SRS-001. Every "
        "requirement is covered by at least one test case, and every test case names the "
        "requirements it verifies.")
    d.note("None of the system test cases has been executed yet for this revision; the Result columns are "
           "intentionally blank. The recent UI and rendering changes have not been compiled or run on a device "
           "(KI-06). Performance and memory cases define how to measure; they do not state measured values.",
           "Status")

    d.h(1, "2. Test Strategy")
    d.table(["Level", "Scope", "Tooling", "Who / when"], [
        ("Unit (JVM)", "Pure-Java logic whose failures are silent: DB post-processing, CTC, SentencePiece, "
                       "script detection, language codes and gating, DOCX writing", "JUnit 4, ./gradlew test",
         "Developer; every change"),
        ("Integration", "Preferences, gating across components, developer toggles", "Device + adb, developer build", "Developer; per feature"),
        ("System", "End-to-end behaviour of every screen on a device", "Manual, device matrix", "Tester; per release candidate"),
        ("Acceptance", "Accessibility and usability walkthroughs", "TalkBack, Accessibility Scanner", "Tester + user representative"),
    ], widths_cm=[2.6, 6.6, 3.8, 3.3], caption="Test levels")
    d.h(2, "2.1 Test environment")
    d.table(["Item", "Specification"], [
        ("Build", "Debug APK with the full model tree (tools/fetch_models.sh), and one build without models (TC-19-1)"),
        ("Phone", "Android 7.0 (API 24) device or emulator — minimum supported"),
        ("Phone", "Mid-tier Android 13-15 phone, 360-412 dp wide — reference device for NFR-04"),
        ("Tablet", "Android tablet with smallest width >= 600 dp (sw600dp tokens)"),
        ("Test material", "Printed English, Japanese (with Kana) and Chinese pages; a Korean page; a two-column page; "
                          "a dark sign with light text; text over a photograph; a 12-page and a 20-page PDF; a corrupt image file"),
        ("Tools", "adb, logcat, Android Studio profiler, Accessibility Scanner, TalkBack"),
    ], widths_cm=[3, 13.3], caption="Test environment")
    d.h(2, "2.2 Entry and exit criteria")
    d.bullets([
        "Entry: the build compiles; ./gradlew test passes; the model tree validates (Installed Models shows 3 / 4).",
        "Exit: all High-priority cases pass; no open defect of severity Critical or Major; every Must requirement "
        "has at least one passing case; performance and memory measurements recorded.",
    ])
    d.h(2, "2.3 Pass / fail and severity")
    d.table(["Severity", "Definition"], [
        ("Critical", "Crash, data loss, or data leaves the device"),
        ("Major", "A Must requirement is not met; no workaround"),
        ("Minor", "Requirement met with a workaround, or a Should/Could requirement not met"),
        ("Cosmetic", "Visual or wording issue without functional impact"),
    ], widths_cm=[3, 13.3], caption="Defect severity")

    d.h(1, "3. Unit Test Inventory")
    d.p("These JVM tests already exist in app/src/test and run with `./gradlew test`.")
    rows = []
    for cls, methods in UNIT_TESTS.items():
        rows.append((cls, str(len(methods)), ", ".join(methods)))
    d.table(["Test class", "Count", "Test methods"], rows, widths_cm=[3.6, 1.4, 11.3],
            caption="Existing unit tests", font_size=8)
    d.p(f"Total: **{sum(len(v) for v in UNIT_TESTS.values())}** tests. The renderer, the side menu and the "
        "activities depend on android.graphics and the view system and are covered by system test cases instead.")

    d.h(1, "4. Test Case Summary")
    levels = Counter(t[3] for t in TC)
    prios = Counter(t[4] for t in TC)
    d.table(["Measure", "Count"], [
        ("Test cases", str(len(TC))),
        *[(f"Level: {k}", str(v)) for k, v in sorted(levels.items())],
        *[(f"Priority: {k}", str(v)) for k, v in sorted(prios.items())],
    ], widths_cm=[8, 8.3], caption="Test case counts")
    d.table(["ID", "Title", "Requirements", "Level", "Priority"],
            [(t[0], t[1], ", ".join(t[2]), t[3], t[4]) for t in TC],
            widths_cm=[2.2, 6.6, 3.5, 2.1, 1.9], caption="Test case index", font_size=8)

    d.h(1, "5. Test Cases")
    group = None
    for tid, title, reqs, level, prio, pre, steps, expected in TC:
        key = reqs[0]
        if key != group:
            group = key
            d.h(2, f"{key} {req_title(key)}")
        d.h(3, f"{tid} {title}")
        d.kv_table([
            ("Test case ID", tid),
            ("Requirements", ", ".join(f"{r} {req_title(r)}" for r in reqs)),
            ("Level / priority", f"{level} / {prio}"),
            ("Preconditions", pre),
            ("Steps", "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))),
            ("Expected result", expected),
            ("Actual result", ""),
            ("Result (Pass / Fail / Blocked)", ""),
            ("Tester / date / build", ""),
        ], widths_cm=(4.2, 12.1), font_size=8.5)

    d.h(1, "6. Requirements Coverage")
    rows = [(r[0], r[1], ", ".join(tests_for(r[0])) or "NONE") for r in FR]
    rows += [(r[0], r[1], ", ".join(tests_for(r[0])) or "review / inspection") for r in NFR]
    d.table(["Requirement", "Title", "Test cases"], rows, widths_cm=[2.3, 5, 9],
            caption="Coverage matrix", font_size=8)
    missing = [r[0] for r in FR if not tests_for(r[0])]
    d.p("Every functional requirement is covered." if not missing
        else "Functional requirements without a test case: " + ", ".join(missing))

    d.h(1, "7. Execution Log Template")
    d.table(["Run", "Date", "Build / commit", "Device", "Executed", "Passed", "Failed", "Blocked", "Notes"],
            [("1", "", "", "", "", "", "", "", ""), ("2", "", "", "", "", "", "", "", "")],
            widths_cm=[1, 1.8, 2.4, 2.4, 1.6, 1.5, 1.5, 1.6, 2.5], caption="Execution log", font_size=8)
    d.h(1, "8. Defect Report Template")
    d.kv_table([
        ("Defect ID", ""), ("Test case", ""), ("Severity", "Critical / Major / Minor / Cosmetic"),
        ("Build / device", ""), ("Steps to reproduce", ""), ("Expected", ""), ("Actual", ""),
        ("Attachments", "Screenshot, logcat"), ("Status", "Open / Fixed / Verified / Closed"),
    ], caption="Defect report")
    d.h(1, "Appendix A. Known Issues")
    d.table(["ID", "Area", "Description", "Handling"], KNOWN_ISSUES,
            widths_cm=[1.6, 2.8, 7.6, 4.3], caption="Known issues referenced by test cases")
    return d.save(OUT)


if __name__ == "__main__":
    print(build())
