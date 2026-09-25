"""Chapter 5: On-device Translation."""


def build(c):
    c.chapter(5, "On-device Translation")
    c.p("This chapter describes how recognised paragraphs are translated on the device: tokenisation "
        "with a pure-Java SentencePiece unigram encoder, encoding and greedy decoding with an OPUS-MT "
        "Transformer on int8 weights, chunking of long inputs, and routing of directions without a "
        "direct model through English. Each design decision trades quality or speed for simplicity and "
        "bounded memory, and the chapter quantifies the trade wherever it can be derived analytically; "
        "measurements are deferred to RQ3 and RQ4.")

    c.h2("Translation Interface and Page-level Batching", key="mt_iface")
    c.p("The pipeline calls `translateAll(sources, from, to)` once per page with the list of paragraph "
        "source texts, not once per paragraph. The call is served by `PivotTranslator`, which either "
        "delegates to `MarianTranslator` for a direct pair or runs two whole-page legs through English. "
        "Batching at page level matters because translation sessions are loaded lazily and only one pair "
        "is kept resident: translating paragraph by paragraph through a pivot would load and unload two "
        "model pairs per paragraph. Empty or whitespace-only paragraphs yield an empty translation "
        "without invoking the model, and if source and target coincide the input is returned unchanged.")

    c.h2("SentencePiece Unigram Tokenisation", key="spm")
    c.h3("Normalisation")
    c.p("SentencePiece ships its model as a protocol buffer parsed by a C++ library. Rather than "
        "reimplement that format, the conversion script flattens the source-side model into a two-column "
        "table of pieces and log-probabilities, and `SpmEncoder` consumes the table. Input text is first "
        "normalised as SentencePiece does by default [@kudo2018sentencepiece]: Unicode NFKC "
        "normalisation, collapsing runs of whitespace to one space and trimming, then replacing every "
        "space with the boundary marker ▁ (U+2581) and prefixing the string with one marker. The leading "
        "marker (\"add dummy prefix\") makes the first word of a sentence tokenise identically to the same "
        "word in mid-sentence.")
    c.h3("Formulation and Viterbi segmentation")
    c.p("A unigram language model [@kudo2018unigram] assigns each piece w in a vocabulary V a "
        "probability p(w), and the probability of a segmentation 𝐱 = (x_{1}, …, x_{K}) of a normalised "
        "string z is the product of its piece probabilities. The tokeniser returns the most probable "
        "segmentation:")
    c.eq("𝐱* = argmax_{𝐱 ∈ S(z)}  Σ_{k=1}^{K} log p(x_{k})", key="unigram")
    c.p("where S(z) is the set of segmentations of z into pieces. Because the objective is a sum over "
        "consecutive pieces, it decomposes over prefixes and is solved exactly by dynamic programming — "
        "the Viterbi algorithm [@forney1973viterbi] on the lattice whose nodes are character positions "
        "and whose arcs are pieces ({F:viterbi}). With B(0) = 0 and ℓ_{max} the length of the longest "
        "piece in V,")
    c.eq("B(e) = max  [ B(s) + σ(z_{s:e}) ]  over  e − ℓ_{max} ≤ s < e,     "
         "σ(w) = log p(w) if w ∈ V;  −10 if |w| = 1 and w ∉ V;  −∞ otherwise", key="viterbi")
    c.p("and back-pointers recover 𝐱*. The single-character escape with a fixed penalty of −10 "
        "guarantees that every string is segmentable, so an unseen glyph cannot make a whole sentence "
        "untranslatable; such a character is later mapped to the vocabulary's unknown id. Ties are "
        "broken towards the earliest start position, because the recurrence updates B(e) only on a "
        "strict improvement.")
    c.figure("viterbi", "viterbi", "Viterbi segmentation on a toy unigram lattice for \"▁unhappy\" with "
             "invented piece scores (illustration of the algorithm, not model data). Arcs are pieces; the "
             "red path is the maximum-score segmentation.", width=15.5)
    c.p("For a normalised string of n characters the recurrence examines at most n ℓ_{max} arcs; each "
        "arc requires a substring and a hash lookup of cost O(ℓ_{max}), so the time is O(n ℓ_{max}^{2}) "
        "character operations and the memory O(n). For OCR-length inputs this is negligible beside the "
        "network. Relative to the reference library the implementation is exact for the segmentation "
        "objective given the same piece scores; it does not reproduce features the OPUS-MT source models "
        "are not expected to need, such as byte fallback, user-defined symbols or sampling-based subword "
        "regularisation. Because a subtly different segmentation still produces valid ids — and the "
        "model then produces fluent text that is not a translation of the input — the encoder is covered "
        "by eight unit tests (Chapter 7).")
    c.h3("Vocabulary, special tokens and detokenisation")
    c.p("Marian models share one vocabulary between source and target, so a single `token<TAB>id` table "
        "serves both directions of lookup; it is split on the *last* tab of each line because a token "
        "may itself contain a tab. Pieces are mapped to ids, with unknown pieces mapped to the id of "
        "`<unk>`, and the end-of-sequence id is appended. Special-token ids and decoding limits are "
        "read from a per-pair configuration file rather than hard-coded, because they differ between "
        "releases and a wrong decoder start id fails silently ({T:mtconfig}). On output, ids are mapped "
        "back to pieces, pieces that look like special tokens (`<…>`) are dropped, the pieces are "
        "concatenated and markers become spaces.")
    c.table("mtconfig", "Per-pair configuration read by `MtConfig` (fallback defaults from the code)",
            ["Field", "Fallback", "Use"],
            [["`pad_token_id`", "58100", "Padding; also stops decoding if emitted"],
             ["`eos_token_id`", "0", "Appended to the source; stops decoding"],
             ["`unk_token_id`", "1", "Unknown id (vocabulary's own `<unk>` preferred)"],
             ["`decoder_start_token_id`", "= pad", "First decoder input (Marian reuses pad)"],
             ["`max_length`", "256, clamped to [8, 512]", "Hard ceiling n_{max} on generated tokens"],
             ["`vocab_size`", "0 (informational)", "—"]],
            widths=[4.6, 4.2, 7.5])

    c.h2("Encoder and Greedy Decoding", key="decode")
    c.p("For each chunk the encoder runs once on the source ids 𝐮 = (u_{1}, …, u_{m}) — the pieces plus "
        "the end-of-sequence id, so m includes it — with an all-ones attention mask, and its hidden "
        "states are reused at every decoder step. Decoding is greedy:")
    c.eq("y_{t} = argmax_{v}  p_{θ}(v | y_{0:t−1}, 𝐮),    y_{0} = decoder start id", key="greedy")
    c.p("and stops when y_{t} is the end-of-sequence or padding id, or when the step limit")
    c.eq("n_{lim} = min( n_{max},  max(16, ⌊3m⌋ + 8) )", key="limit")
    c.p("is reached. The limit is a backstop against runaway, repetitive output: a translation that "
        "exceeds three times the source length plus a constant is almost certainly degenerate, while "
        "the floor of 16 protects very short inputs. Beam search is not used; a beam of k keeps k "
        "hypotheses and roughly multiplies decoder cost by k for a typically modest quality gain, and "
        "RQ3 measures that gain for beam 4 off-device.")
    c.p("The decoder graph's input names are resolved at load time, first by exact match and then by "
        "substring, because the exporter has renamed them between releases and a mismatch otherwise "
        "surfaces as an opaque runtime error. The decoder's own id input is resolved separately among "
        "`input_ids` and `decoder_input_ids` so that it cannot collide with the encoder attention mask, "
        "whose name also contains \"attention_mask\".")

    c.h2("Cost of Decoding without a Key–Value Cache", key="nocache")
    c.p("The decoder is the cache-less export (`use_cache=False`). At step t it receives the whole "
        "prefix y_{0:t−1} of t tokens and recomputes every layer for all t positions; only the last "
        "position's logits are used. If decoding runs for n steps (including the final step that emits "
        "end-of-sequence), the number of decoder positions processed is")
    c.eq("N_{nocache}(n) = Σ_{t=1}^{n} t = n(n + 1) / 2,        N_{cache}(n) = n", key="positions")
    c.p("so the overhead factor on position-proportional work is (n + 1)/2 (analytical; {F:cost}). This "
        "factor applies to the projections and feed-forward layers, whose cost is linear in the number "
        "of positions. Attention terms scale differently, as {T:costterms} shows: self-attention over a "
        "prefix of length t costs O(t^{2}d) when recomputed and O(td) with a cache, so its cumulative "
        "ratio is Σt^{2}/Σt = (2n + 1)/3.")
    c.figure("cost", "decoder_cost", "Decoder positions processed with and without a key–value cache and "
             "their ratio (analytical, from Equation {E:positions}).", width=15.5)
    c.table("costterms", "Cumulative decoder cost over n steps with and without a KV cache (analytical; "
                         "d model width, m source length, V vocabulary size, L layers omitted as a common "
                         "factor)",
            ["Term", "Cache-less (this system)", "With KV cache", "Ratio"],
            [["Projections and feed-forward", "O(d^{2} · n(n+1)/2)", "O(d^{2} · n)", "(n + 1)/2"],
             ["Self-attention", "O(d · n(n+1)(2n+1)/6)", "O(d · n(n+1)/2)", "(2n + 1)/3"],
             ["Cross-attention", "O(d m · n(n+1)/2)", "O(d m · n)", "(n + 1)/2"],
             ["Output projection (logits)", "O(d V · n(n+1)/2)", "O(d V · n)", "(n + 1)/2"],
             ["Logits copied to the JVM", "V · n(n+1)/2 floats", "V · n floats", "(n + 1)/2"]],
            widths=[4.3, 4.6, 3.9, 3.5])
    c.p("The last two rows deserve attention because the vocabulary is large. The exported decoder "
        "computes logits for every position of the prefix, and the implementation copies the full t × V "
        "logit block into a Java array at each step before reading its last row. The fallback pad id in "
        "`MtConfig`, 58100, reflects vocabularies of about 5.8 × 10^{4} entries for the Marian models the "
        "code was written against. Under that assumption, a 32-step decode copies 58 101 × 528 ≈ "
        "3.1 × 10^{7} floats (about 123 MB) cumulatively, with at most 32 × 58 101 × 4 bytes ≈ 7.4 MB "
        "in a single step (analytical). Reading only the last row of the output buffer — or exporting "
        "a decoder that emits only the last position — would remove this transfer without any change "
        "to the model.")
    c.p("Why accept a quadratic cost at all? Because the inputs are OCR lines and short paragraphs, "
        "whose translations are typically tens of tokens long; at n = 16 the position overhead is 8.5 "
        "and at n = 32 it is 16.5 (analytical), which multiplies a per-step cost that is small in "
        "absolute terms for a model of this size. In exchange, the cache-less graph has three inputs "
        "and one output, whereas a cached decoder must thread the key and value tensors of every layer, "
        "for both self- and cross-attention, through every step by name. The trade is sound for short "
        "segments and wrong for long documents; the KV-cached export is the first item of future work, "
        "and RQ4 measures the actual ratio on device.")

    c.h2("Chunking Long Inputs", key="chunk")
    c.p("Transformer translation models degrade past the sequence lengths they were trained on, and "
        "their positional encodings impose a hard limit. A paragraph whose encoding exceeds 192 source "
        "tokens is therefore split at sentence punctuation — `.`, `!`, `?`, `。`, `！`, `？`, `…` and "
        "newline — keeping each delimiter attached to the sentence it ends. Sentences are packed "
        "greedily into chunks: a sentence is appended to the current chunk while the re-encoded "
        "candidate stays within 192 tokens, and otherwise starts a new chunk. A single sentence longer "
        "than the budget is sent whole rather than cut mid-clause, which translates worse than a clean "
        "split but far better than a severed one. Chunk translations are concatenated with a single "
        "space.")
    c.p("Two consequences follow from the implementation. The greedy packer re-encodes the growing "
        "candidate at every step, so packing s sentences costs O(s) encodings of up to 192 tokens each — "
        "negligible in practice. And because chunk outputs are joined with a space irrespective of the "
        "target language, a Chinese or Japanese translation of a paragraph long enough to be chunked "
        "contains a space between sentences where the target orthography would have none; this is a "
        "minor typographic artefact, visible only for long paragraphs.")

    c.h2("Pivot Routing through English", key="pivot")
    c.p("Over 𝓛 = {EN, KO, JA, ZH} there are 4 × 3 = 12 directed pairs. OPUS-MT provides models for the "
        "six English-centric directions; for the six CJK↔CJK directions no model exists. `PivotTranslator` "
        "composes them as ℓ_{s} → EN → ℓ_{t} ({F:pivot}). Its routing rule is:")
    c.steps([
        "If ℓ_{s} = ℓ_{t}, return the input.",
        "If the delegate supports ℓ_{s} → ℓ_{t} directly (both encoder and decoder files exist), use it. "
        "A direct model therefore always takes precedence; dropping a genuine `ko-ja` pair into "
        "`assets/model/mt/ko-ja/` makes the pivot step aside with no code change.",
        "Otherwise, if neither language is English and both legs ℓ_{s} → EN and EN → ℓ_{t} are supported, "
        "translate the whole page with the first leg, then the whole page of English with the second.",
        "Otherwise fail with a message naming the missing leg.",
    ])
    c.figure("pivot", "pivot", "Routing over the four implemented languages: six direct English-centric "
             "pairs and six directions pivoted through English (schematic).", width=12)
    c.p("`isPivoted(from, to)` exposes the decision so that the language picker can label a pivoted "
        "pair (\"via English — slower, lower quality\"). {T:routes} lists all twelve directions. In the "
        "deployed interface, where Korean is hidden, the user can reach four direct and two pivoted "
        "directions (EN↔JA, EN↔ZH direct; JA↔ZH pivoted).")
    rows = []
    for s in ("EN", "KO", "JA", "ZH"):
        for t in ("EN", "KO", "JA", "ZH"):
            if s == t:
                continue
            piv = s != "EN" and t != "EN"
            ui = "KO" not in (s, t)
            rows.append([f"{s} → {t}", "Pivot: " + f"{s.lower()}-en, en-{t.lower()}" if piv
                         else f"Direct: {s.lower()}-{t.lower()}", "2" if piv else "1", "Yes" if ui else "No (KO hidden)"])
    c.table("routes", "Routing of the twelve directed pairs (from `PivotTranslator` and the model tree)",
            ["Direction", "Route (model directories)", "Model passes", "Exposed in UI"], rows,
            widths=[2.8, 6.5, 2.8, 4.2])
    c.h3("Cost of pivoting")
    c.p("A pivoted page costs two encode–decode passes per chunk, so its translation latency is roughly "
        "the sum of the two legs; the second leg's input length is that of the intermediate English, "
        "which may differ from the source length. Memory is unaffected because only one pair is "
        "resident at a time. Model loading, however, interacts with residency: within one page each "
        "leg's pair is loaded once, but for a multi-page PDF translated along a pivoted direction the "
        "resident pair alternates between the two legs, so each page reloads both pairs — 2P loads for "
        "P pages instead of 2 if both pairs could stay resident (analytical). Whether this matters "
        "depends on the load time, which RQ4 measures as cold-start model-load time; keeping both legs "
        "resident during a PDF job is a simple optimisation if it does.")
    c.h3("Error compounding")
    c.p("Pivoting compounds errors in two ways. First, errors of the first leg become the input of the "
        "second, and the second model has no access to the original. Under a crude independence model in "
        "which each leg preserves a given unit of meaning with probability a_{1} and a_{2}, the pivot "
        "preserves it with probability a_{1}a_{2} ≤ min(a_{1}, a_{2}); the pivoted direction is never "
        "better than its weaker leg on such a unit, and the losses multiply. Second, and more "
        "systematically, information that the source and target languages share but English does not "
        "encode is lost at the pivot regardless of model quality. Between Korean and Japanese this "
        "includes speech levels and honorifics, topic marking, frequently omitted subjects that English "
        "forces the first model to make explicit (and sometimes to guess), and Sino-Korean and "
        "Sino-Japanese vocabulary whose direct correspondence is obscured by an English paraphrase. "
        "Between Chinese and Japanese, shared Han-character terms and proper names risk being "
        "transliterated or paraphrased in English and then rendered inconsistently in the target. "
        "RQ3 therefore compares each pivoted direction with a direct NLLB-200-distilled-600M "
        "translation [@nllb2022], a model that does not fit the on-device budget but indicates how much "
        "quality the pivot costs.")
    c.p("One further caveat concerns the English→Japanese leg. The conversion script maps it to the "
        "Hugging Face repository `Helsinki-NLP/opus-mt-en-jap`, whose name uses a three-letter code "
        "rather than the ISO 639-1 code `ja` used for the reverse direction (`opus-mt-ja-en`). The "
        "training data and intended language variety of that checkpoint should be confirmed from its "
        "model card before the RQ3 results for the EN→JA direction, and for every pivoted direction "
        "ending in Japanese, are interpreted.")

    c.h2("Memory Residency and Session Management", key="mtmem")
    c.p("`MarianTranslator.ensureLoaded` keys the resident pair by its directory name (for example "
        "`en-ja`). If the requested pair is already loaded it is reused; otherwise the resident pair's "
        "encoder and decoder sessions are closed before the new pair is created. A loaded pair "
        "comprises the two ONNX sessions, the SentencePiece table, the vocabulary and the configuration. "
        "Each directed pair occupies about 35 MB on disk according to the project documentation; the "
        "resident footprint additionally includes the runtime's working buffers, which RQ4 measures as "
        "peak proportional set size. Sessions use the same threading and optimisation options as the "
        "OCR sessions: max(1, min(4, cores − 1)) intra-operator threads and full graph optimisation.")
    c.table("mtparams", "Translation parameters (from `MarianTranslator`, `SpmEncoder`, `PivotTranslator`)",
            ["Parameter", "Value", "Effect"],
            [["Chunk budget", "192 source tokens", "Longer paragraphs split at sentence punctuation"],
             ["Length limit", "min(n_{max}, max(16, ⌊3m⌋ + 8))", "Backstop against runaway decoding"],
             ["Decoding", "Greedy, no KV cache", "n(n+1)/2 decoder positions"],
             ["Unknown character penalty", "−10", "Guarantees segmentability"],
             ["Boundary marker", "▁ (U+2581)", "Lossless detokenisation"],
             ["Pivot language", "English", "Six CJK↔CJK directions"],
             ["Resident pairs", "1", "≈35 MB per pair on disk"],
             ["Quantisation", "Dynamic int8, per channel", "Set by the conversion script"]],
            widths=[4.3, 5.3, 6.7])
