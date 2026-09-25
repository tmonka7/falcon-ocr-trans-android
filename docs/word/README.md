# Word documents

| File | Document | ID |
|---|---|---|
| `01_Software_Requirements_Specification.docx` | Requirements specification (24 functional, 12 non-functional) | FOT-SRS-001 |
| `02_System_Design_Document.docx` | System design | FOT-SDD-001 |
| `03_Screen_Design_Specification.docx` | Screen design, with wireframes of all 10 screens | FOT-SDS-001 |
| `04_Test_Case_Specification.docx` | Test cases, unit-test inventory, coverage matrix | FOT-TCS-001 |
| `Dissertation_Offline_Image_Translation.docx` | Doctoral dissertation draft | — |

The documents are **generated**. Do not edit the .docx files by hand; change the
sources and rebuild:

```sh
python docs/word/_src/build_all.py
```

Needs Python 3 with `python-docx` and `Pillow` (plus `matplotlib` for the
dissertation figures).

- `_src/spec_data.py` is the single source of truth for requirement, screen,
  test-case and known-issue IDs. All four specifications import it, so their
  traceability matrices cannot disagree.
- `_src/docgen.py` holds the shared house style.
- `_src/wireframes.py` and `_src/diagrams.py` draw the figures.

When you open a document, Word asks to update fields. Answer **Yes** so the
table of contents and page numbers fill in.

## Status

- The specifications describe the code in this repository, including the
  translucent re-rendering, the hidden Korean UI, the large screen-relative
  controls and the collapsible side menu.
- The test cases have **not been executed**, so their Result fields are blank.
- The dissertation contains **no measured results**. Every result cell is a
  `[TBD]` placeholder until the experiments in its Chapter 8 are run.
