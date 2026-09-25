package com.falcon.ocrtrans.ocr;

import android.content.Context;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.util.Assets;

import java.io.IOException;
import java.util.List;

/**
 * The character set a recognition head emits, indexed by class id.
 *
 * <p>PP-OCR dictionary files list only the glyphs. The label set the network
 * actually predicts is <em>that list wrapped in two extras</em>: a CTC blank at
 * index 0, and — when the model was trained with {@code use_space_char} — a
 * space appended at the end. Off-by-one here does not throw; it silently shifts
 * every character in every result, so the size is reconciled against the model's
 * own output dimension at load time.
 */
public final class CharDict {

    private final String[] labels;

    private CharDict(String[] labels) {
        this.labels = labels;
    }

    /**
     * @param numClasses the recognition head's output channel count, used to
     *                   decide whether a trailing space class is present
     */
    @NonNull
    public static CharDict load(@NonNull Context ctx, @NonNull String assetPath, int numClasses)
            throws IOException {
        return fromGlyphs(Assets.readLines(ctx, assetPath), numClasses, assetPath);
    }

    /**
     * Builds the label table from an already-read glyph list.
     *
     * <p>Split out from {@link #load} so the index arithmetic — the part that
     * fails silently rather than loudly — can be unit tested without an asset
     * manager.
     */
    @NonNull
    static CharDict fromGlyphs(@NonNull List<String> rawGlyphs, int numClasses, @NonNull String origin)
            throws IOException {
        List<String> glyphs = new java.util.ArrayList<>(rawGlyphs);

        // Some dictionary files end with a stray blank line from the exporter;
        // that is not a space class and must not shift the indices.
        while (!glyphs.isEmpty() && glyphs.get(glyphs.size() - 1).isEmpty()) {
            glyphs.remove(glyphs.size() - 1);
        }

        int expectedWithSpace = glyphs.size() + 2;
        int expectedNoSpace = glyphs.size() + 1;
        if (numClasses != expectedWithSpace && numClasses != expectedNoSpace) {
            throw new IOException("dictionary " + origin + " has " + glyphs.size()
                    + " glyphs, which fits neither " + expectedNoSpace + " nor "
                    + expectedWithSpace + " classes; the model reports " + numClasses
                    + ". The dict and the .onnx are from different exports.");
        }

        String[] labels = new String[numClasses];
        labels[0] = "";
        for (int i = 1; i < numClasses; i++) {
            int g = i - 1;
            labels[i] = g < glyphs.size() ? glyphs.get(g) : " ";
        }
        return new CharDict(labels);
    }

    public int size() {
        return labels.length;
    }

    /** @return the glyph for a class id; the empty string for blank. */
    @NonNull
    public String labelAt(int index) {
        return index >= 0 && index < labels.length ? labels[index] : "";
    }

    public boolean isBlank(int index) {
        return index == 0;
    }
}
