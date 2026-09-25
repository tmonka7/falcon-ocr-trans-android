package com.falcon.ocrtrans.pdf;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.pdf.PdfRenderer;
import android.net.Uri;
import android.os.ParcelFileDescriptor;

import androidx.annotation.NonNull;

import java.io.Closeable;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;

/**
 * Rasterises the pages of a PDF so OCR can read them.
 *
 * <p>{@link PdfRenderer} needs a seekable file descriptor, which a
 * {@code content://} URI from the document picker does not provide, so the
 * source is copied into the cache first.
 */
public final class PdfPageSource implements Closeable {

    /** Pages are rendered at this many dots per inch before recognition. */
    private static final int RENDER_DPI = 200;
    private static final int POINTS_PER_INCH = 72;
    /** Cap on either dimension, to keep a large page from exhausting memory. */
    private static final int MAX_DIMENSION = 3000;

    private final java.io.File cached;
    private final ParcelFileDescriptor descriptor;
    private final PdfRenderer renderer;

    public PdfPageSource(@NonNull Context context, @NonNull Uri uri) throws IOException {
        this.cached = copyToCache(context, uri);
        this.descriptor = ParcelFileDescriptor.open(cached, ParcelFileDescriptor.MODE_READ_ONLY);
        try {
            this.renderer = new PdfRenderer(descriptor);
        } catch (IOException | SecurityException e) {
            descriptor.close();
            //noinspection ResultOfMethodCallIgnored
            cached.delete();
            throw new IOException("cannot open PDF; it may be encrypted or malformed", e);
        }
    }

    public int pageCount() {
        return renderer.getPageCount();
    }

    /**
     * Renders one page to a bitmap.
     *
     * <p>The page is drawn onto white first: PDF pages have no background of
     * their own, and text rendered onto transparency reaches the detector as
     * black-on-black.
     *
     * @param index zero-based page number
     */
    @NonNull
    public Bitmap renderPage(int index) {
        try (PdfRenderer.Page page = renderer.openPage(index)) {
            float scale = RENDER_DPI / (float) POINTS_PER_INCH;
            int width = Math.round(page.getWidth() * scale);
            int height = Math.round(page.getHeight() * scale);

            int longest = Math.max(width, height);
            if (longest > MAX_DIMENSION) {
                float shrink = MAX_DIMENSION / (float) longest;
                width = Math.max(1, Math.round(width * shrink));
                height = Math.max(1, Math.round(height * shrink));
            }

            Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            bitmap.eraseColor(Color.WHITE);
            page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
            return bitmap;
        }
    }

    @Override
    public void close() {
        renderer.close();
        try {
            descriptor.close();
        } catch (IOException ignored) {
            // Already closing; nothing actionable.
        }
        //noinspection ResultOfMethodCallIgnored
        cached.delete();
    }

    private static java.io.File copyToCache(Context context, Uri uri) throws IOException {
        java.io.File out = new java.io.File(context.getCacheDir(),
                "pdf_" + System.currentTimeMillis() + ".pdf");
        try (InputStream in = context.getContentResolver().openInputStream(uri);
             FileOutputStream fos = new FileOutputStream(out)) {
            if (in == null) {
                throw new IOException("cannot read the selected PDF");
            }
            byte[] buffer = new byte[1 << 16];
            int n;
            while ((n = in.read(buffer)) > 0) {
                fos.write(buffer, 0, n);
            }
        }
        return out;
    }
}
