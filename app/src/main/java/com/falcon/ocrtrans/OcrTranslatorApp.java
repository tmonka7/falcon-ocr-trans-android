package com.falcon.ocrtrans;

import android.app.Application;
import android.content.ComponentCallbacks2;

import com.falcon.ocrtrans.engine.Engines;
import com.falcon.ocrtrans.engine.ResultHolder;

/** Application entry point; releases native sessions under memory pressure. */
public final class OcrTranslatorApp extends Application {

    @Override
    public void onTrimMemory(int level) {
        super.onTrimMemory(level);

        // The engines hold tens of megabytes of native session state plus a
        // loaded MT pair. When the system says it is about to start killing
        // processes, giving that back is far cheaper than being killed — the
        // sessions rebuild lazily on the next use.
        if (level >= ComponentCallbacks2.TRIM_MEMORY_RUNNING_LOW) {
            ResultHolder.clear();
            Engines.get(this).releaseEngines();
        }
    }

    @Override
    public void onLowMemory() {
        super.onLowMemory();
        ResultHolder.clear();
        Engines.get(this).releaseEngines();
    }
}
