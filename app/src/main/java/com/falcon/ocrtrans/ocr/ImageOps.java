package com.falcon.ocrtrans.ocr;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.RectF;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.core.Quad;

/** Bitmap to tensor conversion, rotated-box cropping and colour sampling. */
public final class ImageOps {

    /** ImageNet statistics — what PP-OCR's detector was trained against. */
    private static final float[] DET_MEAN = {0.485f, 0.456f, 0.406f};
    private static final float[] DET_STD = {0.229f, 0.224f, 0.225f};

    private ImageOps() {
    }

    /**
     * Scales so the long edge is at most {@code limit} and both sides are
     * multiples of 32.
     *
     * <p>The detector is a fully convolutional network with five stride-2 stages,
     * so a side that is not a multiple of 32 makes the decoder's upsampled output
     * disagree with the input by a pixel or two and shifts every box.
     */
    @NonNull
    public static Bitmap resizeForDetection(@NonNull Bitmap src, int limit) {
        int w = src.getWidth();
        int h = src.getHeight();
        float ratio = 1f;
        int longSide = Math.max(w, h);
        if (longSide > limit) {
            ratio = (float) limit / longSide;
        }
        int rw = Math.max(32, roundTo32(w * ratio));
        int rh = Math.max(32, roundTo32(h * ratio));
        if (rw == w && rh == h) {
            return src;
        }
        return Bitmap.createScaledBitmap(src, rw, rh, true);
    }

    private static int roundTo32(float v) {
        return Math.max(1, Math.round(v / 32f)) * 32;
    }

    /**
     * Packs a bitmap into a normalised NCHW float tensor for the detector.
     * Layout is {@code [1][3][h][w]} flattened, channel order RGB.
     */
    @NonNull
    public static float[] detectionTensor(@NonNull Bitmap bmp) {
        int w = bmp.getWidth();
        int h = bmp.getHeight();
        int[] px = new int[w * h];
        bmp.getPixels(px, 0, w, 0, 0, w, h);

        float[] out = new float[3 * w * h];
        int plane = w * h;
        for (int i = 0; i < plane; i++) {
            int p = px[i];
            float r = ((p >> 16) & 0xFF) / 255f;
            float g = ((p >> 8) & 0xFF) / 255f;
            float b = (p & 0xFF) / 255f;
            out[i] = (r - DET_MEAN[0]) / DET_STD[0];
            out[plane + i] = (g - DET_MEAN[1]) / DET_STD[1];
            out[2 * plane + i] = (b - DET_MEAN[2]) / DET_STD[2];
        }
        return out;
    }

    /**
     * Packs a line crop for the recognition head, scaled to {@code targetH} and
     * right-padded with zeros to {@code padW}.
     *
     * <p>Recognition normalises to {@code [-1, 1]} rather than ImageNet
     * statistics; the two heads genuinely disagree on preprocessing and mixing
     * them up yields confident nonsense rather than an error.
     */
    @NonNull
    public static float[] recognitionTensor(@NonNull Bitmap crop, int targetH, int padW) {
        int srcW = crop.getWidth();
        int srcH = crop.getHeight();
        int scaledW = Math.max(1, Math.min(padW, Math.round(srcW * (targetH / (float) srcH))));

        Bitmap scaled = Bitmap.createScaledBitmap(crop, scaledW, targetH, true);
        int[] px = new int[scaledW * targetH];
        scaled.getPixels(px, 0, scaledW, 0, 0, scaledW, targetH);
        if (scaled != crop) {
            scaled.recycle();
        }

        float[] out = new float[3 * targetH * padW];
        int plane = targetH * padW;
        for (int y = 0; y < targetH; y++) {
            for (int x = 0; x < scaledW; x++) {
                int p = px[y * scaledW + x];
                int dst = y * padW + x;
                out[dst] = (((p >> 16) & 0xFF) / 255f - 0.5f) / 0.5f;
                out[plane + dst] = (((p >> 8) & 0xFF) / 255f - 0.5f) / 0.5f;
                out[2 * plane + dst] = ((p & 0xFF) / 255f - 0.5f) / 0.5f;
            }
        }
        return out;
    }

    /**
     * Cuts a rotated quad out of the page and straightens it into an upright
     * bitmap, which is the only form the recognition head accepts.
     *
     * <p>A four-point perspective map is used rather than a rotate-and-crop so
     * that mild keystoning from photographing a page at an angle is corrected at
     * the same time.
     */
    @NonNull
    public static Bitmap cropQuad(@NonNull Bitmap src, @NonNull Quad quad) {
        int outW = Math.max(1, Math.round(quad.width()));
        int outH = Math.max(1, Math.round(quad.height()));
        // Guard against a pathological detection eating all available memory.
        outW = Math.min(outW, 4096);
        outH = Math.min(outH, 4096);

        float[] srcPts = quad.points();
        float[] dstPts = {0, 0, outW, 0, outW, outH, 0, outH};

        Matrix m = new Matrix();
        if (!m.setPolyToPoly(srcPts, 0, dstPts, 0, 4)) {
            // Collinear corners; fall back to the axis-aligned bounds.
            RectF b = quad.bounds();
            int x = (int) Math.max(0, b.left);
            int y = (int) Math.max(0, b.top);
            int w = (int) Math.min(src.getWidth() - x, Math.max(1, b.width()));
            int h = (int) Math.min(src.getHeight() - y, Math.max(1, b.height()));
            return Bitmap.createBitmap(src, x, y, Math.max(1, w), Math.max(1, h));
        }

        Bitmap out = Bitmap.createBitmap(outW, outH, Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(out);
        c.drawColor(Color.WHITE);
        Paint p = new Paint(Paint.FILTER_BITMAP_FLAG | Paint.ANTI_ALIAS_FLAG);
        c.drawBitmap(src, m, p);
        return out;
    }

    /**
     * Estimates ink and paper colour for a text box.
     *
     * <p>Rather than clustering, this splits the crop's luminance at its midpoint
     * and averages each side. Glyph strokes are a minority of dark pixels against
     * a majority of light paper (or the inverse for reversed text), so the two
     * means land on the two colours that actually matter, cheaply enough to run
     * on every detected line.
     *
     * @return {@code [foregroundArgb, backgroundArgb]}
     */
    @NonNull
    public static int[] sampleColors(@NonNull Bitmap crop) {
        int w = crop.getWidth();
        int h = crop.getHeight();
        // Subsample: colour estimates do not improve past a few thousand pixels.
        int step = Math.max(1, (int) Math.sqrt((w * (long) h) / 4096.0));

        long minLum = 255, maxLum = 0;
        int n = 0;
        for (int y = 0; y < h; y += step) {
            for (int x = 0; x < w; x += step) {
                int lum = luminance(crop.getPixel(x, y));
                minLum = Math.min(minLum, lum);
                maxLum = Math.max(maxLum, lum);
                n++;
            }
        }
        if (n == 0 || maxLum <= minLum) {
            return new int[]{Color.BLACK, Color.WHITE};
        }
        long mid = (minLum + maxLum) / 2;

        long dr = 0, dg = 0, db = 0, dc = 0;
        long lr = 0, lg = 0, lb = 0, lc = 0;
        for (int y = 0; y < h; y += step) {
            for (int x = 0; x < w; x += step) {
                int p = crop.getPixel(x, y);
                int r = (p >> 16) & 0xFF, g = (p >> 8) & 0xFF, b = p & 0xFF;
                if (luminance(p) < mid) {
                    dr += r; dg += g; db += b; dc++;
                } else {
                    lr += r; lg += g; lb += b; lc++;
                }
            }
        }
        int dark = dc > 0 ? Color.rgb((int) (dr / dc), (int) (dg / dc), (int) (db / dc)) : Color.BLACK;
        int light = lc > 0 ? Color.rgb((int) (lr / lc), (int) (lg / lc), (int) (lb / lc)) : Color.WHITE;

        // Whichever class holds fewer pixels is the ink; ties favour dark-on-light.
        boolean darkIsInk = dc <= lc;
        return darkIsInk ? new int[]{dark, light} : new int[]{light, dark};
    }

    public static int luminance(int argb) {
        int r = (argb >> 16) & 0xFF;
        int g = (argb >> 8) & 0xFF;
        int b = argb & 0xFF;
        return (r * 299 + g * 587 + b * 114) / 1000;
    }

    /** Rotates a bitmap by a multiple of 90 degrees, e.g. to honour EXIF. */
    @NonNull
    public static Bitmap rotate(@NonNull Bitmap src, int degrees) {
        if (degrees % 360 == 0) {
            return src;
        }
        Matrix m = new Matrix();
        m.postRotate(degrees);
        return Bitmap.createBitmap(src, 0, 0, src.getWidth(), src.getHeight(), m, true);
    }
}
