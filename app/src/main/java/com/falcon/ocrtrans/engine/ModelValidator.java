package com.falcon.ocrtrans.engine;

import android.content.Context;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.util.Assets;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Checks the bundled model tree before any engine tries to load from it.
 *
 * <p>The failure this exists to prevent is a stack trace forty frames deep
 * inside ONNX Runtime that says nothing about which file is missing. Running
 * this first turns "the app crashed" into a precise list of absent assets and
 * the script that produces them.
 */
public final class ModelValidator {

    /** What the installed model tree can currently do. */
    public static final class Report {

        private final List<String> missing;
        private final Set<Lang> ocrLanguages;
        private final Set<String> mtPairs;

        Report(List<String> missing, Set<Lang> ocrLanguages, Set<String> mtPairs) {
            this.missing = missing;
            this.ocrLanguages = ocrLanguages;
            this.mtPairs = mtPairs;
        }

        /** True when detection plus at least one recognition head is present. */
        public boolean canRunOcr() {
            return !ocrLanguages.isEmpty();
        }

        /** True if the direction is served directly or by pivoting through English. */
        public boolean canTranslate(@NonNull Lang from, @NonNull Lang to) {
            if (from == to) {
                return true;
            }
            if (mtPairs.contains(Lang.pairKey(from, to))) {
                return true;
            }
            return mtPairs.contains(Lang.pairKey(from, Lang.EN))
                    && mtPairs.contains(Lang.pairKey(Lang.EN, to));
        }

        /** True if the direction works only by chaining two models. */
        public boolean isPivoted(@NonNull Lang from, @NonNull Lang to) {
            return from != to
                    && !mtPairs.contains(Lang.pairKey(from, to))
                    && canTranslate(from, to);
        }

        public boolean canRecognize(@NonNull Lang lang) {
            return ocrLanguages.contains(lang);
        }

        @NonNull
        public Set<Lang> ocrLanguages() {
            return Collections.unmodifiableSet(ocrLanguages);
        }

        @NonNull
        public Set<String> mtPairs() {
            return Collections.unmodifiableSet(mtPairs);
        }

        @NonNull
        public List<String> missing() {
            return Collections.unmodifiableList(missing);
        }

        public boolean isComplete() {
            return missing.isEmpty();
        }

        /** Human-readable summary for the Settings screen and logcat. */
        @NonNull
        public String describe() {
            StringBuilder sb = new StringBuilder();
            sb.append("OCR: ");
            if (ocrLanguages.isEmpty()) {
                sb.append("unavailable");
            } else {
                for (Lang l : ocrLanguages) {
                    sb.append(l.code()).append(' ');
                }
            }
            sb.append("\nMT pairs: ").append(mtPairs.isEmpty() ? "none" : mtPairs.size());
            if (!missing.isEmpty()) {
                sb.append("\nMissing ").append(missing.size()).append(" file(s):");
                int shown = Math.min(missing.size(), 12);
                for (int i = 0; i < shown; i++) {
                    sb.append("\n  ").append(missing.get(i));
                }
                if (missing.size() > shown) {
                    sb.append("\n  … and ").append(missing.size() - shown).append(" more");
                }
                sb.append("\n\nRun tools/fetch_models.sh to populate assets/model.");
            }
            return sb.toString();
        }
    }

    private ModelValidator() {
    }

    @NonNull
    public static Report validate(@NonNull Context ctx) {
        List<String> missing = new ArrayList<>();
        Set<Lang> ocrLangs = new LinkedHashSet<>();
        Set<String> pairs = new LinkedHashSet<>();

        boolean det = require(ctx, ModelPaths.DET_MODEL, missing);
        // The angle classifier is genuinely optional: without it upside-down
        // lines recognise poorly, but everything else still works.
        Assets.exists(ctx, ModelPaths.CLS_MODEL);

        for (Lang lang : Lang.values()) {
            boolean ok = require(ctx, ModelPaths.recModel(lang), missing)
                    & require(ctx, ModelPaths.recDict(lang), missing);
            if (det && ok) {
                ocrLangs.add(lang);
            }
        }

        for (Lang from : Lang.values()) {
            for (Lang to : Lang.values()) {
                if (from == to) {
                    continue;
                }
                // Only pairs involving English are reported as missing when
                // absent. Helsinki-NLP publishes no CJK-to-CJK OPUS-MT model, so
                // listing ko-ja as a missing file would be telling the user to go
                // fetch something that does not exist; those directions are
                // expected to be served by PivotTranslator instead.
                boolean expected = from == Lang.EN || to == Lang.EN;
                List<String> sink = expected ? missing : new ArrayList<>();

                boolean ok = require(ctx, ModelPaths.mtEncoder(from, to), sink)
                        & require(ctx, ModelPaths.mtDecoder(from, to), sink)
                        & require(ctx, ModelPaths.mtSourceSpm(from, to), sink)
                        & require(ctx, ModelPaths.mtVocab(from, to), sink)
                        & require(ctx, ModelPaths.mtConfig(from, to), sink);
                if (ok) {
                    pairs.add(Lang.pairKey(from, to));
                }
            }
        }
        return new Report(missing, ocrLangs, pairs);
    }

    private static boolean require(Context ctx, String path, List<String> missing) {
        if (Assets.exists(ctx, path)) {
            return true;
        }
        missing.add(path);
        return false;
    }
}
