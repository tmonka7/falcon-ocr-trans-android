package com.falcon.ocrtrans.ocr;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.Test;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;

/** Covers CTC collapsing and the dictionary index arithmetic it depends on. */
public class CtcDecoderTest {

    /** Classes: 0 blank, 1 'a', 2 'b', 3 'c', 4 space. */
    private static CharDict dict() throws IOException {
        List<String> glyphs = Arrays.asList("a", "b", "c");
        return CharDict.fromGlyphs(glyphs, 5, "test");
    }

    /** One-hot timestep at the given class. */
    private static void set(float[] logits, int step, int classes, int cls) {
        logits[step * classes + cls] = 1f;
    }

    @Test
    public void collapsesRepeatsAndDropsBlanks() throws Exception {
        int classes = 5;
        int steps = 6;
        float[] logits = new float[steps * classes];
        // a a blank b b c  ->  "abc"
        set(logits, 0, classes, 1);
        set(logits, 1, classes, 1);
        set(logits, 2, classes, 0);
        set(logits, 3, classes, 2);
        set(logits, 4, classes, 2);
        set(logits, 5, classes, 3);

        CtcDecoder.Decoded out = CtcDecoder.decode(logits, steps, classes, dict());
        assertEquals("abc", out.text);
    }

    /**
     * The whole point of the blank class: it separates a genuine double letter
     * from one glyph spread over several timesteps.
     */
    @Test
    public void blankSeparatesDoubledCharacters() throws Exception {
        int classes = 5;
        int steps = 3;
        float[] logits = new float[steps * classes];
        // a blank a  ->  "aa"
        set(logits, 0, classes, 1);
        set(logits, 1, classes, 0);
        set(logits, 2, classes, 1);

        assertEquals("aa", CtcDecoder.decode(logits, steps, classes, dict()).text);
    }

    @Test
    public void withoutBlankRepeatsCollapseToOne() throws Exception {
        int classes = 5;
        int steps = 2;
        float[] logits = new float[steps * classes];
        set(logits, 0, classes, 1);
        set(logits, 1, classes, 1);

        assertEquals("a", CtcDecoder.decode(logits, steps, classes, dict()).text);
    }

    @Test
    public void allBlankYieldsEmptyTextAndZeroConfidence() throws Exception {
        int classes = 5;
        int steps = 4;
        float[] logits = new float[steps * classes];
        for (int t = 0; t < steps; t++) {
            set(logits, t, classes, 0);
        }
        CtcDecoder.Decoded out = CtcDecoder.decode(logits, steps, classes, dict());
        assertEquals("", out.text);
        assertEquals(0f, out.confidence, 1e-6);
    }

    /** The last class is the trailing space when the model was trained with one. */
    @Test
    public void trailingClassIsSpace() throws Exception {
        CharDict d = dict();
        assertEquals("a", d.labelAt(1));
        assertEquals("c", d.labelAt(3));
        assertEquals(" ", d.labelAt(4));
        assertTrue(d.isBlank(0));
    }

    /** Without a space class the table is exactly blank plus the glyphs. */
    @Test
    public void dictionaryWithoutSpaceClassIsAccepted() throws Exception {
        CharDict d = CharDict.fromGlyphs(Arrays.asList("a", "b", "c"), 4, "test");
        assertEquals(4, d.size());
        assertEquals("c", d.labelAt(3));
    }

    /**
     * A dictionary that cannot fit the model's class count is the failure that
     * would otherwise shift every character in every result, so it must throw.
     */
    @Test
    public void mismatchedDictionaryIsRejected() {
        try {
            CharDict.fromGlyphs(Arrays.asList("a", "b", "c"), 99, "test");
            fail("expected an IOException for a dictionary that fits no class count");
        } catch (IOException expected) {
            assertTrue(expected.getMessage().contains("99"));
        }
    }

    /** A stray blank final line from the exporter must not shift the indices. */
    @Test
    public void trailingEmptyLineIsIgnored() throws Exception {
        CharDict d = CharDict.fromGlyphs(Arrays.asList("a", "b", "c", ""), 5, "test");
        assertEquals("c", d.labelAt(3));
        assertEquals(" ", d.labelAt(4));
    }
}
