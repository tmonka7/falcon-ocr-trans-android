package com.falcon.ocrtrans.render;

import android.graphics.Bitmap;
import android.graphics.BlurMaskFilter;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.CornerPathEffect;
import android.graphics.Matrix;
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

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Paints translated text back onto the page in place of the original.
 *
 * <p>The sequence is highlight, then typeset. Every block that receives a
 * translation is first covered with a faint, soft-edged highlight in the paper
 * colour sampled from inside its own box; the translation is then laid out into
 * the rectangle its source lines occupied, at the block's own angle, in the ink
 * colour sampled from the original glyphs.
 *
 * <p><b>Why a highlight and not an erase.</b> Filling each box with an opaque
 * paper colour gave the translation a solid background of its own, which read
 * as a sticker pasted onto the page and showed as a flat patch over any photo,
 * gradient or paper texture. The highlight is translucent, so the page stays
 * visible underneath and the original text survives as a faint ghost. Legibility
 * over that ghost comes from a thin halo in the paper colour drawn behind each
 * glyph, not from hiding the page.
 *
 * <p><b>What this preserves and what it does not.</b> Position, block geometry,
 * rotation, relative size, ink and paper colour, and now the page texture all
 * survive. Typeface, weight and letterforms do not — the system font is
 * substituted, because identifying and re-synthesising the original face from a
 * photograph is a different and much larger problem.
 */
public final class LayoutRenderer {

    /** How far each highlight is grown past its box, as a fraction of its own size. */
    private static final float HIGHLIGHT_PADDING = 0.06f;
    /** Below this angle a block is treated as upright, avoiding needless rotation. */
    private static final float ANGLE_EPSILON = 0.75f;
    /** Highlight corner radius and edge softness, as fractions of the line height. */
    private static final float CORNER_RADIUS = 0.18f;
    private static final float EDGE_SOFTNESS = 0.06f;
    /** Halo stroke width as a fraction of the fitted text size. */
    private static final float HALO_WIDTH = 0.16f;
    /** Target text size relative to the source line height, which includes leading. */
    private static final float SIZE_FROM_LINE_HEIGHT = 0.82f;

    /**
     * Default highlight opacity, 0–255. High enough that the original reads as a
     * ghost behind the halo'd translation, low enough that the page shows through.
     */
    public static final int DEFAULT_HIGHLIGHT_ALPHA = 150;

    /** Tunables for one render pass. */
    public static final class Options {
        /** Draw a faint outline around each replaced block. */
        public boolean debugBoxes;
        /** Re-typeset per line instead of per paragraph. */
        public boolean perLine;
        /** Opacity of the highlight over each text area; 0 draws no highlight. */
        public int highlightAlpha = DEFAULT_HIGHLIGHT_ALPHA;
        /** Outline glyphs in the paper colour so they read over the original. */
        public boolean halo = true;

        public static Options defaults() {
            return new Options();
        }
    }

    /**
     * One run of translated text and where it goes: the upright rectangle it is
     * laid out in, the angle that rectangle is turned by about its centre, and
     * the source quads its highlight must cover.
     */
    private static final class Block {
        final String text;
        final RectF target;
        final float angle;
        final float preferredSize;
        final float lineHeight;
        final int ink;
        final int paper;
        final List<Quad> sources;

        Block(String text, RectF target, float angle, float preferredSize, float lineHeight,
              int ink, int paper, List<Quad> sources) {
            this.text = text;
            this.target = target;
            this.angle = angle;
            this.preferredSize = preferredSize;
            this.lineHeight = lineHeight;
            this.ink = ink;
            this.paper = paper;
            this.sources = sources;
        }

        boolean rotated() {
            return Math.abs(angle) > ANGLE_EPSILON;
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

        List<Block> blocks = options.perLine
                ? lineBlocks(result.lines())
                : paragraphBlocks(result.paragraphs());

        // All highlights go down before any text, so a neighbouring block's
        // highlight can never fade glyphs that were already drawn.
        for (Block block : blocks) {
            highlight(canvas, block, options);
        }
        for (Block block : blocks) {
            typeset(canvas, block, options);
        }
        return out;
    }

    // ------------------------------------------------------------------- blocks

    private static List<Block> paragraphBlocks(List<Paragraph> paragraphs) {
        List<Block> blocks = new ArrayList<>();
        for (Paragraph paragraph : paragraphs) {
            if (paragraph.isEmpty()) {
                continue;
            }
            String text = paragraph.translatedText();
            if (text == null || text.trim().isEmpty()) {
                // Nothing will be drawn here, so leave the original untouched
                // rather than fading it for no replacement.
                continue;
            }
            List<TextLine> lines = paragraph.lines();
            TextLine first = lines.get(0);
            float angle = medianAngle(lines);
            RectF bounds = paragraph.bounds();
            // A rotated paragraph is laid out upright, then the canvas is turned;
            // the alternative, rotating each glyph run by hand, loses line
            // breaking. Rotating about the centre keeps the centre fixed, but
            // the box's extents in the rotated frame are the un-rotated ones.
            RectF target = Math.abs(angle) > ANGLE_EPSILON
                    ? centred(bounds, paragraphWidth(lines), bounds.height())
                    : new RectF(bounds);

            List<Quad> quads = new ArrayList<>(lines.size());
            for (TextLine l : lines) {
                quads.add(l.quad());
            }
            float lineHeight = paragraph.medianLineHeight();
            blocks.add(new Block(text, target, angle, lineHeight * SIZE_FROM_LINE_HEIGHT,
                    lineHeight, first.foregroundColor(), first.backgroundColor(), quads));
        }
        return blocks;
    }

    private static List<Block> lineBlocks(List<TextLine> lines) {
        List<Block> blocks = new ArrayList<>();
        for (TextLine line : lines) {
            String text = line.displayText();
            if (text.trim().isEmpty()) {
                continue;
            }
            Quad quad = line.quad();
            RectF bounds = quad.bounds();
            float angle = quad.angleDegrees();
            RectF target = Math.abs(angle) > ANGLE_EPSILON
                    ? centred(bounds, quad.width(), quad.height())
                    : bounds;
            blocks.add(new Block(text, target, angle, quad.height() * SIZE_FROM_LINE_HEIGHT,
                    quad.height(), line.foregroundColor(), line.backgroundColor(),
                    Collections.singletonList(quad)));
        }
        return blocks;
    }

    // ---------------------------------------------------------------- highlight

    /**
     * Lays a faint, soft-edged wash of the block's paper colour over the area its
     * translation will occupy.
     *
     * <p>The area is the union of the source line quads and the layout rectangle,
     * so it covers both the original glyphs and wherever the new text lands, as
     * one shape. Unioning first matters: overlapping translucent fills would
     * double up and leave darker bands between lines.
     */
    private static void highlight(Canvas canvas, Block block, Options options) {
        int alpha = Math.max(0, Math.min(255, options.highlightAlpha));
        if (alpha == 0) {
            return;
        }
        Path area = new Path();
        for (Quad quad : block.sources) {
            area.op(expandedPath(quad), Path.Op.UNION);
        }
        area.op(targetPath(block), Path.Op.UNION);

        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(block.paper);
        paint.setAlpha(alpha);
        paint.setPathEffect(new CornerPathEffect(block.lineHeight * CORNER_RADIUS));
        // A feathered edge is what keeps the highlight from reading as a patch.
        // The canvas is bitmap-backed, so the mask filter is honoured.
        float soft = block.lineHeight * EDGE_SOFTNESS;
        if (soft >= 0.5f) {
            paint.setMaskFilter(new BlurMaskFilter(soft, BlurMaskFilter.Blur.NORMAL));
        }
        canvas.drawPath(area, paint);
    }

    /** The layout rectangle in page coordinates, grown slightly and turned by the block's angle. */
    private static Path targetPath(Block block) {
        RectF r = new RectF(block.target);
        float dx = r.width() * HIGHLIGHT_PADDING / 2f;
        float dy = r.height() * HIGHLIGHT_PADDING / 2f;
        r.inset(-dx, -dy);
        Path path = new Path();
        path.addRect(r, Path.Direction.CW);
        if (block.rotated()) {
            Matrix m = new Matrix();
            m.setRotate(block.angle, block.target.centerX(), block.target.centerY());
            path.transform(m);
        }
        return path;
    }

    /**
     * Builds a source quad's outline, grown outward from its centre.
     *
     * <p>Detection boxes sit tight against the glyphs, so an exact fit leaves a
     * fringe of antialiased pixels from the original text outside the highlight.
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
            float x = cx + (pts[i * 2] - cx) * (1f + HIGHLIGHT_PADDING);
            float y = cy + (pts[i * 2 + 1] - cy) * (1f + HIGHLIGHT_PADDING);
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

    private static void typeset(Canvas canvas, Block block, Options options) {
        RectF target = block.target;
        canvas.save();
        if (block.rotated()) {
            canvas.rotate(block.angle, target.centerX(), target.centerY());
        }

        TextPaint paint = basePaint(block.ink);
        TextFitter.Fit fit = TextFitter.fit(
                block.text, paint,
                Math.round(target.width()), Math.round(target.height()),
                block.preferredSize, Layout.Alignment.ALIGN_NORMAL);

        canvas.save();
        canvas.translate(target.left, target.top);
        if (options.halo) {
            // The layout draws with the paint it was built with, so restyling that
            // paint between draws strokes the same glyph runs. Stroke width does
            // not affect advances, so the fitted line breaks still hold.
            paint.setStyle(Paint.Style.STROKE);
            paint.setStrokeJoin(Paint.Join.ROUND);
            paint.setStrokeWidth(fit.textSize * HALO_WIDTH);
            paint.setColor(block.paper);
            fit.layout.draw(canvas);
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(block.ink);
        }
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

    // ------------------------------------------------------------------ geometry

    private static RectF centred(RectF around, float w, float h) {
        return new RectF(
                around.centerX() - w / 2f, around.centerY() - h / 2f,
                around.centerX() + w / 2f, around.centerY() + h / 2f);
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
