package com.falcon.ocrtrans.ui;

import android.graphics.Bitmap;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.data.HistoryItem;
import com.falcon.ocrtrans.data.HistoryStore;
import com.falcon.ocrtrans.engine.ResultHolder;
import com.falcon.ocrtrans.util.ImageLoader;

import java.util.Locale;

/**
 * Shows the repainted page alongside the recognised and translated text.
 *
 * <p>The translation stays editable: OCR and MT both make mistakes, and letting
 * the user correct the text before saving is cheaper than making them redo the
 * capture.
 */
public final class ResultActivity extends BaseActivity {

    @Nullable
    private ResultHolder.Payload payload;
    @Nullable
    private TextToSpeech tts;
    private boolean ttsReady;
    private boolean showingOriginal;

    private ImageView image;
    private EditText translatedField;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_result);
        setupToolbar(R.string.title_result);
        bindBusyOverlay(R.id.result_busy);

        // peek, not take: a configuration change recreates this activity and it
        // still needs the same page.
        payload = ResultHolder.peek();
        if (payload == null) {
            Toast.makeText(this, R.string.error_generic, Toast.LENGTH_SHORT).show();
            finish();
            return;
        }

        image = findViewById(R.id.result_image);
        translatedField = findViewById(R.id.result_translated_text);
        TextView sourceField = findViewById(R.id.result_source_text);
        TextView badge = findViewById(R.id.result_mode_badge);

        String sourceText = payload.result.ocr.plainText();
        String translatedText = payload.result.ocr.translatedText();

        sourceField.setText(sourceText);
        translatedField.setText(translatedText);
        badge.setText(payload.source.code().toUpperCase(Locale.US)
                + " → " + payload.target.code().toUpperCase(Locale.US));

        boolean empty = payload.result.ocr.isEmpty();
        findViewById(R.id.result_empty).setVisibility(empty ? View.VISIBLE : View.GONE);
        showRendered();

        initTts(payload.target);

        findViewById(R.id.result_speak).setOnClickListener(v -> speak());
        findViewById(R.id.result_save).setOnClickListener(v -> save());
        findViewById(R.id.result_toggle).setOnClickListener(v -> toggleImage());
    }

    private void showRendered() {
        if (payload == null) {
            return;
        }
        Bitmap toShow = showingOriginal || payload.rendered == null
                ? payload.original
                : payload.rendered;
        image.setImageBitmap(toShow);
        ((Button) findViewById(R.id.result_toggle)).setText(showingOriginal
                ? R.string.result_show_translated
                : R.string.result_show_original);
    }

    private void toggleImage() {
        showingOriginal = !showingOriginal;
        showRendered();
    }

    private void initTts(@NonNull Lang target) {
        tts = new TextToSpeech(this, status -> {
            ttsReady = status == TextToSpeech.SUCCESS;
            if (!ttsReady || tts == null) {
                return;
            }
            int result = tts.setLanguage(toLocale(target));
            // A missing voice pack is common for offline Korean and Japanese;
            // disable the button rather than failing silently on tap.
            if (result == TextToSpeech.LANG_MISSING_DATA
                    || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                ttsReady = false;
                findViewById(R.id.result_speak).setEnabled(false);
            }
        });
    }

    private static Locale toLocale(Lang lang) {
        switch (lang) {
            case KO:
                return Locale.KOREAN;
            case JA:
                return Locale.JAPANESE;
            case ZH:
                return Locale.CHINESE;
            case EN:
            default:
                return Locale.ENGLISH;
        }
    }

    private void speak() {
        if (!ttsReady || tts == null) {
            Toast.makeText(this, R.string.error_generic, Toast.LENGTH_SHORT).show();
            return;
        }
        String text = translatedField.getText().toString().trim();
        if (text.isEmpty()) {
            return;
        }
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "result");
    }

    private void save() {
        if (payload == null) {
            return;
        }
        final String sourceText = payload.result.ocr.plainText();
        final String translatedText = translatedField.getText().toString();
        final Bitmap toSave = payload.rendered != null ? payload.rendered : payload.original;
        final Lang source = payload.source;
        final Lang target = payload.target;

        showBusy(R.string.working);
        runInBackground(() -> {
            String path = ImageLoader.saveToAppStorage(ResultActivity.this, toSave, "page");
            HistoryStore store = new HistoryStore(ResultActivity.this);
            try {
                return store.insert(HistoryItem.Kind.IMAGE, source, target,
                        sourceText, translatedText, path);
            } finally {
                store.close();
            }
        }, new Callback<Long>() {
            @Override
            public void onSuccess(Long id) {
                hideBusy();
                Toast.makeText(ResultActivity.this, R.string.result_saved,
                        Toast.LENGTH_SHORT).show();
            }

            @Override
            public void onError(@NonNull Exception error) {
                hideBusy();
                Toast.makeText(ResultActivity.this, R.string.error_generic,
                        Toast.LENGTH_SHORT).show();
            }
        });
    }

    @Override
    protected void onDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
            tts = null;
        }
        // Release the page bitmaps once this screen is genuinely going away,
        // rather than on a rotation.
        if (isFinishing()) {
            ResultHolder.clear();
        }
        super.onDestroy();
    }
}
