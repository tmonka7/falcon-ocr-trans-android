package com.falcon.ocrtrans.ocr;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.core.Quad;

import java.util.ArrayList;
import java.util.List;

/**
 * Turns the detector's per-pixel probability map into rotated text boxes.
 *
 * <p>This is the Differentiable Binarization post-process that PP-OCR pairs with
 * its detection head. Upstream runs it in C++ on OpenCV contours and the Vatti
 * clipper; this is a pure-Java equivalent built from three pieces:
 *
 * <ol>
 *   <li>threshold the map and flood-fill it into connected components;
 *   <li>wrap each component in its minimum-area rectangle, via a convex hull and
 *       rotating calipers — the rectangle beats the raw contour here because the
 *       renderer needs a baseline angle, not a blob outline;
 *   <li>dilate that rectangle outward, because the network is trained to predict
 *       a <em>shrunk</em> version of each text region, so the raw box reliably
 *       clips ascenders and the first and last glyph.
 * </ol>
 */
public final class DbPostProcessor {

    /** Pixels above this are text; the standard operating point for PP-OCR. */
    private float binaryThreshold = 0.3f;
    /** Mean confidence a whole box must reach to survive. */
    private float boxThreshold = 0.6f;
    /** How far to dilate the shrunk prediction back out. */
    private float unclipRatio = 1.6f;
    /** Discards specks: components smaller than this many pixels. */
    private int minComponentArea = 12;
    /** Discards slivers: boxes whose short side is under this many pixels. */
    private float minBoxSide = 3f;
    /** Safety valve on pathological maps. */
    private int maxCandidates = 1000;

    public DbPostProcessor setBinaryThreshold(float v) {
        this.binaryThreshold = v;
        return this;
    }

    public DbPostProcessor setBoxThreshold(float v) {
        this.boxThreshold = v;
        return this;
    }

    public DbPostProcessor setUnclipRatio(float v) {
        this.unclipRatio = v;
        return this;
    }

    public DbPostProcessor setMinComponentArea(int v) {
        this.minComponentArea = v;
        return this;
    }

    /**
     * @param prob   probability map, row-major, length {@code w*h}, values in [0,1]
     * @param w      map width
     * @param h      map height
     * @param scaleX multiply x by this to reach original-image pixels
     * @param scaleY multiply y by this to reach original-image pixels
     */
    @NonNull
    public List<Quad> extract(@NonNull float[] prob, int w, int h, float scaleX, float scaleY) {
        List<Quad> out = new ArrayList<>();
        if (w <= 0 || h <= 0 || prob.length < w * h) {
            return out;
        }

        boolean[] visited = new boolean[w * h];
        int[] stack = new int[Math.max(64, Math.min(w * h, 1 << 16))];
        IntBag component = new IntBag(256);

        for (int seed = 0; seed < w * h; seed++) {
            if (visited[seed] || prob[seed] < binaryThreshold) {
                continue;
            }
            component.clear();

            // Iterative flood fill: recursion would blow the stack on a full-page
            // paragraph, which is routinely a component of 100k+ pixels.
            int sp = 0;
            stack[sp++] = seed;
            visited[seed] = true;

            while (sp > 0) {
                int idx = stack[--sp];
                component.add(idx);

                int x = idx % w;
                int y = idx / w;
                // 8-connectivity keeps diagonally-touching strokes in one glyph run.
                for (int dy = -1; dy <= 1; dy++) {
                    int ny = y + dy;
                    if (ny < 0 || ny >= h) {
                        continue;
                    }
                    for (int dx = -1; dx <= 1; dx++) {
                        int nx = x + dx;
                        if ((dx | dy) == 0 || nx < 0 || nx >= w) {
                            continue;
                        }
                        int nIdx = ny * w + nx;
                        if (visited[nIdx] || prob[nIdx] < binaryThreshold) {
                            continue;
                        }
                        visited[nIdx] = true;
                        if (sp == stack.length) {
                            int[] bigger = new int[stack.length * 2];
                            System.arraycopy(stack, 0, bigger, 0, stack.length);
                            stack = bigger;
                        }
                        stack[sp++] = nIdx;
                    }
                }
            }

            if (component.size() < minComponentArea) {
                continue;
            }
            Quad box = boxFor(component, prob, w, h);
            if (box != null) {
                out.add(box.scaled(scaleX, scaleY));
                if (out.size() >= maxCandidates) {
                    break;
                }
            }
        }
        return out;
    }

    /** Scores one component and returns its dilated minimum-area rectangle. */
    private Quad boxFor(IntBag component, float[] prob, int w, int h) {
        int n = component.size();
        int[] data = component.data();

        int minX = Integer.MAX_VALUE, maxX = Integer.MIN_VALUE;
        int minY = Integer.MAX_VALUE, maxY = Integer.MIN_VALUE;
        for (int i = 0; i < n; i++) {
            int x = data[i] % w;
            int y = data[i] / w;
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        }

        // Mean probability over the component's own pixels. Upstream averages the
        // bounding box instead; restricting it to the component avoids punishing
        // a diagonal line of text for the empty corners of its bounding box.
        double sum = 0;
        for (int i = 0; i < n; i++) {
            sum += prob[data[i]];
        }
        if (sum / n < boxThreshold) {
            return null;
        }

        // The hull needs the component's outline, not its interior. Keeping only
        // the leftmost and rightmost pixel per row cuts a 100k-pixel paragraph
        // down to a few hundred candidates without changing the hull at all.
        int rows = maxY - minY + 1;
        int[] rowMin = new int[rows];
        int[] rowMax = new int[rows];
        java.util.Arrays.fill(rowMin, Integer.MAX_VALUE);
        java.util.Arrays.fill(rowMax, Integer.MIN_VALUE);
        for (int i = 0; i < n; i++) {
            int x = data[i] % w;
            int r = data[i] / w - minY;
            if (x < rowMin[r]) rowMin[r] = x;
            if (x > rowMax[r]) rowMax[r] = x;
        }

        int[] px = new int[rows * 2];
        int[] py = new int[rows * 2];
        int m = 0;
        for (int r = 0; r < rows; r++) {
            if (rowMin[r] == Integer.MAX_VALUE) {
                continue;
            }
            px[m] = rowMin[r];
            py[m] = minY + r;
            m++;
            if (rowMax[r] != rowMin[r]) {
                px[m] = rowMax[r];
                py[m] = minY + r;
                m++;
            }
        }
        if (m < 3) {
            return null;
        }

        int[] hull = convexHull(px, py, m);
        float[] rect = minAreaRect(px, py, hull);
        if (rect == null) {
            return null;
        }
        return unclip(rect, w, h);
    }

    /**
     * Andrew's monotone chain hull.
     *
     * @return indices into {@code px}/{@code py}, counter-clockwise, no duplicate
     *         endpoint
     */
    private static int[] convexHull(int[] px, int[] py, int n) {
        Integer[] order = new Integer[n];
        for (int i = 0; i < n; i++) {
            order[i] = i;
        }
        java.util.Arrays.sort(order, (a, b) -> px[a] != px[b]
                ? Integer.compare(px[a], px[b])
                : Integer.compare(py[a], py[b]));

        int[] hull = new int[n * 2];
        int k = 0;
        for (int i = 0; i < n; i++) {
            int p = order[i];
            while (k >= 2 && cross(px, py, hull[k - 2], hull[k - 1], p) <= 0) {
                k--;
            }
            hull[k++] = p;
        }
        int lower = k + 1;
        for (int i = n - 2; i >= 0; i--) {
            int p = order[i];
            while (k >= lower && cross(px, py, hull[k - 2], hull[k - 1], p) <= 0) {
                k--;
            }
            hull[k++] = p;
        }
        int[] out = new int[Math.max(1, k - 1)];
        System.arraycopy(hull, 0, out, 0, out.length);
        return out;
    }

    private static long cross(int[] px, int[] py, int o, int a, int b) {
        return (long) (px[a] - px[o]) * (py[b] - py[o]) - (long) (py[a] - py[o]) * (px[b] - px[o]);
    }

    /**
     * Rotating calipers: the minimum-area enclosing rectangle always has one side
     * flush with a hull edge, so testing every edge is exhaustive.
     *
     * @return {@code [cx, cy, halfW, halfH, ux, uy]} — centre, half extents, and
     *         the unit vector along the rectangle's width
     */
    private static float[] minAreaRect(int[] px, int[] py, int[] hull) {
        int n = hull.length;
        if (n < 2) {
            return null;
        }
        double bestArea = Double.MAX_VALUE;
        float[] best = null;

        for (int i = 0; i < n; i++) {
            int a = hull[i];
            int b = hull[(i + 1) % n];
            double ex = px[b] - px[a];
            double ey = py[b] - py[a];
            double len = Math.hypot(ex, ey);
            if (len < 1e-6) {
                continue;
            }
            double ux = ex / len, uy = ey / len;
            double vx = -uy, vy = ux;

            double minU = Double.MAX_VALUE, maxU = -Double.MAX_VALUE;
            double minV = Double.MAX_VALUE, maxV = -Double.MAX_VALUE;
            for (int j = 0; j < n; j++) {
                int p = hull[j];
                double u = px[p] * ux + py[p] * uy;
                double v = px[p] * vx + py[p] * vy;
                if (u < minU) minU = u;
                if (u > maxU) maxU = u;
                if (v < minV) minV = v;
                if (v > maxV) maxV = v;
            }
            double bw = maxU - minU;
            double bh = maxV - minV;
            double area = bw * bh;
            if (area < bestArea) {
                bestArea = area;
                double cu = (minU + maxU) / 2;
                double cv = (minV + maxV) / 2;
                // Back out of (u,v) into image space.
                double cx = cu * ux + cv * vx;
                double cy = cu * uy + cv * vy;
                best = new float[]{(float) cx, (float) cy, (float) (bw / 2), (float) (bh / 2),
                        (float) ux, (float) uy};
            }
        }
        return best;
    }

    /**
     * Dilates the rectangle by the DB unclip distance
     * {@code area * ratio / perimeter}, then emits ordered corners.
     */
    private Quad unclip(float[] rect, int w, int h) {
        float cx = rect[0], cy = rect[1];
        float halfW = rect[2], halfH = rect[3];
        float ux = rect[4], uy = rect[5];
        float vx = -uy, vy = ux;

        float bw = halfW * 2, bh = halfH * 2;
        if (Math.min(bw, bh) < minBoxSide) {
            return null;
        }
        float area = bw * bh;
        float perimeter = 2 * (bw + bh);
        float dist = perimeter > 1e-6f ? area * unclipRatio / perimeter : 0f;

        float eu = halfW + dist;
        float ev = halfH + dist;

        float[] pts = new float[8];
        // Corner order follows (-u,-v), (+u,-v), (+u,+v), (-u,+v).
        float[][] signs = {{-1, -1}, {1, -1}, {1, 1}, {-1, 1}};
        for (int i = 0; i < 4; i++) {
            float su = signs[i][0] * eu;
            float sv = signs[i][1] * ev;
            pts[i * 2] = cx + su * ux + sv * vx;
            pts[i * 2 + 1] = cy + su * uy + sv * vy;
        }
        return Quad.ordered(pts).clampedTo(w, h);
    }

    /** Minimal growable int array — avoids boxing every pixel index. */
    private static final class IntBag {
        private int[] data;
        private int size;

        IntBag(int capacity) {
            data = new int[Math.max(16, capacity)];
        }

        void add(int v) {
            if (size == data.length) {
                int[] bigger = new int[data.length * 2];
                System.arraycopy(data, 0, bigger, 0, data.length);
                data = bigger;
            }
            data[size++] = v;
        }

        void clear() {
            size = 0;
        }

        int size() {
            return size;
        }

        int[] data() {
            return data;
        }
    }
}
