package com.falcon.ocrtrans.ocr;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import com.falcon.ocrtrans.core.Quad;

import org.junit.Test;

import java.util.List;

/**
 * Covers detection post-processing on synthetic probability maps.
 *
 * <p>Bounds are computed from the raw corner array rather than
 * {@link Quad#bounds()} because that returns an Android {@code RectF}, which is
 * a non-functional stub in a plain JVM test.
 */
public class DbPostProcessorTest {

    /** Fills an axis-aligned rectangle in a probability map with 1.0. */
    private static void fill(float[] map, int w, int x0, int y0, int x1, int y1) {
        for (int y = y0; y < y1; y++) {
            for (int x = x0; x < x1; x++) {
                map[y * w + x] = 1f;
            }
        }
    }

    private static float[] boundsOf(Quad q) {
        float[] p = q.points();
        float minX = p[0], maxX = p[0], minY = p[1], maxY = p[1];
        for (int i = 1; i < 4; i++) {
            minX = Math.min(minX, p[i * 2]);
            maxX = Math.max(maxX, p[i * 2]);
            minY = Math.min(minY, p[i * 2 + 1]);
            maxY = Math.max(maxY, p[i * 2 + 1]);
        }
        return new float[]{minX, minY, maxX, maxY};
    }

    @Test
    public void findsASingleBlock() {
        int w = 100, h = 60;
        float[] map = new float[w * h];
        fill(map, w, 20, 20, 60, 35);

        List<Quad> quads = new DbPostProcessor().extract(map, w, h, 1f, 1f);

        assertEquals(1, quads.size());
        float[] b = boundsOf(quads.get(0));
        // The box is dilated outward, so it must cover the blob and not much more.
        assertTrue("left edge should be at or left of the blob", b[0] <= 20);
        assertTrue("top edge should be at or above the blob", b[1] <= 20);
        assertTrue("right edge should reach the blob", b[2] >= 60);
        assertTrue("bottom edge should reach the blob", b[3] >= 35);
        assertTrue("box should not be wildly oversized", b[2] - b[0] < 70);
    }

    @Test
    public void separatesTwoDistinctBlocks() {
        int w = 120, h = 80;
        float[] map = new float[w * h];
        fill(map, w, 10, 10, 40, 25);
        fill(map, w, 70, 50, 110, 70);

        List<Quad> quads = new DbPostProcessor().extract(map, w, h, 1f, 1f);
        assertEquals(2, quads.size());
    }

    /** The dilation is what stops the box clipping ascenders and end glyphs. */
    @Test
    public void unclipExpandsBeyondTheRawBlob() {
        int w = 80, h = 40;
        float[] map = new float[w * h];
        fill(map, w, 30, 15, 50, 25);

        List<Quad> quads = new DbPostProcessor().extract(map, w, h, 1f, 1f);
        assertEquals(1, quads.size());

        float[] b = boundsOf(quads.get(0));
        assertTrue("expected dilation past the 20px blob width", b[2] - b[0] > 20);
        assertTrue("expected dilation past the 10px blob height", b[3] - b[1] > 10);
    }

    /** Sub-threshold noise must not become a box. */
    @Test
    public void ignoresLowProbabilityNoise() {
        int w = 60, h = 40;
        float[] map = new float[w * h];
        for (int i = 0; i < map.length; i++) {
            map[i] = 0.2f;
        }
        assertTrue(new DbPostProcessor().extract(map, w, h, 1f, 1f).isEmpty());
    }

    /** Specks above threshold but below the area floor are dropped. */
    @Test
    public void ignoresTinyComponents() {
        int w = 60, h = 40;
        float[] map = new float[w * h];
        fill(map, w, 10, 10, 12, 12);

        assertTrue(new DbPostProcessor().extract(map, w, h, 1f, 1f).isEmpty());
    }

    /** Coordinates come back in original-image space, not map space. */
    @Test
    public void scalesResultsBackToSourceResolution() {
        int w = 100, h = 60;
        float[] map = new float[w * h];
        fill(map, w, 20, 20, 60, 35);

        List<Quad> quads = new DbPostProcessor().extract(map, w, h, 4f, 2f);
        assertEquals(1, quads.size());

        float[] b = boundsOf(quads.get(0));
        assertTrue("x should be scaled by 4", b[2] >= 60 * 4 - 1);
        assertTrue("y should be scaled by 2", b[3] >= 35 * 2 - 1);
    }

    @Test
    public void emptyMapYieldsNoBoxes() {
        assertTrue(new DbPostProcessor().extract(new float[0], 0, 0, 1f, 1f).isEmpty());
    }

    /** Raising the binary threshold above the blob's value excludes it. */
    @Test
    public void thresholdIsHonoured() {
        int w = 60, h = 40;
        float[] map = new float[w * h];
        for (int y = 10; y < 25; y++) {
            for (int x = 10; x < 40; x++) {
                map[y * w + x] = 0.7f;
            }
        }
        assertEquals(1, new DbPostProcessor().extract(map, w, h, 1f, 1f).size());
        assertTrue(new DbPostProcessor()
                .setBinaryThreshold(0.8f)
                .extract(map, w, h, 1f, 1f)
                .isEmpty());
    }

    /**
     * The two thresholds are independent: a blob can clear binarization and
     * still be rejected on mean confidence. Pinning this because a value between
     * the two reads as "detected" if you only remember one of them.
     */
    @Test
    public void boxScoreThresholdRejectsLowConfidenceBlobs() {
        int w = 60, h = 40;
        float[] map = new float[w * h];
        for (int y = 10; y < 25; y++) {
            for (int x = 10; x < 40; x++) {
                map[y * w + x] = 0.45f;
            }
        }
        // 0.45 is above the 0.3 binary threshold but below the 0.6 box threshold.
        assertTrue(new DbPostProcessor().extract(map, w, h, 1f, 1f).isEmpty());
        assertEquals(1, new DbPostProcessor()
                .setBoxThreshold(0.4f)
                .extract(map, w, h, 1f, 1f)
                .size());
    }
}
