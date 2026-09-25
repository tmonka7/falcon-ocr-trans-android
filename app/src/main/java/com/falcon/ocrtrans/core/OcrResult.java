package com.falcon.ocrtrans.core;

import androidx.annotation.NonNull;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Everything recognised on one page or photo, plus the geometry it came from. */
public final class OcrResult {

    private final List<TextLine> lines;
    private final List<Paragraph> paragraphs;
    private final int imageWidth;
    private final int imageHeight;
    private final long elapsedMillis;

    public OcrResult(@NonNull List<TextLine> lines,
                     @NonNull List<Paragraph> paragraphs,
                     int imageWidth,
                     int imageHeight,
                     long elapsedMillis) {
        this.lines = new ArrayList<>(lines);
        this.paragraphs = new ArrayList<>(paragraphs);
        this.imageWidth = imageWidth;
        this.imageHeight = imageHeight;
        this.elapsedMillis = elapsedMillis;
    }

    public static OcrResult empty(int w, int h) {
        return new OcrResult(Collections.emptyList(), Collections.emptyList(), w, h, 0L);
    }

    @NonNull
    public List<TextLine> lines() {
        return Collections.unmodifiableList(lines);
    }

    @NonNull
    public List<Paragraph> paragraphs() {
        return Collections.unmodifiableList(paragraphs);
    }

    public int imageWidth() {
        return imageWidth;
    }

    public int imageHeight() {
        return imageHeight;
    }

    public long elapsedMillis() {
        return elapsedMillis;
    }

    public boolean isEmpty() {
        return lines.isEmpty();
    }

    /** All recognised source text, one paragraph per line break. */
    @NonNull
    public String plainText() {
        StringBuilder sb = new StringBuilder();
        for (Paragraph p : paragraphs) {
            if (sb.length() > 0) {
                sb.append('\n');
            }
            sb.append(p.sourceText());
        }
        return sb.toString();
    }

    /** All translated text, one paragraph per line break. */
    @NonNull
    public String translatedText() {
        StringBuilder sb = new StringBuilder();
        for (Paragraph p : paragraphs) {
            if (sb.length() > 0) {
                sb.append('\n');
            }
            sb.append(p.translatedText());
        }
        return sb.toString();
    }
}
