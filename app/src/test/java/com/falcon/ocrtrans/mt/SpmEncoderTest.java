package com.falcon.ocrtrans.mt;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Covers the SentencePiece reimplementation.
 *
 * <p>A wrong segmentation here produces valid token ids and fluent-looking
 * output that simply is not a translation of the input, so these cases pin the
 * behaviour that would otherwise fail silently.
 */
public class SpmEncoderTest {

    private static final char M = SpmEncoder.SPACE_MARKER;

    /** Prefers one high-scoring long piece over two cheap short ones. */
    @Test
    public void viterbiPrefersHigherScoringSegmentation() {
        Map<String, Float> pieces = new HashMap<>();
        pieces.put(M + "hello", -1.0f);
        pieces.put(M + "hel", -5.0f);
        pieces.put("lo", -5.0f);

        SpmEncoder encoder = SpmEncoder.fromPieces(pieces);
        List<String> out = encoder.encodeToPieces(M + "hello");

        assertEquals(Arrays.asList(M + "hello"), out);
    }

    /** When the long piece is poor, the split wins on total score. */
    @Test
    public void viterbiSplitsWhenThatScoresBetter() {
        Map<String, Float> pieces = new HashMap<>();
        pieces.put(M + "hello", -20.0f);
        pieces.put(M + "hel", -1.0f);
        pieces.put("lo", -1.0f);

        SpmEncoder encoder = SpmEncoder.fromPieces(pieces);
        List<String> out = encoder.encodeToPieces(M + "hello");

        assertEquals(Arrays.asList(M + "hel", "lo"), out);
    }

    /**
     * An unseen character must not make the sentence unsegmentable — the
     * single-character fallback has to keep the lattice connected.
     */
    @Test
    public void unknownCharacterFallsBackToSingleChar() {
        Map<String, Float> pieces = new HashMap<>();
        pieces.put(M + "ab", -1.0f);

        SpmEncoder encoder = SpmEncoder.fromPieces(pieces);
        List<String> out = encoder.encodeToPieces(M + "abZ");

        assertEquals(Arrays.asList(M + "ab", "Z"), out);
    }

    @Test
    public void normalizePrefixesMarkerAndReplacesSpaces() {
        assertEquals(M + "hello" + M + "world", SpmEncoder.normalize("hello world"));
    }

    /** Runs of whitespace collapse, and the string is trimmed, before marking. */
    @Test
    public void normalizeCollapsesWhitespace() {
        assertEquals(M + "a" + M + "b", SpmEncoder.normalize("  a \t\n b  "));
    }

    @Test
    public void normalizeReturnsEmptyForBlankInput() {
        assertEquals("", SpmEncoder.normalize("   "));
        assertTrue(SpmEncoder.fromPieces(new HashMap<>()).encodeToPieces("").isEmpty());
    }

    /** NFKC folds full-width Latin onto ASCII, as the reference tokenizer does. */
    @Test
    public void normalizeAppliesNfkc() {
        assertEquals(M + "AB", SpmEncoder.normalize("ＡＢ"));
    }

    @Test
    public void decodePiecesRestoresSpaces() {
        assertEquals("hello world",
                SpmEncoder.decodePieces(Arrays.asList(M + "hello", M + "wor", "ld")));
    }
}
