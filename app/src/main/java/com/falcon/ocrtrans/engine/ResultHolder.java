package com.falcon.ocrtrans.engine;

import android.graphics.Bitmap;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.core.Lang;

/**
 * Hands a finished page from the screen that produced it to the screen that
 * displays it.
 *
 * <p>An {@link android.content.Intent} cannot carry this. The Binder
 * transaction buffer is about 1 MB for the whole process, and a single
 * full-resolution page bitmap is several times that — putting one in an extra
 * raises {@code TransactionTooLargeException} at the far end, often only on the
 * user's larger-sensor device. A static handoff is the ordinary way around it.
 *
 * <p>The reference is cleared by whoever consumes it so a multi-megabyte bitmap
 * does not outlive the screen that needed it.
 */
public final class ResultHolder {

    @Nullable
    private static Payload pending;

    /** One page, ready to display. */
    public static final class Payload {
        @NonNull
        public final Bitmap original;
        @Nullable
        public final Bitmap rendered;
        @NonNull
        public final TranslationPipeline.Result result;
        @NonNull
        public final Lang source;
        @NonNull
        public final Lang target;

        public Payload(@NonNull Bitmap original,
                       @Nullable Bitmap rendered,
                       @NonNull TranslationPipeline.Result result,
                       @NonNull Lang source,
                       @NonNull Lang target) {
            this.original = original;
            this.rendered = rendered;
            this.result = result;
            this.source = source;
            this.target = target;
        }
    }

    private ResultHolder() {
    }

    public static synchronized void put(@Nullable Payload payload) {
        pending = payload;
    }

    /** Takes the pending payload, clearing it. Returns {@code null} if none. */
    @Nullable
    public static synchronized Payload take() {
        Payload p = pending;
        pending = null;
        return p;
    }

    /** Reads without clearing, so a recreated activity can render again. */
    @Nullable
    public static synchronized Payload peek() {
        return pending;
    }

    public static synchronized void clear() {
        pending = null;
    }
}
