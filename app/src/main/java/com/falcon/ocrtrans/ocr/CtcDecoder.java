package com.falcon.ocrtrans.ocr;

import androidx.annotation.NonNull;

/**
 * Greedy CTC decoding of a recognition head's output.
 *
 * <p>The network emits one class distribution per horizontal timestep, and a
 * single glyph usually spans several of them. Collapsing consecutive identical
 * predictions and then dropping the blank class recovers the string; the blank
 * is what lets a genuine double letter survive, since {@code l-blank-l} collapses
 * to {@code ll} while {@code l-l} collapses to {@code l}.
 */
public final class CtcDecoder {

    /** One decoded line and how confident the network was about it. */
    public static final class Decoded {
        public final String text;
        public final float confidence;

        Decoded(String text, float confidence) {
            this.text = text;
            this.confidence = confidence;
        }
    }

    private CtcDecoder() {
    }

    /**
     * @param logits flattened {@code [T][C]} for one line; already softmaxed by
     *               PP-OCR's exported graph, so values are probabilities
     * @param steps  T
     * @param classes C
     */
    @NonNull
    public static Decoded decode(@NonNull float[] logits, int steps, int classes, @NonNull CharDict dict) {
        StringBuilder sb = new StringBuilder(steps);
        double confSum = 0;
        int confCount = 0;
        int previous = -1;

        for (int t = 0; t < steps; t++) {
            int base = t * classes;
            int best = 0;
            float bestVal = logits[base];
            for (int c = 1; c < classes; c++) {
                float v = logits[base + c];
                if (v > bestVal) {
                    bestVal = v;
                    best = c;
                }
            }
            // Collapse the run first, then discard blanks.
            if (best != previous && !dict.isBlank(best)) {
                sb.append(dict.labelAt(best));
                confSum += bestVal;
                confCount++;
            }
            previous = best;
        }

        float confidence = confCount > 0 ? (float) (confSum / confCount) : 0f;
        return new Decoded(sb.toString(), confidence);
    }
}
