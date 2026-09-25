package com.falcon.ocrtrans.core;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

/**
 * The four languages this build implements. The interface offers only the
 * subset in {@link #userFacing()}.
 *
 * <p>Note the code for Japanese is {@code ja}, not {@code jp}: {@code ja} is the
 * ISO 639-1 language code, while {@code jp} is only the ISO 3166 code for the
 * country. Model directories, preferences and history rows all use {@code ja}.
 * {@link #fromCode(String)} still accepts {@code "jp"} so older stored values
 * and hand-written intents keep resolving.
 */
public enum Lang {
    EN("en", "English", "English"),
    KO("ko", "Korean", "한국어"),
    JA("ja", "Japanese", "日本語"),
    ZH("zh", "Chinese", "中文");

    /**
     * The languages a user can see and choose, in picker order.
     *
     * <p>Korean is fully implemented — recognition head, dictionary, both MT
     * directions, script detection, TTS locale and flag — but is withheld from
     * the interface for now. It stays in the enum so that code, tests and stored
     * data keep compiling and resolving; every screen, default and auto-detection
     * path reads this list instead of {@link #values()}, so it never surfaces.
     * To ship Korean, uncomment the {@code KO} line below; nothing else changes.
     */
    private static final Lang[] USER_FACING = {
            EN,
            // KO, // Korean: implemented, hidden from the UI. Uncomment to enable.
            JA,
            ZH,
    };

    private final String code;
    private final String englishName;
    private final String nativeName;

    Lang(String code, String englishName, String nativeName) {
        this.code = code;
        this.englishName = englishName;
        this.nativeName = nativeName;
    }

    public String code() {
        return code;
    }

    public String englishName() {
        return englishName;
    }

    public String nativeName() {
        return nativeName;
    }

    /** Label as shown in the language picker, e.g. {@code "Korean (한국어)"}. */
    public String displayName() {
        return EN == this ? englishName : englishName + " (" + nativeName + ")";
    }

    /** @return a copy of the languages shown in the interface, in picker order. */
    @NonNull
    public static Lang[] userFacing() {
        return USER_FACING.clone();
    }

    /** True if this language may appear anywhere the user can see it. */
    public boolean isUserFacing() {
        for (Lang l : USER_FACING) {
            if (l == this) {
                return true;
            }
        }
        return false;
    }

    /**
     * Like {@link #fromCodeOr(String, Lang)}, but also falls back when the code
     * names a language that is implemented yet hidden — a Korean preference
     * saved before Korean was withheld, for instance.
     */
    @NonNull
    public static Lang userFacingOr(@Nullable String code, @NonNull Lang fallback) {
        Lang l = fromCode(code);
        return l != null && l.isUserFacing() ? l : fallback;
    }

    /** @return the language, or {@code null} if {@code code} names none of them. */
    @Nullable
    public static Lang fromCode(@Nullable String code) {
        if (code == null) {
            return null;
        }
        String c = code.trim().toLowerCase();
        int sep = c.indexOf('-');
        if (sep < 0) {
            sep = c.indexOf('_');
        }
        if (sep > 0) {
            c = c.substring(0, sep);
        }
        switch (c) {
            case "en":
                return EN;
            case "ko":
            case "kor":
                return KO;
            case "ja":
            case "jp":
            case "jpn":
                return JA;
            case "zh":
            case "cn":
            case "chi":
            case "zho":
                return ZH;
            default:
                return null;
        }
    }

    @NonNull
    public static Lang fromCodeOr(@Nullable String code, @NonNull Lang fallback) {
        Lang l = fromCode(code);
        return l != null ? l : fallback;
    }

    /** Directed pair key used for model directories and routing, e.g. {@code "en-ko"}. */
    public static String pairKey(@NonNull Lang from, @NonNull Lang to) {
        return from.code + "-" + to.code;
    }
}
