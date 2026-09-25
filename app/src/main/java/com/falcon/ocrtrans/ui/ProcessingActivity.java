package com.falcon.ocrtrans.ui;

import android.content.Intent;
import android.graphics.Bitmap;
import android.net.Uri;
import android.widget.Toast;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.data.Prefs;
import com.falcon.ocrtrans.engine.ResultHolder;
import com.falcon.ocrtrans.engine.TranslationPipeline;
import com.falcon.ocrtrans.util.ImageLoader;

/**
 * Shared "run the pipeline on one image, then show the result" behaviour.
 *
 * <p>Camera and gallery import differ only in where the bitmap comes from, so
 * everything after that point lives here.
 */
abstract class ProcessingActivity extends BaseActivity {

    /** Decodes, recognises, translates and repaints, then opens the result screen. */
    protected void processUri(@NonNull Uri uri) {
        runInBackground(() -> {
            Bitmap bitmap = ImageLoader.load(ProcessingActivity.this, uri);
            return runPipeline(bitmap);
        }, resultCallback());
    }

    protected void processBitmap(@NonNull Bitmap bitmap) {
        runInBackground(() -> runPipeline(bitmap), resultCallback());
    }

    @NonNull
    private ResultHolder.Payload runPipeline(@NonNull Bitmap bitmap) throws Exception {
        Prefs prefs = new Prefs(this);
        Lang source = prefs.sourceLang();
        Lang target = prefs.targetLang();

        TranslationPipeline.Options options = new TranslationPipeline.Options();
        options.translate = prefs.autoTranslate();
        options.autoDetectSource = prefs.autoDetectScript();

        TranslationPipeline.Result result =
                engines().pipeline().process(bitmap, source, target, options);

        // The pipeline may have overridden the configured source after reading
        // the page; the result screen should report what was actually used.
        return new ResultHolder.Payload(
                bitmap, result.rendered, result, result.detectedSource, target);
    }

    @NonNull
    private Callback<ResultHolder.Payload> resultCallback() {
        showBusy(R.string.working);
        return new Callback<ResultHolder.Payload>() {
            @Override
            public void onSuccess(ResultHolder.Payload payload) {
                hideBusy();
                ResultHolder.put(payload);
                startActivity(new Intent(ProcessingActivity.this, ResultActivity.class));
            }

            @Override
            public void onError(@NonNull Exception error) {
                hideBusy();
                String message = error.getMessage();
                Toast.makeText(ProcessingActivity.this,
                        message != null ? message : getString(R.string.error_generic),
                        Toast.LENGTH_LONG).show();
            }
        };
    }
}
