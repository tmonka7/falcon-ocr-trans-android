package com.falcon.ocrtrans.util;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;

import androidx.annotation.NonNull;
import androidx.annotation.WorkerThread;
import androidx.exifinterface.media.ExifInterface;

import com.falcon.ocrtrans.ocr.ImageOps;

import java.io.IOException;
import java.io.InputStream;

/** Decodes user-chosen images at a sane size and in the right orientation. */
public final class ImageLoader {

    /**
     * Longest edge of a decoded page.
     *
     * <p>Detection runs at 960 px regardless, but the full-size bitmap is what
     * the renderer paints translated text onto, so it needs to stay large enough
     * to look sharp — while staying small enough that a 108-megapixel phone
     * photo does not blow the heap at four bytes per pixel.
     */
    private static final int MAX_EDGE = 2400;

    private ImageLoader() {
    }

    @WorkerThread
    @NonNull
    public static Bitmap load(@NonNull Context context, @NonNull Uri uri) throws IOException {
        // Pass one reads the header only, to choose a power-of-two sample size.
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        try (InputStream in = open(context, uri)) {
            BitmapFactory.decodeStream(in, null, bounds);
        }
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
            throw new IOException("not a decodable image: " + uri);
        }

        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inSampleSize = sampleSize(bounds.outWidth, bounds.outHeight);
        options.inPreferredConfig = Bitmap.Config.ARGB_8888;

        Bitmap decoded;
        try (InputStream in = open(context, uri)) {
            decoded = BitmapFactory.decodeStream(in, null, options);
        }
        if (decoded == null) {
            throw new IOException("could not decode " + uri);
        }

        // A phone photo is nearly always stored in sensor orientation with the
        // real rotation in EXIF. Skipping this reads every portrait photo sideways.
        int rotation = exifRotation(context, uri);
        if (rotation != 0) {
            Bitmap rotated = ImageOps.rotate(decoded, rotation);
            if (rotated != decoded) {
                decoded.recycle();
            }
            decoded = rotated;
        }
        return decoded;
    }

    private static int sampleSize(int width, int height) {
        int sample = 1;
        while (Math.max(width, height) / (sample * 2) >= MAX_EDGE) {
            sample *= 2;
        }
        return sample;
    }

    private static int exifRotation(Context context, Uri uri) {
        try (InputStream in = open(context, uri)) {
            int orientation = new ExifInterface(in).getAttributeInt(
                    ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
            switch (orientation) {
                case ExifInterface.ORIENTATION_ROTATE_90:
                    return 90;
                case ExifInterface.ORIENTATION_ROTATE_180:
                    return 180;
                case ExifInterface.ORIENTATION_ROTATE_270:
                    return 270;
                default:
                    return 0;
            }
        } catch (IOException e) {
            // No EXIF, or an unreadable stream; the pixels are still usable.
            return 0;
        }
    }

    private static InputStream open(Context context, Uri uri) throws IOException {
        InputStream in = context.getContentResolver().openInputStream(uri);
        if (in == null) {
            throw new IOException("cannot open " + uri);
        }
        return in;
    }

    /** Writes a bitmap into app storage and returns its absolute path. */
    @WorkerThread
    @NonNull
    public static String saveToAppStorage(@NonNull Context context,
                                          @NonNull Bitmap bitmap,
                                          @NonNull String prefix) throws IOException {
        java.io.File dir = new java.io.File(context.getFilesDir(), "pages");
        //noinspection ResultOfMethodCallIgnored
        dir.mkdirs();
        java.io.File file = new java.io.File(dir, prefix + "_" + System.currentTimeMillis() + ".jpg");
        try (java.io.FileOutputStream out = new java.io.FileOutputStream(file)) {
            bitmap.compress(Bitmap.CompressFormat.JPEG, 90, out);
        }
        return file.getAbsolutePath();
    }
}
