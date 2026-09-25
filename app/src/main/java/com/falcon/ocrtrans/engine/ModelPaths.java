package com.falcon.ocrtrans.engine;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.core.Lang;

/**
 * The single source of truth for where model files live inside {@code assets/}.
 *
 * <p>Both the Java loaders and {@code tools/fetch_models.sh} are written against
 * this layout, so a change here has to be mirrored in the script — that pairing
 * is the whole reason the paths are centralised rather than inlined at each use.
 */
public final class ModelPaths {

    public static final String ROOT = "model";

    public static final String OCR_ROOT = ROOT + "/ocr";
    public static final String MT_ROOT = ROOT + "/mt";

    /** Shared text detector — language independent. */
    public static final String DET_MODEL = OCR_ROOT + "/det/det.onnx";
    /** 180-degree orientation classifier, run before recognition. */
    public static final String CLS_MODEL = OCR_ROOT + "/cls/cls.onnx";

    private ModelPaths() {
    }

    /** Recognition weights for a script, e.g. {@code model/ocr/rec/korean/rec.onnx}. */
    @NonNull
    public static String recModel(@NonNull Lang lang) {
        return OCR_ROOT + "/rec/" + recDirName(lang) + "/rec.onnx";
    }

    /** Character dictionary paired with {@link #recModel(Lang)}, one glyph per line. */
    @NonNull
    public static String recDict(@NonNull Lang lang) {
        return OCR_ROOT + "/rec/" + recDirName(lang) + "/dict.txt";
    }

    /**
     * PaddleOCR ships one recognition head per script family. Latin text is
     * covered by the English model; the three CJK models each also cover Latin
     * digits and punctuation, which is what makes mixed-script signage work.
     */
    @NonNull
    public static String recDirName(@NonNull Lang lang) {
        switch (lang) {
            case KO:
                return "korean";
            case JA:
                return "japan";
            case ZH:
                return "chinese";
            case EN:
            default:
                return "english";
        }
    }

    /** Directory holding one directed OPUS-MT pair, e.g. {@code model/mt/en-ko}. */
    @NonNull
    public static String mtDir(@NonNull Lang from, @NonNull Lang to) {
        return MT_ROOT + "/" + Lang.pairKey(from, to);
    }

    @NonNull
    public static String mtEncoder(@NonNull Lang from, @NonNull Lang to) {
        return mtDir(from, to) + "/encoder.int8.onnx";
    }

    @NonNull
    public static String mtDecoder(@NonNull Lang from, @NonNull Lang to) {
        return mtDir(from, to) + "/decoder.int8.onnx";
    }

    /** SentencePiece pieces for the source side: {@code piece<TAB>score} per line. */
    @NonNull
    public static String mtSourceSpm(@NonNull Lang from, @NonNull Lang to) {
        return mtDir(from, to) + "/source.spm.tsv";
    }

    /**
     * Token to id table: {@code token<TAB>id} per line. This is the target
     * vocabulary, used to decode output; for joint-vocabulary models it also
     * serves the source side.
     */
    @NonNull
    public static String mtVocab(@NonNull Lang from, @NonNull Lang to) {
        return mtDir(from, to) + "/vocab.tsv";
    }

    /**
     * Optional source-side table, present only for models trained with separate
     * vocabularies (the tc-big en-ko release). Absent means {@link #mtVocab}
     * serves both sides.
     */
    @NonNull
    public static String mtSourceVocab(@NonNull Lang from, @NonNull Lang to) {
        return mtDir(from, to) + "/source_vocab.tsv";
    }

    /** Special token ids and decode limits, written by the conversion script. */
    @NonNull
    public static String mtConfig(@NonNull Lang from, @NonNull Lang to) {
        return mtDir(from, to) + "/config.json";
    }
}
