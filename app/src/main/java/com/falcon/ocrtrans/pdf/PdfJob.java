package com.falcon.ocrtrans.pdf;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Rect;
import android.graphics.pdf.PdfDocument;
import android.net.Uri;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.annotation.WorkerThread;

import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.data.Prefs;
import com.falcon.ocrtrans.engine.TranslationPipeline;
import com.falcon.ocrtrans.mt.Translator;
import com.falcon.ocrtrans.ocr.OcrEngine;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Translates a whole PDF, one page at a time, and writes the chosen output.
 *
 * <p>Pages are processed and released individually rather than rasterised up
 * front: a 200 dpi A4 page is roughly 15.5 MB as ARGB_8888, so holding a
 * twelve-page document in memory at once would exceed the heap on most devices.
 * The PDF output path keeps rendered pages only long enough to write each one
 * into the document.
 */
public final class PdfJob {

    private static final String TAG = "PdfJob";
    private static final int POINTS_PER_INCH = 72;
    private static final int RENDER_DPI = 200;

    /** Progress and cancellation. */
    public interface Listener {
        /** @param page one-based */
        void onPageStarted(int page, int total);

        void onPageFinished(int page, int total, @NonNull String pageText);

        /** Polled between pages; return true to stop early. */
        boolean isCancelled();
    }

    /** What a finished job produced. */
    public static final class Output {
        @NonNull
        public final File file;
        public final int pagesProcessed;
        @NonNull
        public final String combinedText;

        Output(@NonNull File file, int pagesProcessed, @NonNull String combinedText) {
            this.file = file;
            this.pagesProcessed = pagesProcessed;
            this.combinedText = combinedText;
        }
    }

    private final Context context;
    private final TranslationPipeline pipeline;

    public PdfJob(@NonNull Context context, @NonNull TranslationPipeline pipeline) {
        this.context = context.getApplicationContext();
        this.pipeline = pipeline;
    }

    /**
     * @param firstPage one-based, inclusive
     * @param lastPage  one-based, inclusive; clamped to the document length
     */
    @WorkerThread
    @NonNull
    public Output run(@NonNull Uri source,
                      @NonNull Lang from,
                      @NonNull Lang to,
                      @NonNull Prefs.PdfOutput format,
                      int firstPage,
                      int lastPage,
                      @Nullable Listener listener)
            throws IOException, OcrEngine.OcrException, Translator.MtException {

        TranslationPipeline.Options options = new TranslationPipeline.Options();
        // Only the PDF output repaints pages; DOCX and TXT need text alone, and
        // rendering for them would be several seconds per page of wasted work.
        options.render = format == Prefs.PdfOutput.PDF;

        List<String> pageTexts = new ArrayList<>();
        File target = outputFile(format);

        try (PdfPageSource pages = new PdfPageSource(context, source)) {
            int total = pages.pageCount();
            int start = Math.max(1, firstPage);
            int end = lastPage <= 0 ? total : Math.min(total, lastPage);
            int count = Math.max(0, end - start + 1);

            PdfDocument document = options.render ? new PdfDocument() : null;
            try {
                int processed = 0;
                for (int page = start; page <= end; page++) {
                    if (listener != null && listener.isCancelled()) {
                        break;
                    }
                    if (listener != null) {
                        listener.onPageStarted(page - start + 1, count);
                    }

                    Bitmap source0 = pages.renderPage(page - 1);
                    Bitmap rendered = null;
                    String text;
                    try {
                        TranslationPipeline.Result result =
                                pipeline.process(source0, from, to, options);
                        rendered = result.rendered;
                        text = result.ocr.translatedText();
                        if (text.trim().isEmpty()) {
                            text = result.ocr.plainText();
                        }
                        pageTexts.add(text);

                        if (document != null) {
                            writePage(document, rendered != null ? rendered : source0, processed);
                        }
                    } finally {
                        if (rendered != null && rendered != source0 && !rendered.isRecycled()) {
                            rendered.recycle();
                        }
                        if (!source0.isRecycled()) {
                            source0.recycle();
                        }
                    }

                    processed++;
                    if (listener != null) {
                        listener.onPageFinished(page - start + 1, count, text);
                    }
                }

                switch (format) {
                    case PDF:
                        writePdf(document, target);
                        break;
                    case DOCX:
                        DocxWriter.write(target, pageTexts);
                        break;
                    case TXT:
                    default:
                        writeTxt(target, pageTexts);
                        break;
                }

                Log.d(TAG, "processed " + processed + " page(s) into " + target.getName());
                return new Output(target, processed, join(pageTexts));
            } finally {
                if (document != null) {
                    document.close();
                }
            }
        }
    }

    private static void writePage(PdfDocument document, Bitmap bitmap, int index) {
        // Convert the raster back to points so the page keeps its physical size
        // rather than becoming a giant page of 1-pixel-per-point.
        float scale = POINTS_PER_INCH / (float) RENDER_DPI;
        int widthPt = Math.max(1, Math.round(bitmap.getWidth() * scale));
        int heightPt = Math.max(1, Math.round(bitmap.getHeight() * scale));

        PdfDocument.PageInfo info =
                new PdfDocument.PageInfo.Builder(widthPt, heightPt, index + 1).create();
        PdfDocument.Page page = document.startPage(info);
        Canvas canvas = page.getCanvas();
        canvas.drawBitmap(bitmap,
                new Rect(0, 0, bitmap.getWidth(), bitmap.getHeight()),
                new Rect(0, 0, widthPt, heightPt),
                null);
        document.finishPage(page);
    }

    private static void writePdf(@Nullable PdfDocument document, File target) throws IOException {
        if (document == null) {
            throw new IOException("no rendered pages to write");
        }
        try (FileOutputStream out = new FileOutputStream(target)) {
            document.writeTo(out);
        }
    }

    private static void writeTxt(File target, List<String> pages) throws IOException {
        try (FileOutputStream out = new FileOutputStream(target)) {
            out.write(join(pages).getBytes(StandardCharsets.UTF_8));
        }
    }

    private static String join(List<String> pages) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < pages.size(); i++) {
            if (i > 0) {
                sb.append("\n\n");
            }
            sb.append(pages.get(i));
        }
        return sb.toString();
    }

    private File outputFile(Prefs.PdfOutput format) {
        File dir = new File(context.getFilesDir(), "exports");
        //noinspection ResultOfMethodCallIgnored
        dir.mkdirs();
        String extension = format.name().toLowerCase();
        return new File(dir, "translated_" + System.currentTimeMillis() + "." + extension);
    }
}
