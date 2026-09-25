package com.falcon.ocrtrans.core;

import android.graphics.Matrix;
import android.graphics.PointF;
import android.graphics.RectF;

import androidx.annotation.NonNull;

import java.util.Locale;

/**
 * A rotated quadrilateral in image pixel coordinates, corners ordered
 * clockwise from the top-left: {@code [tl, tr, br, bl]}.
 *
 * <p>Detection emits rotated boxes rather than upright rectangles because signs,
 * book spines and photographed pages are rarely axis-aligned, and the renderer
 * needs the true baseline angle to lay translated text back down over the
 * original.
 */
public final class Quad {

    /** x0,y0,x1,y1,x2,y2,x3,y3 — clockwise from top-left. */
    private final float[] pts;

    public Quad(@NonNull float[] pts) {
        if (pts.length != 8) {
            throw new IllegalArgumentException("a quad needs 8 coordinates, got " + pts.length);
        }
        this.pts = pts.clone();
    }

    public static Quad ofRect(@NonNull RectF r) {
        return new Quad(new float[]{r.left, r.top, r.right, r.top, r.right, r.bottom, r.left, r.bottom});
    }

    /** @return a defensive copy of the raw coordinate array. */
    public float[] points() {
        return pts.clone();
    }

    public float x(int corner) {
        return pts[corner * 2];
    }

    public float y(int corner) {
        return pts[corner * 2 + 1];
    }

    public PointF corner(int i) {
        return new PointF(pts[i * 2], pts[i * 2 + 1]);
    }

    /** Axis-aligned bounds enclosing all four corners. */
    public RectF bounds() {
        float minX = pts[0], maxX = pts[0], minY = pts[1], maxY = pts[1];
        for (int i = 1; i < 4; i++) {
            minX = Math.min(minX, pts[i * 2]);
            maxX = Math.max(maxX, pts[i * 2]);
            minY = Math.min(minY, pts[i * 2 + 1]);
            maxY = Math.max(maxY, pts[i * 2 + 1]);
        }
        return new RectF(minX, minY, maxX, maxY);
    }

    /** Mean of the top and bottom edge lengths — the reading-direction extent. */
    public float width() {
        return (dist(0, 1) + dist(3, 2)) * 0.5f;
    }

    /** Mean of the left and right edge lengths — the cap-to-descender extent. */
    public float height() {
        return (dist(0, 3) + dist(1, 2)) * 0.5f;
    }

    public PointF center() {
        float cx = 0, cy = 0;
        for (int i = 0; i < 4; i++) {
            cx += pts[i * 2];
            cy += pts[i * 2 + 1];
        }
        return new PointF(cx / 4f, cy / 4f);
    }

    /**
     * Baseline angle in degrees, measured along the top edge and positive
     * clockwise to match {@link android.graphics.Canvas#rotate(float)}.
     */
    public float angleDegrees() {
        float dx = (pts[2] - pts[0] + pts[4] - pts[6]) * 0.5f;
        float dy = (pts[3] - pts[1] + pts[5] - pts[7]) * 0.5f;
        return (float) Math.toDegrees(Math.atan2(dy, dx));
    }

    private float dist(int a, int b) {
        float dx = pts[a * 2] - pts[b * 2];
        float dy = pts[a * 2 + 1] - pts[b * 2 + 1];
        return (float) Math.hypot(dx, dy);
    }

    /** Scales every corner about the origin. */
    public Quad scaled(float sx, float sy) {
        float[] out = new float[8];
        for (int i = 0; i < 4; i++) {
            out[i * 2] = pts[i * 2] * sx;
            out[i * 2 + 1] = pts[i * 2 + 1] * sy;
        }
        return new Quad(out);
    }

    public Quad transformed(@NonNull Matrix m) {
        float[] out = pts.clone();
        m.mapPoints(out);
        return new Quad(out);
    }

    /** Clamps every corner into {@code [0,w] x [0,h]}. */
    public Quad clampedTo(int w, int h) {
        float[] out = new float[8];
        for (int i = 0; i < 4; i++) {
            out[i * 2] = Math.max(0, Math.min(w, pts[i * 2]));
            out[i * 2 + 1] = Math.max(0, Math.min(h, pts[i * 2 + 1]));
        }
        return new Quad(out);
    }

    /**
     * Reorders an arbitrary set of four corners into the clockwise-from-top-left
     * convention. Sums and differences of the coordinates identify the extremes:
     * the top-left minimises {@code x+y}, and the top-right maximises {@code x-y}.
     */
    public static Quad ordered(@NonNull float[] raw) {
        if (raw.length != 8) {
            throw new IllegalArgumentException("expected 8 coordinates");
        }
        int tl = 0, br = 0, tr = 0, bl = 0;
        float minSum = Float.MAX_VALUE, maxSum = -Float.MAX_VALUE;
        float minDiff = Float.MAX_VALUE, maxDiff = -Float.MAX_VALUE;
        for (int i = 0; i < 4; i++) {
            float sum = raw[i * 2] + raw[i * 2 + 1];
            float diff = raw[i * 2] - raw[i * 2 + 1];
            if (sum < minSum) {
                minSum = sum;
                tl = i;
            }
            if (sum > maxSum) {
                maxSum = sum;
                br = i;
            }
            if (diff > maxDiff) {
                maxDiff = diff;
                tr = i;
            }
            if (diff < minDiff) {
                minDiff = diff;
                bl = i;
            }
        }
        // A degenerate box can map two roles onto one corner; fall back to the
        // raw order rather than emitting a quad with duplicated vertices.
        if (tl == br || tr == bl || tl == tr || bl == br) {
            return new Quad(raw);
        }
        return new Quad(new float[]{
                raw[tl * 2], raw[tl * 2 + 1],
                raw[tr * 2], raw[tr * 2 + 1],
                raw[br * 2], raw[br * 2 + 1],
                raw[bl * 2], raw[bl * 2 + 1]});
    }

    @NonNull
    @Override
    public String toString() {
        return String.format(Locale.US, "Quad[(%.0f,%.0f)(%.0f,%.0f)(%.0f,%.0f)(%.0f,%.0f)]",
                pts[0], pts[1], pts[2], pts[3], pts[4], pts[5], pts[6], pts[7]);
    }
}
