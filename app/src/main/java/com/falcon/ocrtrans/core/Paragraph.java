package com.falcon.ocrtrans.core;

import androidx.annotation.NonNull;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * A run of {@link TextLine}s that belong to the same block of prose.
 *
 * <p>Translating line by line produces nonsense whenever a sentence wraps: an MT
 * model handed {@code "Please scan the QR code"} and {@code "for more information."}
 * as two independent inputs loses the dependency between them. Grouping lines
 * into paragraphs first, translating the joined text, then reflowing the result
 * back across the original line boxes is what keeps the output readable and the
 * layout intact.
 */
public final class Paragraph {

    private final List<TextLine> lines = new ArrayList<>();

    @NonNull
    private String sourceText = "";

    @NonNull
    private String translatedText = "";

    public void addLine(@NonNull TextLine line) {
        lines.add(line);
    }

    @NonNull
    public List<TextLine> lines() {
        return Collections.unmodifiableList(lines);
    }

    public boolean isEmpty() {
        return lines.isEmpty();
    }

    /**
     * Joins the member lines into a single string for the translator.
     *
     * <p>Latin scripts get a space at the wrap point; CJK scripts do not, because
     * a space between two Han or Kana characters is a real character there rather
     * than a word boundary artefact.
     */
    @NonNull
    public String buildSourceText() {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < lines.size(); i++) {
            String t = lines.get(i).text();
            if (i > 0 && sb.length() > 0) {
                char prev = sb.charAt(sb.length() - 1);
                char next = t.isEmpty() ? ' ' : t.charAt(0);
                if (!isCjk(prev) || !isCjk(next)) {
                    sb.append(' ');
                }
            }
            sb.append(t);
        }
        sourceText = sb.toString().trim();
        return sourceText;
    }

    @NonNull
    public String sourceText() {
        return sourceText;
    }

    @NonNull
    public String translatedText() {
        return translatedText;
    }

    public void setTranslatedText(@NonNull String translatedText) {
        this.translatedText = translatedText;
    }

    /** Union of every member line's bounds, in image pixels. */
    @NonNull
    public android.graphics.RectF bounds() {
        android.graphics.RectF out = new android.graphics.RectF(
                Float.MAX_VALUE, Float.MAX_VALUE, -Float.MAX_VALUE, -Float.MAX_VALUE);
        for (TextLine l : lines) {
            out.union(l.quad().bounds());
        }
        return out;
    }

    /** Median line height — the basis for the replacement font size. */
    public float medianLineHeight() {
        if (lines.isEmpty()) {
            return 0f;
        }
        float[] h = new float[lines.size()];
        for (int i = 0; i < lines.size(); i++) {
            h[i] = lines.get(i).quad().height();
        }
        java.util.Arrays.sort(h);
        return h[h.length / 2];
    }

    public static boolean isCjk(char c) {
        Character.UnicodeBlock b = Character.UnicodeBlock.of(c);
        return b == Character.UnicodeBlock.CJK_UNIFIED_IDEOGRAPHS
                || b == Character.UnicodeBlock.CJK_UNIFIED_IDEOGRAPHS_EXTENSION_A
                || b == Character.UnicodeBlock.CJK_SYMBOLS_AND_PUNCTUATION
                || b == Character.UnicodeBlock.HIRAGANA
                || b == Character.UnicodeBlock.KATAKANA
                || b == Character.UnicodeBlock.HANGUL_SYLLABLES
                || b == Character.UnicodeBlock.HANGUL_JAMO
                || b == Character.UnicodeBlock.HANGUL_COMPATIBILITY_JAMO
                || b == Character.UnicodeBlock.HALFWIDTH_AND_FULLWIDTH_FORMS;
    }
}
