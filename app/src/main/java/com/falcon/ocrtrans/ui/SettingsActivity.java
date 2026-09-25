package com.falcon.ocrtrans.ui;

import android.app.AlertDialog;
import android.os.Bundle;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.BuildConfig;
import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.data.Prefs;
import com.falcon.ocrtrans.engine.ModelValidator;

/** Preferences, plus a report on what the installed model tree can do. */
public final class SettingsActivity extends BaseActivity {

    private Prefs prefs;

    private OptionRow ocrLanguageRow;
    private OptionRow qualityRow;
    private OptionRow sourceRow;
    private OptionRow targetRow;
    private OptionRow modelsRow;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);
        setupToolbar(R.string.title_settings);

        prefs = new Prefs(this);

        ocrLanguageRow = new OptionRow(findViewById(R.id.settings_ocr_language))
                .icon(R.drawable.ic_text)
                .label(R.string.settings_ocr_language)
                .onClick(v -> toggleAutoDetect());

        qualityRow = new OptionRow(findViewById(R.id.settings_image_quality))
                .icon(R.drawable.ic_image)
                .label(R.string.settings_image_quality)
                .onClick(v -> promptForQuality());

        new OptionRow(findViewById(R.id.settings_auto_translate))
                .icon(R.drawable.ic_translate)
                .label(R.string.settings_auto_translation)
                .asSwitch(prefs.autoTranslate(), prefs::setAutoTranslate);

        sourceRow = new OptionRow(findViewById(R.id.settings_default_source))
                .icon(R.drawable.ic_home)
                .label(R.string.settings_default_source)
                .onClick(v -> startActivity(
                        LanguageActivity.intent(this, LanguageActivity.Side.SOURCE)));

        targetRow = new OptionRow(findViewById(R.id.settings_default_target))
                .icon(R.drawable.ic_add)
                .label(R.string.settings_default_target)
                .onClick(v -> startActivity(
                        LanguageActivity.intent(this, LanguageActivity.Side.TARGET)));

        modelsRow = new OptionRow(findViewById(R.id.settings_models))
                .icon(R.drawable.ic_info)
                .label(R.string.settings_models)
                .onClick(v -> showModelReport());

        new OptionRow(findViewById(R.id.settings_about))
                .icon(R.drawable.ic_info)
                .label(R.string.settings_about)
                .value("v" + BuildConfig.VERSION_NAME)
                .onClick(v -> showAbout());

        new OptionRow(findViewById(R.id.settings_help))
                .icon(R.drawable.ic_help)
                .label(R.string.settings_help)
                .onClick(v -> showHelp());
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshValues();
    }

    private void refreshValues() {
        ocrLanguageRow.value(prefs.autoDetectScript()
                ? getString(R.string.settings_auto)
                : prefs.sourceLang().englishName());
        qualityRow.value(prefs.imageQuality().name());
        sourceRow.value(prefs.sourceLang().englishName());
        targetRow.value(prefs.targetLang().englishName());

        runInBackground(() -> engines().models(), new Callback<ModelValidator.Report>() {
            @Override
            public void onSuccess(ModelValidator.Report report) {
                modelsRow.value(report.isComplete()
                        ? report.ocrLanguages().size() + " / " + report.mtPairs().size()
                        : getString(R.string.error_models_missing));
            }

            @Override
            public void onError(@NonNull Exception error) {
                modelsRow.value(getString(R.string.error_generic));
            }
        });
    }

    private void toggleAutoDetect() {
        boolean next = !prefs.autoDetectScript();
        prefs.setAutoDetectScript(next);
        refreshValues();
    }

    private void promptForQuality() {
        final Prefs.ImageQuality[] values = Prefs.ImageQuality.values();
        final String[] labels = new String[values.length];
        for (int i = 0; i < values.length; i++) {
            labels[i] = values[i].name() + "  (" + values[i].detectionLimit + " px)";
        }
        new AlertDialog.Builder(this)
                .setTitle(R.string.settings_image_quality)
                .setItems(labels, (dialog, which) -> {
                    prefs.setImageQuality(values[which]);
                    refreshValues();
                })
                .show();
    }

    private void showModelReport() {
        runInBackground(() -> engines().models(), new Callback<ModelValidator.Report>() {
            @Override
            public void onSuccess(ModelValidator.Report report) {
                StringBuilder sb = new StringBuilder(report.describe());
                // Spell out which directions are chained, since that is the main
                // thing a user would otherwise misread as the model being bad.
                StringBuilder pivoted = new StringBuilder();
                for (Lang from : Lang.userFacing()) {
                    for (Lang to : Lang.userFacing()) {
                        if (report.isPivoted(from, to)) {
                            pivoted.append("\n  ").append(Lang.pairKey(from, to));
                        }
                    }
                }
                if (pivoted.length() > 0) {
                    sb.append("\n\nRouted through English:").append(pivoted);
                }
                new AlertDialog.Builder(SettingsActivity.this)
                        .setTitle(R.string.settings_models)
                        .setMessage(sb.toString())
                        .setPositiveButton(R.string.action_ok, null)
                        .show();
            }

            @Override
            public void onError(@NonNull Exception error) {
                new AlertDialog.Builder(SettingsActivity.this)
                        .setMessage(R.string.error_generic)
                        .setPositiveButton(R.string.action_ok, null)
                        .show();
            }
        });
    }

    private void showAbout() {
        new AlertDialog.Builder(this)
                .setTitle(R.string.app_name)
                .setMessage(getString(R.string.app_name) + " v" + BuildConfig.VERSION_NAME
                        + "\n\nOffline OCR and translation."
                        + "\n\nText recognition: PaddleOCR (Apache 2.0)."
                        + "\nTranslation: OPUS-MT by Helsinki-NLP (CC-BY 4.0)."
                        + "\nInference: ONNX Runtime."
                        + "\n\nNo image or text leaves the device.")
                .setPositiveButton(R.string.action_ok, null)
                .show();
    }

    private void showHelp() {
        new AlertDialog.Builder(this)
                .setTitle(R.string.settings_help)
                .setMessage("Tips\n\n"
                        + "• Hold the camera square to the page; heavy perspective "
                        + "reduces accuracy.\n"
                        + "• Raise Image Quality if small text is being missed.\n"
                        + "• Japanese and Chinese translate to each other "
                        + "through English, which is slower and less accurate than any "
                        + "pair involving English directly.\n"
                        + "• The translation on the result screen is editable before "
                        + "you save it.")
                .setPositiveButton(R.string.action_ok, null)
                .show();
    }
}
