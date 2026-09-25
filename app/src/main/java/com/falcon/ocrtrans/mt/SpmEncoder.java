package com.falcon.ocrtrans.mt;

import android.content.Context;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.util.Assets;

import java.io.IOException;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * A SentencePiece <em>unigram</em> tokenizer, in pure Java.
 *
 * <p>SentencePiece ships its model as a protobuf that the C++ library parses;
 * rather than reimplement that here, {@code tools/convert_mt.py} flattens it to
 * a two-column TSV of {@code piece<TAB>logProbability} and this class consumes
 * that. The segmentation itself is unchanged: a unigram model scores a
 * tokenisation as the sum of its pieces' log probabilities, so the best
 * segmentation is a shortest-path problem and Viterbi solves it exactly.
 *
 * <p>Getting this wrong is quiet rather than loud — a subtly different
 * segmentation still produces valid ids, and the model still emits fluent text,
 * just not a translation of what you asked for.
 */
public final class SpmEncoder {

    /** SentencePiece marks a word boundary with U+2581, "lower one eighth block". */
    static final char SPACE_MARKER = '▁';

    /** Cost charged for falling back to a single unknown character. */
    private static final float UNK_PENALTY = -10f;

    private final Map<String, Float> pieceScores;
    private final int maxPieceLength;

    private SpmEncoder(Map<String, Float> pieceScores, int maxPieceLength) {
        this.pieceScores = pieceScores;
        this.maxPieceLength = maxPieceLength;
    }

    /**
     * Builds an encoder from an in-memory piece table.
     *
     * <p>Exists so the Viterbi segmentation can be unit tested against a small
     * hand-written vocabulary, without an asset manager or a 60k-entry model.
     */
    @NonNull
    static SpmEncoder fromPieces(@NonNull Map<String, Float> pieceScores) {
        int maxLen = 1;
        for (String piece : pieceScores.keySet()) {
            maxLen = Math.max(maxLen, piece.length());
        }
        return new SpmEncoder(new HashMap<>(pieceScores), maxLen);
    }

    /** Loads a {@code piece<TAB>score} table produced by the conversion script. */
    @NonNull
    public static SpmEncoder load(@NonNull Context ctx, @NonNull String assetPath) throws IOException {
        List<String> lines = Assets.readLines(ctx, assetPath);
        Map<String, Float> scores = new HashMap<>(lines.size() * 2);
        int maxLen = 1;

        for (String line : lines) {
            if (line.isEmpty()) {
                continue;
            }
            int tab = line.indexOf('\t');
            if (tab <= 0) {
                continue;
            }
            String piece = line.substring(0, tab);
            float score;
            try {
                score = Float.parseFloat(line.substring(tab + 1).trim());
            } catch (NumberFormatException e) {
                continue;
            }
            scores.put(piece, score);
            maxLen = Math.max(maxLen, piece.length());
        }
        if (scores.isEmpty()) {
            throw new IOException("no SentencePiece entries in " + assetPath);
        }
        return new SpmEncoder(scores, maxLen);
    }

    /**
     * Applies SentencePiece's default normalisation: NFKC, collapse runs of
     * whitespace, then replace each space with the boundary marker and prefix
     * the string with one.
     *
     * <p>The leading marker ("add_dummy_prefix") is what makes the first word of
     * a sentence tokenise identically to the same word mid-sentence.
     */
    @NonNull
    public static String normalize(@NonNull String text) {
        String n = Normalizer.normalize(text, Normalizer.Form.NFKC);
        n = n.replaceAll("\\s+", " ").trim();
        if (n.isEmpty()) {
            return "";
        }
        return SPACE_MARKER + n.replace(' ', SPACE_MARKER);
    }

    /**
     * Segments already-normalised text into pieces by Viterbi.
     *
     * <p>{@code best[i]} is the score of the best segmentation of the first
     * {@code i} characters; each position is reached by trying every piece that
     * could end there, capped at the longest piece in the vocabulary.
     */
    @NonNull
    public List<String> encodeToPieces(@NonNull String normalized) {
        int n = normalized.length();
        List<String> out = new ArrayList<>();
        if (n == 0) {
            return out;
        }

        float[] best = new float[n + 1];
        int[] backPiece = new int[n + 1];
        java.util.Arrays.fill(best, Float.NEGATIVE_INFINITY);
        best[0] = 0f;

        for (int end = 1; end <= n; end++) {
            int earliest = Math.max(0, end - maxPieceLength);
            for (int start = earliest; start < end; start++) {
                if (best[start] == Float.NEGATIVE_INFINITY) {
                    continue;
                }
                String candidate = normalized.substring(start, end);
                Float score = pieceScores.get(candidate);
                float value;
                if (score != null) {
                    value = best[start] + score;
                } else if (end - start == 1) {
                    // Always leave a single-character escape hatch so an unseen
                    // glyph cannot make the whole sentence unsegmentable.
                    value = best[start] + UNK_PENALTY;
                } else {
                    continue;
                }
                if (value > best[end]) {
                    best[end] = value;
                    backPiece[end] = start;
                }
            }
        }

        // Walk the back-pointers from the end, then reverse.
        int pos = n;
        List<String> reversed = new ArrayList<>();
        while (pos > 0) {
            int start = backPiece[pos];
            reversed.add(normalized.substring(start, pos));
            pos = start;
        }
        for (int i = reversed.size() - 1; i >= 0; i--) {
            out.add(reversed.get(i));
        }
        return out;
    }

    @NonNull
    public List<String> encode(@NonNull String rawText) {
        return encodeToPieces(normalize(rawText));
    }

    /** Reverses {@link #normalize}: joins pieces and restores real spaces. */
    @NonNull
    public static String decodePieces(@NonNull List<String> pieces) {
        StringBuilder sb = new StringBuilder();
        for (String p : pieces) {
            sb.append(p);
        }
        return sb.toString().replace(SPACE_MARKER, ' ').trim();
    }
}
