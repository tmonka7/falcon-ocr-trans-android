package com.falcon.ocrtrans.ocr;

import android.graphics.RectF;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.core.Paragraph;
import com.falcon.ocrtrans.core.TextLine;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Puts detected lines into reading order and merges them into paragraphs.
 *
 * <p>Detection returns boxes in raster order of their seed pixel, which is not
 * reading order, and it has no concept of a paragraph at all. Both matter
 * downstream: the translator needs whole sentences rather than fragments, and
 * the renderer needs to know which boxes it may reflow text across.
 */
public final class LineGrouper {

    /** Two lines are on the same visual row if their centres are this close. */
    private static final float ROW_TOLERANCE = 0.6f;
    /** Largest vertical gap, in line heights, that still continues a paragraph. */
    private static final float MAX_LINE_GAP = 1.6f;
    /** Largest height ratio between neighbours in one paragraph. */
    private static final float MAX_HEIGHT_RATIO = 1.7f;
    /** Largest baseline angle difference, in degrees, within one paragraph. */
    private static final float MAX_ANGLE_DELTA = 8f;
    /** Minimum horizontal overlap, as a fraction of the narrower line. */
    private static final float MIN_OVERLAP = 0.25f;

    private LineGrouper() {
    }

    /** Sorts top-to-bottom, then left-to-right within a row. */
    @NonNull
    public static List<TextLine> sortReadingOrder(@NonNull List<TextLine> lines) {
        List<TextLine> sorted = new ArrayList<>(lines);
        Collections.sort(sorted, (a, b) -> {
            RectF ra = a.quad().bounds();
            RectF rb = b.quad().bounds();
            float tolerance = Math.min(ra.height(), rb.height()) * ROW_TOLERANCE;
            float ca = ra.centerY();
            float cb = rb.centerY();
            if (Math.abs(ca - cb) > tolerance) {
                return Float.compare(ca, cb);
            }
            return Float.compare(ra.left, rb.left);
        });
        return sorted;
    }

    /**
     * Groups reading-ordered lines into paragraphs.
     *
     * <p>A line continues the current paragraph when it sits close below the
     * previous one, shares a column with it, and is set at a similar size and
     * angle. Any of those failing starts a new paragraph — the common cases being
     * a heading above body text, or a second column beginning.
     */
    @NonNull
    public static List<Paragraph> group(@NonNull List<TextLine> orderedLines) {
        List<Paragraph> out = new ArrayList<>();
        if (orderedLines.isEmpty()) {
            return out;
        }

        Paragraph current = new Paragraph();
        current.addLine(orderedLines.get(0));

        for (int i = 1; i < orderedLines.size(); i++) {
            TextLine prev = orderedLines.get(i - 1);
            TextLine line = orderedLines.get(i);

            if (continuesParagraph(prev, line)) {
                current.addLine(line);
            } else {
                current.buildSourceText();
                out.add(current);
                current = new Paragraph();
                current.addLine(line);
            }
        }
        current.buildSourceText();
        out.add(current);
        return out;
    }

    private static boolean continuesParagraph(TextLine prev, TextLine next) {
        RectF a = prev.quad().bounds();
        RectF b = next.quad().bounds();

        float hA = prev.quad().height();
        float hB = next.quad().height();
        if (hA <= 0 || hB <= 0) {
            return false;
        }

        float ratio = Math.max(hA, hB) / Math.min(hA, hB);
        if (ratio > MAX_HEIGHT_RATIO) {
            return false;
        }

        float angleDelta = Math.abs(prev.quad().angleDegrees() - next.quad().angleDegrees());
        if (angleDelta > MAX_ANGLE_DELTA) {
            return false;
        }

        // Vertical gap measured from the bottom of one to the top of the next;
        // a negative value means they overlap, which is fine.
        float gap = b.top - a.bottom;
        if (gap > Math.max(hA, hB) * MAX_LINE_GAP) {
            return false;
        }
        // A line that starts above the previous one is a new column, not a wrap.
        if (b.centerY() < a.centerY()) {
            return false;
        }

        float overlap = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        float narrower = Math.min(a.width(), b.width());
        return narrower > 0 && overlap / narrower >= MIN_OVERLAP;
    }
}
