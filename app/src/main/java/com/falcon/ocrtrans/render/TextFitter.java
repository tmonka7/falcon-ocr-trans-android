package com.falcon.ocrtrans.render;

import android.text.Layout;
import android.text.StaticLayout;
import android.text.TextPaint;

import androidx.annotation.NonNull;

/**
 * Chooses the largest text size at which a translation still fits the box the
 * original text occupied.
 *
 * <p>Translations change length — English into Korean or Japanese typically
 * shortens, the reverse typically expands, and German-style compounds can double
 * a line. Reusing the source font size therefore overflows the box often enough
 * to be the norm rather than the exception, so the size is searched for instead.
 */
public final class TextFitter {

    /** Never shrink below this fraction of the original size; illegible past it. */
    private static final float MIN_SCALE = 0.45f;
    /** Never grow past this fraction, or short translations look shouty. */
    private static final float MAX_SCALE = 1.15f;
    /** Binary search terminates once the bracket is this narrow, in pixels. */
    private static final float PRECISION = 0.25f;

    /** A chosen size and the laid-out text at that size. */
    public static final class Fit {
        public final StaticLayout layout;
        public final float textSize;
        /** True when even {@link #MIN_SCALE} overflowed; the text then runs past the box. */
        public final boolean overflowed;

        Fit(StaticLayout layout, float textSize, boolean overflowed) {
            this.layout = layout;
            this.textSize = textSize;
            this.overflowed = overflowed;
        }
    }

    private TextFitter() {
    }

    /**
     * @param paint     styled paint; its text size is overwritten during the search
     * @param preferred the source text's size, used as the upper anchor
     */
    @NonNull
    public static Fit fit(@NonNull CharSequence text,
                          @NonNull TextPaint paint,
                          int width,
                          int height,
                          float preferred,
                          @NonNull Layout.Alignment alignment) {
        int safeWidth = Math.max(1, width);
        int safeHeight = Math.max(1, height);

        float low = Math.max(4f, preferred * MIN_SCALE);
        float high = Math.max(low, preferred * MAX_SCALE);

        // If even the smallest permitted size overflows, use it anyway and flag
        // it: overflowing text beats a blank region where text was. The caller
        // sets no clip, so the overflow runs past the bottom of the box.
        paint.setTextSize(low);
        StaticLayout smallest = build(text, paint, safeWidth, alignment);
        if (smallest.getHeight() > safeHeight) {
            return new Fit(smallest, low, true);
        }

        StaticLayout best = smallest;
        float bestSize = low;

        while (high - low > PRECISION) {
            float mid = (low + high) / 2f;
            paint.setTextSize(mid);
            StaticLayout candidate = build(text, paint, safeWidth, alignment);
            if (candidate.getHeight() <= safeHeight) {
                best = candidate;
                bestSize = mid;
                low = mid;
            } else {
                high = mid;
            }
        }

        paint.setTextSize(bestSize);
        return new Fit(best, bestSize, false);
    }

    private static StaticLayout build(CharSequence text, TextPaint paint, int width,
                                      Layout.Alignment alignment) {
        return StaticLayout.Builder
                .obtain(text, 0, text.length(), paint, width)
                .setAlignment(alignment)
                .setLineSpacing(0f, 1.0f)
                .setIncludePad(false)
                // Without this, CJK text wraps only at spaces — which CJK does not
                // use — and a translated paragraph becomes one unbroken line.
                .setBreakStrategy(Layout.BREAK_STRATEGY_HIGH_QUALITY)
                .setHyphenationFrequency(Layout.HYPHENATION_FREQUENCY_NONE)
                .build();
    }
}
