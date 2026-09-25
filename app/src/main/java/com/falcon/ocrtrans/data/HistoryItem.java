package com.falcon.ocrtrans.data;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.core.Lang;

/** One saved translation, as listed on the History screen. */
public final class HistoryItem {

    /** Which entry point produced the record; drives the row's leading icon. */
    public enum Kind {
        CAMERA, IMAGE, PDF, MANUAL;

        @NonNull
        public static Kind fromName(@Nullable String name) {
            if (name != null) {
                for (Kind k : values()) {
                    if (k.name().equalsIgnoreCase(name)) {
                        return k;
                    }
                }
            }
            return IMAGE;
        }
    }

    public final long id;
    public final Kind kind;
    public final Lang source;
    public final Lang target;
    public final String sourceText;
    public final String translatedText;
    /** Absolute path of the rendered image, or {@code null} for text-only rows. */
    @Nullable
    public final String imagePath;
    public final long createdAt;

    public HistoryItem(long id,
                       @NonNull Kind kind,
                       @NonNull Lang source,
                       @NonNull Lang target,
                       @NonNull String sourceText,
                       @NonNull String translatedText,
                       @Nullable String imagePath,
                       long createdAt) {
        this.id = id;
        this.kind = kind;
        this.source = source;
        this.target = target;
        this.sourceText = sourceText;
        this.translatedText = translatedText;
        this.imagePath = imagePath;
        this.createdAt = createdAt;
    }

    /** First line of the source text, for the row's title. */
    @NonNull
    public String title() {
        String t = sourceText.trim();
        int newline = t.indexOf('\n');
        if (newline > 0) {
            t = t.substring(0, newline);
        }
        return t.length() > 60 ? t.substring(0, 60) + "…" : t;
    }

    /** e.g. {@code "EN → ZH"}. */
    @NonNull
    public String directionLabel() {
        return source.code().toUpperCase() + " → " + target.code().toUpperCase();
    }
}
