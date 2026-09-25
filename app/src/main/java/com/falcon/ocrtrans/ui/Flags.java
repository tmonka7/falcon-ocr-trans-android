package com.falcon.ocrtrans.ui;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.core.Lang;

/**
 * Emoji flags for the language pickers.
 *
 * <p>Built from regional-indicator pairs rather than bundled images, so they
 * inherit the system emoji font and cost nothing in the APK.
 *
 * <p>These are country flags standing in for languages, which is a compromise
 * the mock makes too: English is shown with the UK flag although the language is
 * not the country's alone.
 */
public final class Flags {

    private Flags() {
    }

    @NonNull
    public static String of(@NonNull Lang lang) {
        switch (lang) {
            case KO:
                return flag("KR");
            case JA:
                return flag("JP");
            case ZH:
                return flag("CN");
            case EN:
            default:
                return flag("GB");
        }
    }

    /** Maps an ISO 3166 pair onto the regional indicator symbols U+1F1E6…U+1F1FF. */
    private static String flag(String countryCode) {
        int first = Character.codePointAt(countryCode, 0) - 'A' + 0x1F1E6;
        int second = Character.codePointAt(countryCode, 1) - 'A' + 0x1F1E6;
        return new String(Character.toChars(first)) + new String(Character.toChars(second));
    }
}
