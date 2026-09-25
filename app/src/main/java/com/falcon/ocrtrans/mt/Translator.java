package com.falcon.ocrtrans.mt;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.core.Lang;

import java.io.Closeable;
import java.util.List;

/** Translates text between two of the supported languages, entirely offline. */
public interface Translator extends Closeable {

    @NonNull
    String translate(@NonNull String text, @NonNull Lang from, @NonNull Lang to) throws MtException;

    /**
     * Translates several strings.
     *
     * <p>Implementations are free to reuse a loaded session across the batch,
     * which is the difference between one model load and {@code n} of them when a
     * page has twenty paragraphs on it.
     */
    @NonNull
    List<String> translateAll(@NonNull List<String> texts, @NonNull Lang from, @NonNull Lang to)
            throws MtException;

    /** @return whether this translator can serve the given direction at all. */
    boolean supports(@NonNull Lang from, @NonNull Lang to);

    @Override
    void close();

    /** Any failure to load a model or run decoding. */
    class MtException extends Exception {
        public MtException(String message) {
            super(message);
        }

        public MtException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
