"""Chapter 2: Background and Literature Review."""


def build(c):
    c.chapter(2, "Background and Literature Review")
    c.p("Image translation sits at the intersection of four research areas that rarely cite each other: "
        "text detection and recognition in computer vision, neural machine translation in natural "
        "language processing, image editing and inpainting in graphics, and efficient inference and "
        "interaction design in mobile computing. This chapter reviews each area to the depth needed to "
        "position the design decisions of Chapters 3 to 7, and closes with a synthesis that identifies "
        "the gap this dissertation addresses. The review is selective rather than exhaustive; surveys "
        "such as that of Long, He and Yao [@long2021survey] cover scene-text methods more broadly.")

    # ------------------------------------------------------------------ OCR
    c.h2("Optical Character Recognition", key="lit_ocr")
    c.h3("From document OCR to scene text")
    c.p("Classical OCR engines were designed for scanned documents: high-resolution, fronto-parallel, "
        "dark text on a light, mostly uniform background, laid out in columns. Tesseract, originally "
        "developed at Hewlett-Packard and described by Smith [@smith2007tesseract], is the best-known "
        "open engine of this lineage; its pipeline finds text lines through connected-component analysis "
        "and page-layout heuristics before recognising words. Photographs taken with a phone violate most "
        "of the assumptions behind that design. Text appears at arbitrary angles and scales, under "
        "perspective distortion, over textured or photographic backgrounds, with uneven illumination, "
        "blur and specular highlights, and often as isolated fragments — a label, a sign, a price — "
        "rather than as a paragraph. The research community responded with *scene-text* methods, driven "
        "by benchmarks such as the ICDAR Robust Reading competitions [@karatzas2015icdar, nayef2019mlt] "
        "and by large synthetic training corpora [@gupta2016synthtext, jaderberg2016reading]. Modern "
        "systems, including the one studied here, separate the problem into *detection* (where is text?) "
        "and *recognition* (what does a given text region say?), each solved by a neural network, with "
        "hand-written geometry in between.")

    c.h3("Regression-based and segmentation-based detection")
    c.p("Text detectors fall into two broad families. *Regression-based* detectors predict box "
        "parameters directly. CTPN [@tian2016ctpn] detects fine-scale vertical text proposals and links "
        "them with a recurrent network into horizontal lines. EAST [@zhou2017east] is a single-stage "
        "fully convolutional network that predicts, at every pixel of a score map, the geometry of a "
        "rotated rectangle or quadrilateral, followed by non-maximum suppression. Regression works well "
        "for straight text of moderate aspect ratio but struggles with very long lines and curved text, "
        "because a single receptive field must see the whole instance.")
    c.p("*Segmentation-based* detectors instead predict a per-pixel text probability and recover "
        "instances from it by post-processing. CRAFT [@baek2019craft] predicts character-region and "
        "affinity scores and groups characters into words. PSENet [@wang2019psenet] predicts several "
        "kernels of increasing size for each instance and expands them progressively, which separates "
        "adjacent instances that a single binary map would merge. Differentiable Binarization (DB) "
        "[@liao2020db] simplifies this family considerably. The network predicts a probability map *P* "
        "and a threshold map *T*; during training an approximate, differentiable step function "
        "B = 1/(1 + e^{−k(P − T)}) lets the binarisation threshold be learned jointly with the "
        "segmentation. Ground-truth text regions are *shrunk* before training by an offset "
        "D = A(1 − r_{s}^{2})/L, where *A* and *L* are the area and perimeter of the polygon and r_{s} "
        "is a shrink ratio, so that adjacent instances are separated in the probability map. At "
        "inference the threshold map is discarded, *P* is binarised at a fixed threshold, and each "
        "connected region is dilated (\"unclipped\") back to full size by an offset proportional to its "
        "area over its perimeter. DB++ [@liao2023dbpp] adds adaptive scale fusion to the feature "
        "pyramid. Because DB's inference-time post-processing is cheap and its network is small, it has "
        "become the default detector of lightweight OCR systems, including PP-OCR.")
    c.p("The inference-time post-processing of DB is the part of the detector that this dissertation "
        "reimplements. In the reference implementation [@paddleocr] it consists of: binarising *P*; "
        "extracting contours of connected regions with OpenCV's border-following algorithm "
        "[@suzuki1985border, bradski2000opencv]; scoring each contour by the mean of *P* over its "
        "axis-aligned bounding box; fitting a minimum-area rectangle; dilating the resulting polygon with "
        "the Vatti clipping algorithm [@vatti1992clip] as implemented in a polygon-clipping library; and "
        "fitting a minimum-area rectangle again to the dilated polygon. Chapter 4 shows that each step "
        "admits a short, exact, library-free replacement.")

    c.h3("Sequence recognition with CTC and attention")
    c.p("Recognition networks map an upright crop of a text line to a character string. The dominant "
        "lightweight design is the convolutional-recurrent network (CRNN) of Shi, Bai and Yao "
        "[@shi2017crnn]: a convolutional backbone turns the crop into a horizontal sequence of feature "
        "columns, a bidirectional LSTM [@hochreiter1997lstm] models context along the sequence, and a "
        "per-column classifier predicts a distribution over the character set plus a special *blank* "
        "symbol. The network is trained with connectionist temporal classification (CTC) "
        "[@graves2006ctc], which marginalises over all alignments between the column sequence and the "
        "target string. At inference, greedy CTC decoding takes the most probable symbol per column, "
        "collapses consecutive repeats and removes blanks; the blank is what allows genuine double "
        "letters to survive, since \"l-blank-l\" collapses to \"ll\" while \"l-l\" collapses to \"l\". "
        "Attention-based recognisers such as ASTER [@shi2019aster] replace CTC with an autoregressive "
        "decoder and add a learned rectification of curved text; they are typically more accurate on "
        "irregular text and slower. Baek et al. [@baek2019wrong] decompose recognisers into "
        "transformation, feature extraction, sequence modelling and prediction stages and show that many "
        "reported gains shrink under a consistent training and evaluation protocol — a caution that "
        "motivates the careful comparison protocol of Chapter 8.")

    c.h3("The PP-OCR family")
    c.p("PP-OCR [@du2020ppocr] is an engineering-oriented OCR system that packages a DB detector, a "
        "small text-direction classifier and a CRNN-style CTC recogniser, all with lightweight backbones "
        "derived from MobileNetV3 [@howard2019mobilenetv3, sandler2018mobilenetv2], and a collection of "
        "training strategies chosen to keep the total model size small. The direction classifier decides "
        "whether a cropped line is upside down and is used to rotate it by 180° before recognition. "
        "PP-OCRv3 [@li2022ppocrv3] revised the detector training and the recogniser architecture; "
        "later versions, including the PP-OCRv4 models used in this work, are distributed through the "
        "project repository [@paddleocr]. Recognisers are released per script or language, each with a "
        "character dictionary. The weights are released under the Apache 2.0 licence, and the "
        "project's own mobile demonstration runs them through a C++ runtime together with OpenCV. The "
        "present work uses the released weights unchanged and reimplements all of the algorithmic code "
        "around them in Java.")

    c.h3("Computational geometry for text boxes")
    c.p("Turning a pixel region into an oriented box is a classical computational-geometry task. The "
        "convex hull of *n* planar points can be computed in O(n log n) time by Graham's scan "
        "[@graham1972hull] or by Andrew's monotone chain [@andrew1979hull], which sorts the points "
        "lexicographically and builds the lower and upper hulls in two linear passes; standard texts "
        "[@preparata1985cg, deberg2008cg] give the analysis. Freeman and Shapira [@freeman1975rect] "
        "proved that a minimum-area rectangle enclosing a convex polygon has one side collinear with an "
        "edge of the polygon, which reduces the continuous search over orientations to a finite set of "
        "candidates. Toussaint's rotating calipers [@toussaint1983calipers] enumerate those candidates in "
        "linear time by advancing four support lines around the hull. Polygon offsetting — dilating a "
        "polygon by a fixed distance — is harder in general: the Vatti algorithm [@vatti1992clip] handles "
        "arbitrary, possibly self-intersecting polygons at the price of a substantial implementation. "
        "Finally, rectifying an oriented quadrilateral into an upright crop is a planar homography "
        "determined by four point correspondences [@hartley2004mvg].")

    # ------------------------------------------------------------------- MT
    c.h2("Neural Machine Translation", key="lit_mt")
    c.h3("Encoder–decoder models and the Transformer")
    c.p("Neural machine translation models the conditional probability of a target sentence given a "
        "source sentence with an encoder–decoder network. Early systems used recurrent networks "
        "[@sutskever2014seq2seq]; attention [@bahdanau2015attention] let the decoder consult all encoder "
        "states at every step, and large production systems followed [@wu2016gnmt]. The Transformer "
        "[@vaswani2017attention] replaced recurrence with multi-head self-attention and became the "
        "standard architecture. Decoding is autoregressive: the decoder produces one token at a time, "
        "each conditioned on the source encoding and on all previously generated tokens. Greedy decoding "
        "takes the arg-max at each step; beam search keeps the *k* best partial hypotheses and usually "
        "improves quality modestly at roughly *k* times the decoder cost.")
    c.p("Because each decoding step attends over all previous target positions, a naive implementation "
        "recomputes the keys and values of the whole prefix at every step. Production inference caches "
        "them — the *key–value (KV) cache* — so that each step processes only the newest position; the "
        "memory and bandwidth implications of the cache are a central concern of large-scale Transformer "
        "inference [@pope2023scaling]. Exporting a model with a KV cache to a portable graph format "
        "requires threading the cache tensors of every layer through the graph as explicit inputs and "
        "outputs, which is why simpler exports omit it. Chapter 5 analyses exactly what that omission "
        "costs.")

    c.h3("Marian, OPUS and OPUS-MT")
    c.p("Marian [@junczys2018marian] is an efficient C++ toolkit for training and serving NMT models. "
        "OPUS [@tiedemann2012opus] is a large collection of openly licensed parallel corpora. OPUS-MT "
        "[@tiedemann2020opusmt] combines the two: the Helsinki-NLP group trained and released Transformer "
        "models for many language pairs on OPUS data, which are also distributed in a form usable with "
        "the Hugging Face Transformers library [@wolf2020transformers] and can therefore be exported to "
        "ONNX with Hugging Face Optimum [@optimum]. The models are released under CC-BY 4.0, which "
        "requires attribution. Most published OPUS-MT models are English-centric; for pairs among "
        "Chinese, Japanese and Korean there is no direct model, which is the origin of the pivoting "
        "problem addressed in Chapter 5.")

    c.h3("Subword tokenisation")
    c.p("NMT models operate on subword units so that the vocabulary is finite while rare words remain "
        "representable. Byte-pair encoding [@sennrich2016bpe] merges frequent symbol pairs greedily. The "
        "*unigram language model* of Kudo [@kudo2018unigram] instead assigns each piece in a vocabulary a "
        "probability and segments a string into the sequence of pieces with maximum total "
        "log-probability, which is found exactly by the Viterbi algorithm [@forney1973viterbi]. "
        "SentencePiece [@kudo2018sentencepiece] implements both schemes language-independently: it "
        "treats the input as a raw character stream, applies Unicode normalisation, and represents word "
        "boundaries with a visible meta-symbol (U+2581) so that detokenisation is lossless. OPUS-MT models "
        "ship SentencePiece models for source and target, and a vocabulary that maps pieces to ids. A "
        "segmentation that differs from the one used in training still produces valid ids, so tokeniser "
        "errors are silent — a property that shapes the testing strategy of Chapter 7.")

    c.h3("Compression: quantisation, distillation and efficient architectures")
    c.p("Transformer translation models have tens to hundreds of millions of parameters. Three families "
        "of techniques reduce their cost. *Quantisation* stores weights, and optionally activations, as "
        "8-bit integers: Jacob et al. [@jacob2018quant] established integer-arithmetic-only inference for "
        "convolutional networks, Krishnamoorthi [@krishnamoorthi2018quant] surveyed post-training and "
        "per-channel schemes, and Bhandare et al. [@bhandare2019int8nmt] applied 8-bit quantisation to "
        "Transformer translation. *Dynamic* quantisation quantises weights offline and activations at run "
        "time from their observed range, requiring no calibration data, which is what the conversion "
        "script of this system uses. *Knowledge distillation* trains a small student to imitate a large "
        "teacher [@hinton2015distill]; sequence-level distillation [@kim2016distill] is especially "
        "effective for NMT. *Architectural* choices such as a deep encoder with a shallow decoder "
        "[@kasai2021deepshallow] shift computation to the encoder, which runs once, and away from the "
        "decoder, which runs once per output token; efficiency-focused systems combine all three "
        "[@kim2019ludicrous]. Model pruning and weight sharing [@han2016deepcompression] are further "
        "options not used here.")

    c.h3("Pivot translation and multilingual models")
    c.p("When no direct model exists for a pair, a classical remedy is to translate through a third "
        "*pivot* language. In phrase-based statistical MT, Utiyama and Isahara compared sentence-level "
        "pivoting (translate twice) with phrase-table triangulation [@utiyama2007pivot], and Wu and Wang "
        "developed the triangulation approach further [@wu2007pivot]. Sentence-level pivoting is simple "
        "and always applicable, but it costs two translations and compounds errors: information lost or "
        "distorted in the first leg cannot be recovered in the second, and phenomena that the pivot "
        "language does not mark — honorific levels, zero pronouns, topic marking — are especially at "
        "risk between languages that share them but that English lacks.")
    c.p("Multilingual NMT offers an alternative. Firat, Cho and Bengio [@firat2016multiway] shared an "
        "attention mechanism across many language pairs; Johnson et al. [@johnson2017multilingual] "
        "trained a single model with a target-language token and observed zero-shot translation between "
        "pairs never seen together in training. M2M-100 [@fan2021m2m] trained explicitly on non-English "
        "directions, and NLLB-200 [@nllb2022] scaled the approach to two hundred languages and released "
        "distilled variants, the smallest of which has about 600 million parameters. These models cover "
        "the CJK directions directly, but even the distilled variants are an order of magnitude larger "
        "than an OPUS-MT pair. For a phone application that must also hold OCR models, that difference "
        "decides the design; Chapter 8 nevertheless includes NLLB-200-distilled-600M as an off-device "
        "upper-bound reference for the pivoted directions.")

    # ---------------------------------------------------------- re-rendering
    c.h2("Text Removal, Editing and In-Image Translation", key="lit_render")
    c.h3("Inpainting")
    c.p("Replacing text in an image requires first removing the original. The general problem is image "
        "inpainting: filling a masked region plausibly from its surroundings. Bertalmio et al. "
        "[@bertalmio2000inpainting] propagated isophotes into the hole with partial differential "
        "equations; Criminisi, Pérez and Toyama [@criminisi2004exemplar] copied exemplar patches in a "
        "priority order that preserves linear structures; Telea [@telea2004inpaint] proposed a fast "
        "marching method that is simple enough to be included in OpenCV. These classical methods work "
        "for thin masks on smooth backgrounds — text strokes on paper are a good case — but produce "
        "smears over structured textures. Learned inpainting, exemplified by LaMa [@suvorov2022lama], "
        "uses fast Fourier convolutions to obtain an image-wide receptive field and handles large masks "
        "and repetitive structure far better, at the cost of a sizeable network.")
    c.h3("Scene-text erasing and editing")
    c.p("Text-specific erasure networks learn to remove text without an explicit mask. Scene Text "
        "Eraser [@nakamura2017eraser] operated on image patches; EnsNet [@zhang2019ensnet] erased text "
        "from whole images end to end with a set of losses designed to make the result indistinguishable "
        "from text-free backgrounds. Scene-text *editing* goes further and synthesises replacement text "
        "in the style of the original: SRNet [@wu2019srnet] decomposes the task into background "
        "inpainting, text conversion and fusion, and STEFANN [@roy2020stefann] edits individual "
        "characters with a font-adaptive network. For translation, style transfer across scripts is "
        "especially difficult because the target glyphs have no counterpart in the source style.")
    c.h3("End-to-end in-image translation")
    c.p("Mansimov et al. [@mansimov2020inimage] framed in-image translation as a single pixel-to-pixel "
        "problem, producing an image of the translated text directly from an image of the source text. "
        "The formulation is elegant but, at the time of writing, far from the robustness and language "
        "coverage of cascaded OCR–MT–rendering systems, and it offers no intermediate text that a user "
        "could copy, correct or have read aloud.")
    c.h3("Compositing")
    c.p("Whatever removes or de-emphasises the original, the final image is assembled by compositing. "
        "Porter and Duff [@porter1984compositing] formalised compositing algebra with an alpha channel; "
        "the *source-over* operator, which blends a source colour *S* with coverage α over a destination "
        "*D* as αS + (1 − α)D, is the default of every 2-D graphics library including Android's. On "
        "Android the blend is performed on gamma-encoded sRGB values [@srgb], not on linear light, which "
        "matters when interpreting any analysis in terms of perceived contrast. Chapter 6 builds the "
        "re-rendering method directly on this operator and analyses it exactly.")

    # ------------------------------------------------------------ runtimes
    c.h2("On-Device Machine Learning Runtimes", key="lit_runtime")
    c.p("Deploying neural networks on phones requires an inference runtime that executes a portable "
        "model representation with kernels optimised for mobile CPUs, GPUs or neural accelerators. "
        "TensorFlow [@abadi2016tensorflow] provides a mobile runtime in its ecosystem; MNN "
        "[@jiang2020mnn] is a lightweight engine designed for mobile deployment; PaddlePaddle ships Paddle "
        "Lite, which the PaddleOCR mobile demonstration uses; and ONNX Runtime [@onnxruntime] executes "
        "models in the Open Neural Network Exchange format [@onnx], with a Java API on Android and "
        "graph-level optimisations such as operator fusion and constant folding. Benchmarks such as AI "
        "Benchmark [@ignatov2018aibench] document the wide spread of neural-network performance across "
        "Android devices, which is why Chapter 8 prescribes measurements on several price tiers rather "
        "than one flagship.")
    c.p("Choosing a runtime also chooses a conversion path. PaddleOCR models are converted to ONNX with "
        "paddle2onnx [@paddle2onnx]; OPUS-MT models are exported with Optimum [@optimum]. Conversions are "
        "not always clean: Chapter 7 documents a rank mismatch in shape-assembling `Concat` nodes emitted "
        "for some PaddleOCR graphs that makes ONNX Runtime refuse to load them, and the repair applied. "
        "A further, often decisive consideration on Android is whether the runtime and its surrounding "
        "code need native libraries built per CPU architecture. ONNX Runtime ships its native library "
        "inside a standard Android archive; everything else in the present system is Java, so the "
        "application itself needs no NDK build.")

    # ----------------------------------------------------------------- HCI
    c.h2("Mobile Interaction Design", key="lit_hci")
    c.h3("Touch-target sizing")
    c.p("Fitts' law [@fitts1954] relates the time to acquire a target to the ratio of its distance and "
        "width, and underlies most guidance on target size. On touch screens the finger's contact area and "
        "occlusion of the target add a floor below which error rates rise sharply. Parhi, Karlson and "
        "Bederson [@parhi2006target] studied one-handed thumb use on small touch screens and found that "
        "targets of roughly 9–10 mm were needed before performance stopped improving. Platform guidance "
        "encodes similar floors: Android recommends touch targets of at least 48 × 48 dp "
        "[@android_a11y], and WCAG 2.1 success criterion 2.5.5 (level AAA) asks for 44 × 44 CSS pixels "
        "[@wcag21]. The users of an image translation app are frequently holding a document or standing "
        "in front of a sign, often with one hand. Chapter 7 describes how the system sizes its controls, "
        "and why several of them deliberately fall below these floors in favour of a compact interface.")
    c.h3("Navigation patterns")
    c.p("Mobile applications organise top-level destinations with a bottom navigation bar, a navigation "
        "drawer or a navigation rail. Material Design describes the rail as a vertical strip of "
        "destination icons along the side of the screen, optionally expandable to show labels, intended "
        "for medium and larger screens [@material_rail]. On a narrow phone a rail competes with content "
        "for width, and an expanded rail that pushes content aside can squeeze it severely; an overlay "
        "that expands over the content with a scrim avoids that at the cost of temporarily hiding it. "
        "Chapter 7 motivates the choice made in this system on exactly this trade-off.")
    c.h3("Contrast and legibility")
    c.p("WCAG 2.1 defines contrast ratio from relative luminance and requires 4.5:1 for normal text at "
        "level AA [@wcag21]. The definition is non-linear in encoded sRGB values, so a linear attenuation "
        "of encoded colour differences — which is what translucent compositing produces — maps "
        "monotonically but not proportionally to contrast ratio. This distinction is made explicit in "
        "Chapter 6, where the analytical result is stated in the compositing colour space and its "
        "perceptual interpretation is deferred to the user study.")

    # ------------------------------------------------------------- synthesis
    c.h2("Synthesis and Gap Analysis", key="lit_gap")
    c.p("{T:gap} summarises the design space. Server-based services are excluded by the privacy and "
        "connectivity requirements. Cascaded on-device pipelines built on OpenCV and a native runtime "
        "are feasible but carry a per-architecture native build. Model-based text removal and editing "
        "produce the most seamless images but add a network of comparable size to the whole OCR stack "
        "and offer no analytical control over what remains of the original. End-to-end in-image "
        "translation is not yet a practical alternative. No approach in the reviewed literature combines "
        "full offline operation, a managed-code implementation without native dependencies of its own, "
        "coverage of pairs without direct models under a bounded memory budget, and a re-rendering "
        "scheme with a stated, provable effect on the original content.")
    c.table("gap", "Qualitative comparison of approaches to image translation (derived from the literature "
                   "reviewed in this chapter; not a measurement)",
            ["Approach", "Offline", "No own native code", "CJK↔CJK without direct model",
             "Original text treatment", "Extra model for removal", "Analytical guarantee"],
            [["Server-based cascaded services", "No", "n/a", "Provider-dependent", "Varies", "Varies", "No"],
             ["Classical OCR engine + offline MT [@smith2007tesseract]", "Yes", "Usually no", "Only if "
              "pivoted", "Usually none (text only)", "No", "n/a"],
             ["PP-OCR reference mobile pipeline [@paddleocr]", "Yes", "No (C++, OpenCV)", "n/a (OCR only)",
              "n/a", "No", "n/a"],
             ["Cascade + learned inpainting [@suvorov2022lama]", "Possible", "Depends", "Depends",
              "Removed", "Yes (large)", "No"],
             ["Scene-text editing [@wu2019srnet, roy2020stefann]", "Research", "No", "n/a",
              "Replaced in style", "Yes", "No"],
             ["End-to-end in-image NMT [@mansimov2020inimage]", "Research", "No", "n/a", "Regenerated",
              "Integral", "No"],
             ["**This work**", "**Yes**", "**Yes (Java + ORT)**", "**Pivot, bounded memory**",
              "**Attenuated by 1 − α, halo**", "**No**", "**Yes (Lemma 4.1, Prop. 6.1)**"]],
            widths=[3.6, 1.4, 2.1, 2.3, 2.4, 2.0, 2.5], font_size=8)
    c.p("The remaining chapters fill this gap. The approach is deliberately analytic where the "
        "literature is predominantly learned: geometry that can be computed exactly is computed exactly "
        "and proved correct, and re-rendering is built from a compositing operator whose effect can be "
        "stated in closed form. Learned components are used where nothing else will do — detection, "
        "recognition and translation — and are taken unchanged from open releases, so that the "
        "contributions of this work are isolated from model training.")
