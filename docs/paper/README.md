# Manuscript draft

`main.tex` + `references.bib`, using the IEEEtran journal class (in every TeX Live / MiKTeX install).

```sh
latexmk -pdf main.tex        # or: pdflatex, bibtex, pdflatex, pdflatex
```

## Status

| Part | State |
|---|---|
| Abstract, I–V (intro, related work, overview, method, implementation) | Written; matches the code as of this commit |
| VI Experimental setup | Protocol written; not yet executed |
| VII Results | **Empty tables. No number in the draft is a measurement** |
| VIII–IX Discussion, conclusion | Written; the headline results sentence is still pending |
| Front matter | Author list, affiliations and journal name are placeholders |

While `\drafttrue` is set, every placeholder (`\tbd`, `\note{}`) renders in red.

## Before submission

1. Run RQ1–RQ5 (Section VI) and fill every `\tbd`. Delete rows you do not measure.
2. Add the qualitative comparison figure (original / opaque erase / highlight + halo / inpainting).
3. Get ethics approval or exemption for the user study (RQ5), and report it.
4. Check every entry in `references.bib` against the publisher record: pages, volume, DOI.
5. Set `\draftfalse`, delete the "Draft status" paragraph, and fill in the front matter.
6. Reformat for the target journal's template if it is not IEEE.

## Venue fit

The contribution is a systems-and-methods paper. The analytically grounded
rendering scheme, the exact hull reduction and a solid on-device evaluation are
its strongest parts. SCIE-indexed venues that publish this kind of work include
*IEEE Access*, *Multimedia Tools and Applications*, *Applied Sciences*,
*Electronics* and *Sensors*. Stronger venues will expect the user study and
the post-processing comparison against the reference to be thorough.
