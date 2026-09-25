package com.falcon.ocrtrans.data;

import android.content.Context;
import android.content.SharedPreferences;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.core.Lang;

/** Typed access to the handful of settings the app persists. */
public final class Prefs {

    private static final String FILE = "falcon_ocr_prefs";

    private static final String KEY_SOURCE = "source_lang";
    private static final String KEY_TARGET = "target_lang";
    private static final String KEY_OCR_AUTO = "ocr_auto_detect";
    private static final String KEY_IMAGE_QUALITY = "image_quality";
    private static final String KEY_AUTO_TRANSLATE = "auto_translate";
    private static final String KEY_PDF_OUTPUT = "pdf_output_format";

    /** Detection input size, which trades recognition of small text against speed. */
    public enum ImageQuality {
        LOW(640), MEDIUM(960), HIGH(1280);

        public final int detectionLimit;

        ImageQuality(int detectionLimit) {
            this.detectionLimit = detectionLimit;
        }

        @NonNull
        public static ImageQuality fromName(@Nullable String name) {
            if (name != null) {
                for (ImageQuality q : values()) {
                    if (q.name().equalsIgnoreCase(name)) {
                        return q;
                    }
                }
            }
            return HIGH;
        }
    }

    /** What a PDF job writes out. */
    public enum PdfOutput {
        PDF, DOCX, TXT;

        @NonNull
        public static PdfOutput fromName(@Nullable String name) {
            if (name != null) {
                for (PdfOutput o : values()) {
                    if (o.name().equalsIgnoreCase(name)) {
                        return o;
                    }
                }
            }
            return PDF;
        }
    }

    private final SharedPreferences prefs;

    public Prefs(@NonNull Context context) {
        this.prefs = context.getApplicationContext()
                .getSharedPreferences(FILE, Context.MODE_PRIVATE);
    }

    @NonNull
    public Lang sourceLang() {
        return Lang.fromCodeOr(prefs.getString(KEY_SOURCE, Lang.EN.code()), Lang.EN);
    }

    public void setSourceLang(@NonNull Lang lang) {
        prefs.edit().putString(KEY_SOURCE, lang.code()).apply();
    }

    @NonNull
    public Lang targetLang() {
        return Lang.fromCodeOr(prefs.getString(KEY_TARGET, Lang.ZH.code()), Lang.ZH);
    }

    public void setTargetLang(@NonNull Lang lang) {
        prefs.edit().putString(KEY_TARGET, lang.code()).apply();
    }

    /** Swaps the pair, as the arrow button between the two selectors does. */
    public void swapLanguages() {
        Lang source = sourceLang();
        prefs.edit()
                .putString(KEY_SOURCE, targetLang().code())
                .putString(KEY_TARGET, source.code())
                .apply();
    }

    /** True when the source script should be guessed instead of taken from settings. */
    public boolean autoDetectScript() {
        return prefs.getBoolean(KEY_OCR_AUTO, true);
    }

    public void setAutoDetectScript(boolean value) {
        prefs.edit().putBoolean(KEY_OCR_AUTO, value).apply();
    }

    @NonNull
    public ImageQuality imageQuality() {
        return ImageQuality.fromName(prefs.getString(KEY_IMAGE_QUALITY, ImageQuality.HIGH.name()));
    }

    public void setImageQuality(@NonNull ImageQuality quality) {
        prefs.edit().putString(KEY_IMAGE_QUALITY, quality.name()).apply();
    }

    public boolean autoTranslate() {
        return prefs.getBoolean(KEY_AUTO_TRANSLATE, true);
    }

    public void setAutoTranslate(boolean value) {
        prefs.edit().putBoolean(KEY_AUTO_TRANSLATE, value).apply();
    }

    @NonNull
    public PdfOutput pdfOutput() {
        return PdfOutput.fromName(prefs.getString(KEY_PDF_OUTPUT, PdfOutput.PDF.name()));
    }

    public void setPdfOutput(@NonNull PdfOutput output) {
        prefs.edit().putString(KEY_PDF_OUTPUT, output.name()).apply();
    }
}
