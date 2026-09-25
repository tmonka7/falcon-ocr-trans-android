package com.falcon.ocrtrans.engine;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.core.Lang;

/**
 * Guesses which of the four supported languages a string is written in.
 *
 * <p>This is deliberately a <em>script</em> test, not a language classifier:
 * Hangul implies Korean and Kana implies Japanese unambiguously, so those two
 * are decided by a single character class. The genuine ambiguity is Han
 * characters, which Japanese and Chinese share — resolved by whether any Kana
 * appears anywhere in the text, since Japanese prose essentially always contains
 * some. Pure-Kanji Japanese (a sign reading 出口, say) will be called Chinese,
 * which is the accepted failure mode for a detector this cheap.
 */
public final class ScriptDetector {

    /** Minimum share of scored characters before a guess overrides the setting. */
    private static final float CONFIDENCE_THRESHOLD = 0.08f;

    private ScriptDetector() {
    }

    /**
     * @param fallback returned when the text carries no usable script signal
     */
    @NonNull
    public static Lang detect(@Nullable String text, @NonNull Lang fallback) {
        if (text == null || text.isEmpty()) {
            return fallback;
        }

        int hangul = 0, kana = 0, han = 0, latin = 0, total = 0;

        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (Character.isWhitespace(c) || Character.isDigit(c)) {
                continue;
            }
            Character.UnicodeBlock block = Character.UnicodeBlock.of(c);
            if (block == Character.UnicodeBlock.HANGUL_SYLLABLES
                    || block == Character.UnicodeBlock.HANGUL_JAMO
                    || block == Character.UnicodeBlock.HANGUL_COMPATIBILITY_JAMO) {
                hangul++;
                total++;
            } else if (block == Character.UnicodeBlock.HIRAGANA
                    || block == Character.UnicodeBlock.KATAKANA) {
                kana++;
                total++;
            } else if (block == Character.UnicodeBlock.CJK_UNIFIED_IDEOGRAPHS
                    || block == Character.UnicodeBlock.CJK_UNIFIED_IDEOGRAPHS_EXTENSION_A) {
                han++;
                total++;
            } else if (block == Character.UnicodeBlock.BASIC_LATIN
                    || block == Character.UnicodeBlock.LATIN_1_SUPPLEMENT) {
                if (Character.isLetter(c)) {
                    latin++;
                    total++;
                }
            }
        }

        if (total == 0) {
            return fallback;
        }

        // Hangul is exclusive to Korean, so even a small share settles it.
        if (hangul / (float) total > CONFIDENCE_THRESHOLD) {
            return Lang.KO;
        }
        // Kana is exclusive to Japanese and disambiguates shared Han characters.
        if (kana / (float) total > CONFIDENCE_THRESHOLD) {
            return Lang.JA;
        }
        if (han > 0 && han >= latin) {
            return Lang.ZH;
        }
        if (latin > 0) {
            return Lang.EN;
        }
        return fallback;
    }
}
