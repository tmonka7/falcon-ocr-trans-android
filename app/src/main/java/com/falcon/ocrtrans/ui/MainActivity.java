package com.falcon.ocrtrans.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.annotation.DrawableRes;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.annotation.StringRes;
import androidx.core.content.ContextCompat;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.data.Prefs;
import com.falcon.ocrtrans.engine.ModelValidator;

/** Home: the action tiles, the language pair, and the navigation rail. */
public final class MainActivity extends BaseActivity {

    private Prefs prefs;
    private LanguageBar languageBar;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = new Prefs(this);

        bindNavRail();
        bindTiles();

        languageBar = new LanguageBar(this, findViewById(R.id.language_bar), prefs,
                side -> startActivity(LanguageActivity.intent(this, side)));

        findViewById(R.id.main_manual_translate).setOnClickListener(
                v -> startActivity(new Intent(this, TranslateActivity.class)));
        findViewById(R.id.main_models_status).setOnClickListener(
                v -> startActivity(new Intent(this, SettingsActivity.class)));
    }

    @Override
    protected void onResume() {
        super.onResume();
        languageBar.refresh();
        showModelWarningIfNeeded();
    }

    private void bindNavRail() {
        bindNavItem(R.id.nav_home, R.drawable.ic_home, R.string.nav_home, true, null);
        bindNavItem(R.id.nav_image, R.drawable.ic_image, R.string.nav_image, false,
                v -> startActivity(new Intent(this, ImageImportActivity.class)));
        bindNavItem(R.id.nav_pdf, R.drawable.ic_pdf, R.string.nav_pdf, false,
                v -> startActivity(new Intent(this, PdfActivity.class)));
        bindNavItem(R.id.nav_history, R.drawable.ic_history, R.string.nav_history, false,
                v -> startActivity(new Intent(this, HistoryActivity.class)));
        bindNavItem(R.id.nav_settings, R.drawable.ic_settings, R.string.nav_settings, false,
                v -> startActivity(new Intent(this, SettingsActivity.class)));
    }

    private void bindNavItem(int rootId,
                             @DrawableRes int iconRes,
                             @StringRes int labelRes,
                             boolean selected,
                             @Nullable View.OnClickListener listener) {
        View root = findViewById(rootId);
        ImageView icon = root.findViewById(R.id.nav_icon);
        TextView label = root.findViewById(R.id.nav_label);

        icon.setImageResource(iconRes);
        label.setText(labelRes);

        int tint = ContextCompat.getColor(this,
                selected ? R.color.text_primary : R.color.text_secondary);
        icon.setImageTintList(android.content.res.ColorStateList.valueOf(tint));
        label.setTextColor(tint);
        root.setBackgroundResource(selected ? R.drawable.bg_nav_selected : 0);

        if (listener != null) {
            root.setOnClickListener(listener);
        }
    }

    private void bindTiles() {
        bindTile(R.id.tile_image, R.drawable.bg_tile_red, R.drawable.ic_camera,
                R.string.home_image_ocr, R.string.home_image_ocr_sub,
                v -> startActivity(new Intent(this, CameraActivity.class)));

        bindTile(R.id.tile_pdf, R.drawable.bg_tile_blue, R.drawable.ic_pdf,
                R.string.home_pdf_ocr, R.string.home_pdf_ocr_sub,
                v -> startActivity(new Intent(this, PdfActivity.class)));

        bindTile(R.id.tile_sequence, R.drawable.bg_tile_green, R.drawable.ic_image,
                R.string.home_sequence, R.string.home_sequence_sub,
                v -> startActivity(new Intent(this, ImageImportActivity.class)));

        bindTile(R.id.tile_history, R.drawable.bg_tile_orange, R.drawable.ic_history,
                R.string.home_history, R.string.home_history_sub,
                v -> startActivity(new Intent(this, HistoryActivity.class)));
    }

    private void bindTile(int rootId,
                          @DrawableRes int backgroundRes,
                          @DrawableRes int iconRes,
                          @StringRes int titleRes,
                          @StringRes int subtitleRes,
                          @NonNull View.OnClickListener listener) {
        View root = findViewById(rootId);
        root.setBackgroundResource(backgroundRes);
        ((ImageView) root.findViewById(R.id.tile_icon)).setImageResource(iconRes);
        ((TextView) root.findViewById(R.id.tile_title)).setText(titleRes);
        ((TextView) root.findViewById(R.id.tile_subtitle)).setText(subtitleRes);
        root.setOnClickListener(listener);
    }

    /**
     * Surfaces a missing model tree on the home screen.
     *
     * <p>Without this the first symptom is a failure several taps deep, after
     * the user has already framed a photo — far better to say so up front.
     */
    private void showModelWarningIfNeeded() {
        TextView warning = findViewById(R.id.main_model_warning);
        runInBackground(() -> engines().models(), new Callback<ModelValidator.Report>() {
            @Override
            public void onSuccess(ModelValidator.Report report) {
                if (report.canRunOcr() && report.isComplete()) {
                    warning.setVisibility(View.GONE);
                    return;
                }
                warning.setVisibility(View.VISIBLE);
                warning.setText(getString(R.string.error_models_missing)
                        + "\n" + getString(R.string.error_models_missing_hint));
                warning.setOnClickListener(v -> startActivity(new Intent(
                        MainActivity.this, SettingsActivity.class)));
            }

            @Override
            public void onError(@NonNull Exception error) {
                warning.setVisibility(View.VISIBLE);
                warning.setText(error.getMessage());
            }
        });
    }
}
