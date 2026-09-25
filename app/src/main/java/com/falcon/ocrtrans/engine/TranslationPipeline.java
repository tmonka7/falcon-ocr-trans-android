package com.falcon.ocrtrans.engine;

import android.graphics.Bitmap;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.annotation.WorkerThread;

import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.core.OcrResult;
import com.falcon.ocrtrans.core.Paragraph;
import com.falcon.ocrtrans.core.TextLine;
import com.falcon.ocrtrans.mt.Translator;
import com.falcon.ocrtrans.ocr.OcrEngine;
import com.falcon.ocrtrans.render.LayoutRenderer;

import java.util.ArrayList;
import java.util.List;

/**
 * Runs the whole job: recognise, translate, repaint.
 *
 * <p>Every method here blocks and must be called on a worker thread.
 */
public final class TranslationPipeline {

    private static final String TAG = "TranslationPipeline";

    /** Everything one page produced. */
    public static final class Result {
        @NonNull
        public final OcrResult ocr;
        /** The page with translated text painted in, or {@code null} if rendering was off. */
        @Nullable
        public final Bitmap rendered;
        /** The source language actually used, after any auto-detection. */
        @NonNull
        public final Lang detectedSource;
        public final long elapsedMillis;

        Result(@NonNull OcrResult ocr, @Nullable Bitmap rendered,
               @NonNull Lang detectedSource, long elapsedMillis) {
            this.ocr = ocr;
            this.rendered = rendered;
            this.detectedSource = detectedSource;
            this.elapsedMillis = elapsedMillis;
        }
    }

    /** Per-run switches. */
    public static final class Options {
        /** Translate the recognised text; false recognises only. */
        public boolean translate = true;
        /** Produce a repainted bitmap as well as text. */
        public boolean render = true;
        /** Re-check the source language against what was actually read. */
        public boolean autoDetectSource = true;
        @NonNull
        public LayoutRenderer.Options renderOptions = LayoutRenderer.Options.defaults();
    }

    private final OcrEngine ocrEngine;
    private final Translator translator;

    public TranslationPipeline(@NonNull OcrEngine ocrEngine, @NonNull Translator translator) {
        this.ocrEngine = ocrEngine;
        this.translator = translator;
    }

    @WorkerThread
    @NonNull
    public Result process(@NonNull Bitmap bitmap,
                          @NonNull Lang source,
                          @NonNull Lang target,
                          @NonNull Options options)
            throws OcrEngine.OcrException, Translator.MtException {

        long started = System.currentTimeMillis();

        OcrResult ocr = ocrEngine.recognize(bitmap, source);
        Lang effectiveSource = source;

        if (!ocr.isEmpty() && options.autoDetectSource) {
            Lang guessed = ScriptDetector.detect(ocr.plainText(), source);
            // Re-running recognition is expensive, so only do it when the guess
            // disagrees — the first pass read the page with the wrong head and
            // its output is not trustworthy enough to translate.
            if (guessed != source) {
                Log.d(TAG, "source looks like " + guessed.code()
                        + " rather than " + source.code() + "; re-recognising");
                OcrResult second = ocrEngine.recognize(bitmap, guessed);
                if (!second.isEmpty()) {
                    ocr = second;
                    effectiveSource = guessed;
                }
            }
        }

        if (options.translate && !ocr.isEmpty() && effectiveSource != target) {
            translateInPlace(ocr, effectiveSource, target);
        }

        Bitmap rendered = null;
        if (options.render && !ocr.isEmpty()) {
            rendered = LayoutRenderer.render(bitmap, ocr, options.renderOptions);
        }

        return new Result(ocr, rendered, effectiveSource, System.currentTimeMillis() - started);
    }

    /**
     * Translates each paragraph, then spreads the result back over its lines.
     *
     * <p>The whole page goes to the translator in one call so the session is
     * loaded once rather than once per paragraph.
     */
    @WorkerThread
    private void translateInPlace(@NonNull OcrResult ocr, @NonNull Lang from, @NonNull Lang to)
            throws Translator.MtException {

        List<Paragraph> paragraphs = ocr.paragraphs();
        List<String> sources = new ArrayList<>(paragraphs.size());
        for (Paragraph p : paragraphs) {
            sources.add(p.sourceText());
        }

        List<String> translated = translator.translateAll(sources, from, to);

        for (int i = 0; i < paragraphs.size() && i < translated.size(); i++) {
            Paragraph p = paragraphs.get(i);
            String text = translated.get(i);
            p.setTranslatedText(text);
            distributeToLines(p, text);
        }
    }

    /**
     * Assigns a share of the paragraph's translation to each of its lines.
     *
     * <p>Per-line text only matters for the line-by-line render mode and for the
     * editable text view; the default paragraph renderer re-wraps the whole
     * string itself. Splitting proportionally by source line length keeps a
     * single-line paragraph exact and a multi-line one approximately aligned,
     * which is as good as this can get without word alignment from the model.
     */
    private static void distributeToLines(@NonNull Paragraph paragraph, @NonNull String translated) {
        List<TextLine> lines = paragraph.lines();
        if (lines.isEmpty()) {
            return;
        }
        if (lines.size() == 1) {
            lines.get(0).setTranslation(translated);
            return;
        }

        int totalSource = 0;
        for (TextLine l : lines) {
            totalSource += Math.max(1, l.text().length());
        }

        int cursor = 0;
        for (int i = 0; i < lines.size(); i++) {
            TextLine line = lines.get(i);
            int take;
            if (i == lines.size() - 1) {
                take = translated.length() - cursor;
            } else {
                float share = Math.max(1, line.text().length()) / (float) totalSource;
                take = Math.round(translated.length() * share);
            }
            take = Math.max(0, Math.min(take, translated.length() - cursor));

            int end = cursor + take;
            // Prefer to break on whitespace so words are not severed mid-token.
            if (end < translated.length() && end > cursor) {
                int space = translated.lastIndexOf(' ', end);
                if (space > cursor) {
                    end = space;
                }
            }
            line.setTranslation(translated.substring(cursor, end).trim());
            cursor = Math.min(translated.length(), end + 1);
        }
    }
}
