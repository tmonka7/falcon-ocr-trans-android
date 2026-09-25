package com.falcon.ocrtrans.ui;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.data.HistoryItem;
import com.falcon.ocrtrans.data.HistoryStore;
import com.falcon.ocrtrans.data.Prefs;

/** Type-and-translate, without going through OCR. */
public final class TranslateActivity extends BaseActivity {

    private static final int MAX_CHARS = 500;

    private Prefs prefs;
    private LanguageBar languageBar;
    private EditText input;
    private TextView output;
    private TextView note;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_translate);
        setupToolbar(R.string.title_translate);
        bindBusyOverlay(R.id.translate_busy);

        prefs = new Prefs(this);
        input = findViewById(R.id.translate_input);
        output = findViewById(R.id.translate_output);
        note = findViewById(R.id.translate_note);

        TextView counter = findViewById(R.id.translate_input_counter);
        input.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int a, int b, int c) {
            }

            @Override
            public void onTextChanged(CharSequence s, int a, int b, int c) {
            }

            @Override
            public void afterTextChanged(Editable s) {
                counter.setText(getString(R.string.translate_counter, s.length(), MAX_CHARS));
            }
        });
        counter.setText(getString(R.string.translate_counter, 0, MAX_CHARS));

        languageBar = new LanguageBar(this, findViewById(R.id.translate_language_bar), prefs,
                side -> startActivity(LanguageActivity.intent(this, side)));
        languageBar.setListener((source, target) -> {
            ((TextView) findViewById(R.id.translate_output_lang)).setText(target.displayName());
            updatePivotNote(source, target);
        });

        findViewById(R.id.translate_action).setOnClickListener(v -> translate());
        findViewById(R.id.translate_copy_source).setOnClickListener(
                v -> copy(input.getText().toString()));
        findViewById(R.id.translate_copy_output).setOnClickListener(
                v -> copy(output.getText().toString()));
    }

    @Override
    protected void onResume() {
        super.onResume();
        languageBar.refresh();
    }

    /** Warns when this direction is chained through English. */
    private void updatePivotNote(@NonNull Lang source, @NonNull Lang target) {
        boolean pivoted = engines().models().isPivoted(source, target);
        note.setVisibility(pivoted ? View.VISIBLE : View.GONE);
        note.setText(R.string.lang_pivoted);
    }

    private void translate() {
        final String text = input.getText().toString().trim();
        if (text.isEmpty()) {
            return;
        }
        final Lang source = prefs.sourceLang();
        final Lang target = prefs.targetLang();
        if (source == target) {
            output.setText(text);
            return;
        }

        showBusy(R.string.working);
        runInBackground(() -> {
            String translated = engines().translator().translate(text, source, target);

            HistoryStore store = new HistoryStore(TranslateActivity.this);
            try {
                store.insert(HistoryItem.Kind.MANUAL, source, target, text, translated, null);
            } finally {
                store.close();
            }
            return translated;
        }, new Callback<String>() {
            @Override
            public void onSuccess(String translated) {
                hideBusy();
                output.setText(translated);
            }

            @Override
            public void onError(@NonNull Exception error) {
                hideBusy();
                String message = error.getMessage();
                output.setText("");
                Toast.makeText(TranslateActivity.this,
                        message != null ? message : getString(R.string.error_generic),
                        Toast.LENGTH_LONG).show();
            }
        });
    }

    private void copy(@NonNull String text) {
        if (text.isEmpty()) {
            return;
        }
        ClipboardManager clipboard =
                (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (clipboard == null) {
            return;
        }
        clipboard.setPrimaryClip(ClipData.newPlainText(getString(R.string.app_name), text));
        Toast.makeText(this, R.string.translate_copied, Toast.LENGTH_SHORT).show();
    }
}
