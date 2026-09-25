"""Chapter 1: Introduction."""


def build(c):
    c.chapter(1, "Introduction")
    c.p("Camera-based translation has become one of the most common ways in which people read text in a "
        "language they do not know. A traveller points a phone at a menu, a migrant photographs a letter "
        "from a public authority, a clinician receives a discharge summary written abroad, a researcher "
        "scans a page of a foreign-language monograph. In each case the user wants more than a list of "
        "translated sentences: they want to see the translation *where the original text was*, in the "
        "context of the page, so that headings still look like headings, a price stays next to its dish "
        "and a form field stays next to its label. Systems that provide this experience work in three "
        "stages: *recognition* (optical character recognition, OCR), *translation* (machine translation, "
        "MT) and *re-rendering*, which paints the translated text back into the image in place of the "
        "original [@mansimov2020inimage].")
    c.p("This dissertation is about building all three stages so that they run completely on a commodity "
        "smartphone, with no server, and about understanding the design decisions that this constraint "
        "forces. It is grounded in a concrete, complete system — an Android application written in Java — "
        "whose source code is the primary artefact studied. Every algorithmic parameter quoted in the "
        "following chapters has been checked against that code, and Appendix A lists each one with the "
        "file that defines it.")

    c.h2("Motivation", key="motivation")
    c.h3("Privacy and confidentiality")
    c.p("In widely deployed translation services the first two stages, and often the third, run on a "
        "server. The image leaves the device, is processed by a third party, and may be retained for "
        "quality improvement or abuse detection. For a photograph of a street sign this is harmless. For "
        "many of the documents that people most need to understand, it is not. Medical records, legal "
        "correspondence, identity documents, bank statements and employment contracts contain personal "
        "data whose transfer to a processor is regulated in many jurisdictions; in the European Union, "
        "for example, such processing falls under the General Data Protection Regulation [@gdpr2016], "
        "which requires a lawful basis, purpose limitation and, for transfers outside the Union, "
        "additional safeguards. Corporate and governmental users face data-residency rules that may "
        "forbid sending documents to an external service at all. A translation tool that never "
        "transmits the image removes this entire class of concerns by construction rather than by "
        "policy.")
    c.p("The system studied here takes the strongest available form of that guarantee on Android: its "
        "manifest does not request the `INTERNET` permission. Without that permission the operating "
        "system denies the application network sockets, so the claim that no image or text leaves the "
        "device does not depend on the correctness of application code. This is a stronger property "
        "than a privacy policy or an \"offline mode\" switch, and it is cheap to audit: a reviewer "
        "needs to read one XML file rather than the entire code base.")
    c.h3("Connectivity")
    c.p("The second motivation is availability. Translation is needed precisely in situations — travel, "
        "field work, humanitarian settings, roaming abroad, basements, aircraft — where connectivity is "
        "absent, expensive or unreliable. A server-based system degrades to nothing in those settings. "
        "An on-device system has constant availability, and its latency does not depend on the network. "
        "The price is that everything must fit on the device: the models, their working memory, and the "
        "computation needed to run them within a time that users will accept.")
    c.h3("Regulated and sensitive documents")
    c.p("A third motivation combines the first two. Institutions that handle sensitive documents — "
        "hospitals, courts, social services, border agencies, law firms — increasingly encounter "
        "documents in languages their staff do not read. Their information-governance rules often "
        "prohibit cloud services, and their staff frequently work away from a desk. A tool that can be "
        "installed on a managed phone, that is demonstrably unable to transmit data, and that preserves "
        "the layout of the document so that the translation can be cross-checked against the original "
        "fills a real gap. Preserving layout matters here beyond aesthetics: when the translation of a "
        "field appears exactly where the field was, a reader can verify which value belongs to which "
        "label, a property that a list of translated sentences does not have.")

    c.h2("Problem Statement", key="problem")
    c.p("Moving the full image translation pipeline onto a phone raises four problems, which together "
        "define the scope of this dissertation.")
    c.steps([
        "**Resources.** Text detection, text recognition for several scripts and a Transformer "
        "translator [@vaswani2017attention] must fit together within a mobile process whose memory is "
        "policed by the operating system's low-memory killer [@android_memory], and must complete within "
        "a few seconds per page on mid-range hardware without making the user interface unresponsive.",
        "**Dependencies.** Reference OCR pipelines depend on OpenCV [@bradski2000opencv] for contour "
        "extraction and minimum-area rectangles and on a polygon-clipping library for region dilation "
        "[@paddleocr, vatti1992clip]. On Android that forces a native build per CPU architecture through "
        "the NDK, increasing application size, build complexity and maintenance cost.",
        "**Language coverage.** Compact open translation models are published predominantly for "
        "English-centric pairs; for the directions between Chinese, Japanese and Korean (CJK) no compact "
        "OPUS-MT model exists [@tiedemann2020opusmt]. Massively multilingual models that do cover these "
        "directions [@nllb2022, fan2021m2m] are far larger than the per-pair budget of a phone "
        "application.",
        "**Re-rendering.** Removing the original text convincingly normally requires an inpainting or "
        "text-erasure network [@suvorov2022lama, zhang2019ensnet], a further model that competes for the "
        "same memory. The cheap alternative, filling every text box with a flat colour, leaves visible "
        "patches over photographs, gradients and paper texture and makes the translation look like a "
        "sticker.",
    ])
    c.p("The problem addressed is therefore: *how can a complete, layout-preserving image translation "
        "pipeline be engineered to run fully offline on commodity smartphones, with no native code of its "
        "own and a bounded memory footprint, while covering all directions among four languages and "
        "producing re-rendered pages whose treatment of the original content is analytically "
        "understood?* The question has an engineering side (can it be built, and how) and a scientific "
        "side (which design choices are exact, which are approximations, and what do they cost). This "
        "dissertation treats both.")

    c.h2("Research Questions", key="rqs")
    c.p("The dissertation is organised around five research questions. They are aligned one-to-one with "
        "the evaluation protocol of the companion journal manuscript, and Chapter 8 operationalises each "
        "of them into hypotheses, datasets, metrics and analyses.")
    c.table("rqs", "Research questions and where they are addressed",
            ["RQ", "Question", "Method chapter", "Protocol / results"],
            [["RQ1", "Is the library-free DB post-processing (component-mean score, row-extreme hull, "
                     "rectangle unclip) faithful to the reference OpenCV + polygon-clipping implementation, "
                     "and does the component-restricted score reduce the bias against rotated text?",
              "4", "{S:m_rq1} / {S:r_rq1}"],
             ["RQ2", "How accurate is on-device recognition across the four scripts, and how much does "
                     "the conservative 180° orientation classifier contribute?", "4", "{S:m_rq2} / {S:r_rq2}"],
             ["RQ3", "What translation quality do int8 OPUS-MT models achieve on-device for all twelve "
                     "directions, and what do quantisation, greedy decoding and English pivoting cost?",
              "5", "{S:m_rq3} / {S:r_rq3}"],
             ["RQ4", "What are per-stage latency, peak memory and model-load time on commodity devices of "
                     "different price tiers, and what is the measured overhead of cache-less decoding?",
              "3, 5", "{S:m_rq4} / {S:r_rq4}"],
             ["RQ5", "How do users perceive translucent, halo-assisted re-rendering compared with opaque "
                     "erasure and with inpainting, and does measured texture retention follow the "
                     "analytical prediction 1 − α?", "6", "{S:m_rq5} / {S:r_rq5}"]],
            widths=[1.2, 9.4, 2.4, 3.3])

    c.h2("Contributions", key="contrib")
    c.p("The dissertation makes the following contributions.")
    c.bullets([
        "**A dependency-light, fully offline pipeline.** End-to-end OCR plus MT runs in managed Java code "
        "over ONNX Runtime [@onnxruntime], with no network permission, a single serialised inference "
        "thread, recognition sessions cached per language, and at most one translation model pair "
        "resident at a time (Chapter 3).",
        "**Library-free DB post-processing with proofs.** An exact reduction of the convex-hull input to "
        "per-row extreme pixels (Lemma 4.1, with a complete proof), a closed-form unclip offset for "
        "rectangles (Equation {E:unclip_rect}), a complexity analysis of the whole post-processing chain, "
        "and a component-restricted confidence score that removes a systematic penalty on rotated text "
        "(Chapter 4).",
        "**Analysed on-device translation.** A pure-Java SentencePiece unigram encoder with exact Viterbi "
        "segmentation, greedy Marian decoding whose cache-less cost is derived exactly, sentence-level "
        "chunking, and English-pivoted routing for the six CJK↔CJK directions with an analysis of error "
        "compounding (Chapter 5).",
        "**Translucent, layout-preserving re-rendering.** A feathered paper-colour highlight over the "
        "geometric union of the text regions, whose effect on the original glyphs and the page texture "
        "is bounded exactly by Proposition 6.1, a halo that restores full local contrast, and a "
        "bisection size-fitting procedure with a proven iteration bound and feasibility guarantee "
        "(Chapter 6).",
        "**An evaluation protocol with pre-specified hypotheses.** Datasets, metrics, device protocol, "
        "ablations and a within-subjects user study with a mixed-effects analysis plan, together with "
        "result tables that are deliberately left empty until the protocol is executed (Chapters 8 and 9).",
        "**A usable system.** The implementation includes large, screen-relative touch targets, a "
        "collapsible overlay side menu and language gating that allows a fully implemented language to "
        "be withheld from users by editing a single list (Chapter 7).",
    ])

    c.h2("Thesis Statement", key="thesis")
    c.note("A complete image translation pipeline — detection, recognition, translation and "
           "layout-preserving re-rendering — can run entirely on a commodity smartphone in managed code "
           "without any native dependency of its own; its geometric post-processing can be made exact "
           "without computer-vision libraries, its coverage of language pairs without direct models can "
           "be obtained by bounded-memory pivoting, and its re-rendering can replace model-based text "
           "removal with a translucent compositing scheme whose effect on the original content is "
           "analytically bounded and whose legibility is locally guaranteed.", label="Thesis")
    c.p("The statement makes three kinds of claim. Claims of *feasibility* are supported by the "
        "existence of the implementation, which builds and runs, and are described in Chapters 3 and 7. "
        "Claims of *exactness* and *boundedness* are supported by proofs and derivations in Chapters 4, 5 "
        "and 6. Claims about *quality* — that the library-free post-processing is as accurate as the "
        "reference, that translation quality is acceptable, that users find the translucent rendering "
        "at least as legible and more natural — are empirical. They are stated as hypotheses in "
        "Chapter 8 and remain open until the protocol is executed; Chapter 9 provides the result tables "
        "that will receive those measurements.")

    c.h2("A Note on the Status of Empirical Results", key="status")
    c.p("The system has not yet been benchmarked. This dissertation therefore adopts a strict reporting "
        "rule: no experimental number appears anywhere in the text. Every cell of every results table "
        "contains the placeholder [TBD], and each results section states which hypothesis the table will "
        "test once filled. Numbers that do appear are of two kinds only. The first kind are *repository "
        "facts*: configuration constants read from the source code (for example the binarisation "
        "threshold 0.3), and sizes stated in the project documentation (a model tree of about 230 MB, "
        "about 35 MB per translation pair, 50 unit tests, a universal debug APK of about 78 MB before "
        "models). The second kind are *analytical values* that follow from a stated formula, such as "
        "the retained contrast 1 − α = 0.41 for α = 150/255, or the number of bisection steps required "
        "for a given tolerance; these are always labelled as analytical. Figures that show images or "
        "curves are either schematics derived from the code or synthetic illustrations, and their "
        "captions say which.")

    c.h2("Organisation of the Dissertation", key="org")
    c.p("Chapter 2 reviews the literature on text detection and recognition, neural machine translation "
        "and its compression, scene-text removal and in-image translation, on-device inference runtimes "
        "and mobile interaction design, and closes with a gap analysis. Chapter 3 states the requirements "
        "and presents the architecture, threading and memory model, data flow and deployment of the "
        "system. Chapter 4 develops the library-free detection post-processing, recognition, colour "
        "estimation, layout analysis and script-based source verification, with proofs and complexity "
        "bounds. Chapter 5 covers tokenisation, decoding, chunking and pivot routing. Chapter 6 presents "
        "the translucent re-rendering model, its analysis and the size-fitting procedure. Chapter 7 "
        "describes the Android implementation, model conversion and graph repair, the user interface and "
        "the testing strategy. Chapter 8 specifies the experimental methodology and Chapter 9 the result "
        "tables and an analytical discussion of expected trade-offs and limitations. Chapter 10 "
        "concludes. Appendices list every parameter with its source file, the model inventory, "
        "placeholders for user-study materials, and build and reproducibility instructions.")
