package com.falcon.ocrtrans.render;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;
import android.text.Layout;
import android.text.TextPaint;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.core.OcrResult;
import com.falcon.ocrtrans.core.Paragraph;
import com.falcon.ocrtrans.core.Quad;
import com.falcon.ocrtrans.core.TextLine;

import java.util.List;

/**
 * Paints translated text back onto the page in place of the original.
 *
 * <p>The sequence is erase, then re-typeset. Every detected line is covered with
 * the paper colour sampled from inside its own box, and each paragraph's
 * translation is laid out into the rectangle its source lines occupied, at the
 * paragraph's own angle, in the ink colour sampled from the original glyphs.
 *
 * <p><b>What this preserves and what it does not.</b> Position, block geometry,
 * rotation, relative size, and ink and paper colour all survive. Typeface,
 * weight and letterforms do not — the system font is substituted, because
 * identifying and re-synthesising the original face from a photograph is a
 * different and much larger problem. On flat backgrounds the result reads as
 * genuinely reset text; over a photograph or gradient, the erase step shows as a
 * flat patch, which is the known cost of not running an inpainting model.
 */
public final class LayoutRenderer {

    /** How far each erase box is grown, as a fraction of its own size. */
    private static final float ERASE_PADDING = 0.06f;
    /** Below this angle a paragraph is treated as upright, avoiding needless rotation. */
    private static final float ANGLE_EPSILON = 0.75f;

    /** Tunables for one render pass. */
    public static final class Options {
        /** Draw a faint outline around each replaced block. */
        public boolean debugBoxes;
        /** Re-typeset per line instead of per paragraph. */
        public boolean perLine;
        /** Keep the source text visible underneath at this alpha; 0 erases fully. */
        public int keepOriginalAlpha;

        public static Options defaults() {
            return new Options();
        }
    }

    private LayoutRenderer() {
    }

    /**
     * @param source the page as recognised; not modified
     * @param result recognition output whose paragraphs carry translations
     * @return a new bitmap with the translation in place of the original text
     */
    @NonNull
    public static Bitmap render(@NonNull Bitmap source,
                                @NonNull OcrResult result,
                                @NonNull Options options) {
        Bitmap out = source.copy(Bitmap.Config.ARGB_8888, true);
        if (result.isEmpty()) {
            return out;
        }
        Canvas canvas = new Canvas(out);

        erase(canvas, result.lines(), options);

        if (options.perLine) {
            for (TextLine line : result.lines()) {
                drawLine(canvas, line, options);
            }
        } else {
            for (Paragraph paragraph : result.paragraphs()) {
                drawParagraph(canvas, paragraph, options);
            }
        }
        return out;
    }

    // -------------------------------------------------------------------- erase

    /** Covers each source line with its own sampled paper colour. */
    private static void erase(Canvas canvas, List<TextLine> lines, Options options) {
        if (options.keepOriginalAlpha >= 255) {
            return;
        }
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setStyle(Paint.Style.FILL);
        // Alpha here is the inverse of how much original to keep showing through.
        int alpha = 255 - Math.max(0, Math.min(255, options.keepOriginalAlpha));

        for (TextLine line : lines) {
            paint.setColor(line.backgroundColor());
            paint.setAlpha(alpha);
            canvas.drawPath(expandedPath(line.quad()), paint);
        }
    }

    /**
     * Builds the erase path, grown outward from the box centre.
     *
     * <p>Detection boxes sit tight against the glyphs, so filling them exactly
     * leaves a visible fringe of antialiased pixels from the original text.
     */
    private static Path expandedPath(Quad quad) {
        float[] pts = quad.points();
        float cx = 0, cy = 0;
        for (int i = 0; i < 4; i++) {
            cx += pts[i * 2] / 4f;
            cy += pts[i * 2 + 1] / 4f;
        }
        Path path = new Path();
        for (int i = 0; i < 4; i++) {
            float x = cx + (pts[i * 2] - cx) * (1f + ERASE_PADDING);
            float y = cy + (pts[i * 2 + 1] - cy) * (1f + ERASE_PADDING);
            if (i == 0) {
                path.moveTo(x, y);
            } else {
                path.lineTo(x, y);
            }
        }
        path.close();
        return path;
    }

    // --------------------------------------------------------------- typesetting

    private static void drawParagraph(Canvas canvas, Paragraph paragraph, Options options) {
        if (paragraph.isEmpty()) {
            return;
        }
        String text = paragraph.translatedText();
        if (text == null || text.trim().isEmpty()) {
            return;
        }

        List<TextLine> lines = paragraph.lines();
        TextLine first = lines.get(0);
        RectF bounds = paragraph.bounds();
        float angle = medianAngle(lines);

        // A rotated paragraph is laid out upright, then the canvas is turned; the
        // alternative, rotating each glyph run by hand, loses line breaking.
        RectF target = new RectF(bounds);
        canvas.save();
        if (Math.abs(angle) > ANGLE_EPSILON) {
            canvas.rotate(angle, bounds.centerX(), bounds.centerY());
            // Rotating about the centre keeps the centre fixed, but the box's
            // extents in the rotated frame are the un-rotated ones.
            float w = paragraphWidth(lines);
            float h = bounds.height();
            target = new RectF(
                    bounds.centerX() - w / 2f, bounds.centerY() - h / 2f,
                    bounds.centerX() + w / 2f, bounds.centerY() + h / 2f);
        }

        TextPaint paint = basePaint(first.foregroundColor());
        float preferred = paragraph.medianLineHeight() * 0.82f;

        TextFitter.Fit fit = TextFitter.fit(
                text, paint,
                Math.round(target.width()), Math.round(target.height()),
                preferred, Layout.Alignment.ALIGN_NORMAL);

        canvas.save();
        canvas.translate(target.left, target.top);
        fit.layout.draw(canvas);
        canvas.restore();

        if (options.debugBoxes) {
            drawDebugBox(canvas, target, fit.overflowed);
        }
        canvas.restore();
    }

    private static void drawLine(Canvas canvas, TextLine line, Options options) {
        String text = line.displayText();
        if (text.trim().isEmpty()) {
            return;
        }
        Quad quad = line.quad();
        RectF bounds = quad.bounds();
        float angle = quad.angleDegrees();

        canvas.save();
        RectF target = bounds;
        if (Math.abs(angle) > ANGLE_EPSILON) {
            canvas.rotate(angle, bounds.centerX(), bounds.centerY());
            float w = quad.width();
            float h = quad.height();
            target = new RectF(
                    bounds.centerX() - w / 2f, bounds.centerY() - h / 2f,
                    bounds.centerX() + w / 2f, bounds.centerY() + h / 2f);
        }

        TextPaint paint = basePaint(line.foregroundColor());
        TextFitter.Fit fit = TextFitter.fit(
                text, paint,
                Math.round(target.width()), Math.round(target.height()),
                quad.height() * 0.82f, Layout.Alignment.ALIGN_NORMAL);

        canvas.save();
        canvas.translate(target.left, target.top);
        fit.layout.draw(canvas);
        canvas.restore();

        if (options.debugBoxes) {
            drawDebugBox(canvas, target, fit.overflowed);
        }
        canvas.restore();
    }

    private static TextPaint basePaint(int color) {
        TextPaint paint = new TextPaint(Paint.ANTI_ALIAS_FLAG | Paint.SUBPIXEL_TEXT_FLAG);
        paint.setColor(color);
        // The system typeface carries CJK coverage through font fallback, so
        // Hangul, Kana and Han all render without bundling a font.
        paint.setTypeface(android.graphics.Typeface.DEFAULT);
        return paint;
    }

    private static void drawDebugBox(Canvas canvas, RectF rect, boolean overflowed) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setStyle(Paint.Style.STROKE);
        p.setStrokeWidth(1.5f);
        p.setColor(overflowed ? Color.RED : Color.argb(140, 0, 160, 255));
        canvas.drawRect(rect, p);
    }

    /** Median rather than mean: one badly-angled detection should not tilt the block. */
    private static float medianAngle(List<TextLine> lines) {
        float[] angles = new float[lines.size()];
        for (int i = 0; i < lines.size(); i++) {
            angles[i] = lines.get(i).quad().angleDegrees();
        }
        java.util.Arrays.sort(angles);
        return angles[angles.length / 2];
    }

    /** Widest member line, measured along its own baseline. */
    private static float paragraphWidth(List<TextLine> lines) {
        float w = 0;
        for (TextLine l : lines) {
            w = Math.max(w, l.quad().width());
        }
        return w;
    }
}
