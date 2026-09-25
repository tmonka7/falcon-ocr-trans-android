package com.falcon.ocrtrans.ocr;

import android.graphics.Bitmap;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.core.OcrResult;

import java.io.Closeable;

/** Finds and reads text in an image. */
public interface OcrEngine extends Closeable {

    /**
     * @param lang the script to recognise, which selects the recognition head;
     *             detection itself is language independent
     */
    @NonNull
    OcrResult recognize(@NonNull Bitmap bitmap, @NonNull Lang lang) throws OcrException;

    /** Releases native sessions. Safe to call more than once. */
    @Override
    void close();

    /** Any failure to load a model or run inference. */
    class OcrException extends Exception {
        public OcrException(String message) {
            super(message);
        }

        public OcrException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
