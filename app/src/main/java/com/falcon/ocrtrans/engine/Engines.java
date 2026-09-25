package com.falcon.ocrtrans.engine;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.data.Prefs;
import com.falcon.ocrtrans.mt.MarianTranslator;
import com.falcon.ocrtrans.mt.PivotTranslator;
import com.falcon.ocrtrans.ocr.PaddleOcrEngine;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Process-wide owner of the OCR and MT engines and the thread they run on.
 *
 * <p>Both engines hold tens of megabytes of native session state and cost
 * seconds to construct, so they outlive any one screen. Neither is thread-safe,
 * which is why everything is funnelled through a <em>single</em> worker thread
 * rather than a pool — the serialisation is the point, not a limitation.
 */
public final class Engines {

    @Nullable
    private static Engines instance;

    private final Context context;
    private final ExecutorService worker;
    private final Handler main;

    @Nullable
    private PaddleOcrEngine ocrEngine;
    @Nullable
    private PivotTranslator translator;
    @Nullable
    private ModelValidator.Report report;

    private Engines(Context context) {
        this.context = context.getApplicationContext();
        this.worker = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "falcon-engine");
            // Below default priority: inference should never outrank the UI
            // thread, or scrolling stutters while a page is being processed.
            t.setPriority(Thread.NORM_PRIORITY - 1);
            return t;
        });
        this.main = new Handler(Looper.getMainLooper());
    }

    @NonNull
    public static synchronized Engines get(@NonNull Context context) {
        if (instance == null) {
            instance = new Engines(context);
        }
        return instance;
    }

    /** The shared inference thread. Everything touching an engine belongs here. */
    @NonNull
    public ExecutorService worker() {
        return worker;
    }

    /** Posts back to the UI thread. */
    public void postToMain(@NonNull Runnable runnable) {
        main.post(runnable);
    }

    @NonNull
    public synchronized PaddleOcrEngine ocr() {
        if (ocrEngine == null) {
            ocrEngine = new PaddleOcrEngine(context);
        }
        // Re-applied on every access rather than only at construction, so a
        // change to the Image Quality setting takes effect on the next scan
        // instead of after a restart.
        ocrEngine.setDetectionLimit(new Prefs(context).imageQuality().detectionLimit);
        return ocrEngine;
    }

    /**
     * The translator, wrapped so that CJK-to-CJK directions route through
     * English. No direct OPUS-MT model exists for those pairs, so the wrapper is
     * what makes six of the twelve advertised directions work at all.
     */
    @NonNull
    public synchronized PivotTranslator translator() {
        if (translator == null) {
            translator = new PivotTranslator(new MarianTranslator(context));
        }
        return translator;
    }

    @NonNull
    public TranslationPipeline pipeline() {
        return new TranslationPipeline(ocr(), translator());
    }

    /** Cached model inventory; the scan touches a few hundred asset entries. */
    @NonNull
    public synchronized ModelValidator.Report models() {
        if (report == null) {
            report = ModelValidator.validate(context);
        }
        return report;
    }

    /** Forgets the cached inventory, for use after a debug model push. */
    public synchronized void invalidateModels() {
        report = null;
    }

    /** Releases native sessions while keeping the worker alive. */
    public synchronized void releaseEngines() {
        if (ocrEngine != null) {
            ocrEngine.close();
            ocrEngine = null;
        }
        if (translator != null) {
            translator.close();
            translator = null;
        }
    }
}
