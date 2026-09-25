package com.falcon.ocrtrans.core;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

/**
 * One recognised line of text: where it sits on the page, what it says, and —
 * once translation has run — what it should say instead.
 *
 * <p>The colours are sampled from the source image rather than assumed, so the
 * renderer can repaint the translation in the original ink over the original
 * background instead of the usual black-on-white patch.
 */
public final class TextLine {

    private final Quad quad;
    private final String text;
    private final float confidence;

    @Nullable
    private String translation;

    /** ARGB of the glyph strokes, sampled from the darkest pixels in the box. */
    private int foregroundColor = 0xFF000000;
    /** ARGB of the paper behind the glyphs, sampled from the box border. */
    private int backgroundColor = 0xFFFFFFFF;
    /** True when the box is taller than it is wide — CJK vertical typesetting. */
    private boolean vertical;

    public TextLine(@NonNull Quad quad, @NonNull String text, float confidence) {
        this.quad = quad;
        this.text = text;
        this.confidence = confidence;
        this.vertical = quad.height() > quad.width() * 1.8f;
    }

    @NonNull
    public Quad quad() {
        return quad;
    }

    @NonNull
    public String text() {
        return text;
    }

    public float confidence() {
        return confidence;
    }

    @Nullable
    public String translation() {
        return translation;
    }

    public void setTranslation(@Nullable String translation) {
        this.translation = translation;
    }

    /** The translation when present, otherwise the recognised source text. */
    @NonNull
    public String displayText() {
        return translation != null && !translation.isEmpty() ? translation : text;
    }

    public int foregroundColor() {
        return foregroundColor;
    }

    public int backgroundColor() {
        return backgroundColor;
    }

    public void setColors(int foreground, int background) {
        this.foregroundColor = foreground;
        this.backgroundColor = background;
    }

    public boolean isVertical() {
        return vertical;
    }

    public void setVertical(boolean vertical) {
        this.vertical = vertical;
    }

    @NonNull
    @Override
    public String toString() {
        return "TextLine{" + text + " @ " + quad + ", conf=" + confidence + '}';
    }
}
