package com.falcon.ocrtrans.ui;

import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.animation.ValueAnimator;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.animation.DecelerateInterpolator;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.activity.OnBackPressedCallback;
import androidx.annotation.DrawableRes;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.annotation.StringRes;
import androidx.core.content.ContextCompat;
import androidx.core.view.ViewCompat;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.data.Prefs;
import com.falcon.ocrtrans.engine.ModelValidator;

/** Home: the action tiles, the language pair, and the collapsible side menu. */
public final class MainActivity extends BaseActivity {

    /** Side-menu width animation length; the system animator scale still applies. */
    private static final long NAV_ANIMATION_MS = 220;

    private static final int[] NAV_ITEM_IDS = {
            R.id.nav_home, R.id.nav_image, R.id.nav_pdf, R.id.nav_history, R.id.nav_settings,
    };

    private Prefs prefs;
    private LanguageBar languageBar;

    private View navRail;
    private View navScrim;
    private ImageButton navToggle;
    private boolean navExpanded;
    private OnBackPressedCallback navBackCallback;
    @Nullable
    private ValueAnimator navAnimator;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = new Prefs(this);

        bindNavRail();
        bindNavToggle();
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

    // ----------------------------------------------------------- side menu

    /**
     * Wires the right-hand title-bar button that expands and collapses the side
     * menu.
     *
     * <p>Collapsed, the menu is a narrow rail of icons that the content always
     * leaves room for. Expanded, it widens over the content, adds a label to each
     * icon and dims the rest of the screen; tapping the dimmed area or pressing
     * Back collapses it again. It overlays rather than pushes because pushing
     * would squeeze the home tiles to a sliver on a phone. For the same reason
     * the menu always starts collapsed instead of restoring its last state.
     */
    private void bindNavToggle() {
        navRail = findViewById(R.id.nav_rail);
        navScrim = findViewById(R.id.nav_scrim);
        navToggle = findViewById(R.id.main_nav_toggle);

        navBackCallback = new OnBackPressedCallback(false) {
            @Override
            public void handleOnBackPressed() {
                setNavExpanded(false);
            }
        };
        getOnBackPressedDispatcher().addCallback(this, navBackCallback);

        navToggle.setOnClickListener(v -> setNavExpanded(!navExpanded));
        navScrim.setOnClickListener(v -> setNavExpanded(false));
        applyNavState(false);
    }

    private void setNavExpanded(boolean expanded) {
        if (expanded == navExpanded) {
            return;
        }
        navExpanded = expanded;
        applyNavState(true);
    }

    private void applyNavState(boolean animate) {
        int collapsed = getResources().getDimensionPixelSize(R.dimen.nav_rail_width);
        int expanded = getResources().getDimensionPixelSize(R.dimen.nav_rail_expanded_width);
        int target = navExpanded ? expanded : collapsed;

        navBackCallback.setEnabled(navExpanded);
        navToggle.setImageResource(navExpanded ? R.drawable.ic_menu_open : R.drawable.ic_menu);
        navToggle.setContentDescription(getString(
                navExpanded ? R.string.nav_collapse : R.string.nav_expand));

        for (int id : NAV_ITEM_IDS) {
            View root = findViewById(id);
            TextView label = root.findViewById(R.id.nav_label);
            // With labels hidden the icon alone must still say where it goes.
            ViewCompat.setTooltipText(root, navExpanded ? null : label.getText());
            root.setContentDescription(label.getText());
        }

        if (navAnimator != null) {
            navAnimator.cancel();
            navAnimator = null;
        }
        if (!animate) {
            setNavWidth(target);
            setNavLabelsVisible(navExpanded, 1f);
            navScrim.setVisibility(navExpanded ? View.VISIBLE : View.GONE);
            navScrim.setAlpha(1f);
            return;
        }

        // Labels appear once there is room for them and leave before the rail
        // narrows, so they are never squeezed into an ellipsis mid-animation.
        if (!navExpanded) {
            setNavLabelsVisible(false, 1f);
        }
        navScrim.setVisibility(View.VISIBLE);
        int start = navRail.getWidth() > 0 ? navRail.getWidth() : (navExpanded ? collapsed : expanded);
        ValueAnimator animator = ValueAnimator.ofInt(start, target);
        animator.setDuration(NAV_ANIMATION_MS);
        animator.setInterpolator(new DecelerateInterpolator());
        animator.addUpdateListener(a -> {
            int width = (int) a.getAnimatedValue();
            setNavWidth(width);
            float progress = (float) (width - collapsed) / Math.max(1, expanded - collapsed);
            navScrim.setAlpha(Math.max(0f, Math.min(1f, progress)));
            if (navExpanded) {
                setNavLabelsVisible(progress > 0.6f, Math.max(0f, (progress - 0.6f) / 0.4f));
            }
        });
        animator.addListener(new AnimatorListenerAdapter() {
            @Override
            public void onAnimationEnd(Animator animation) {
                if (!navExpanded) {
                    navScrim.setVisibility(View.GONE);
                }
            }
        });
        navAnimator = animator;
        animator.start();
    }

    private void setNavWidth(int width) {
        ViewGroup.LayoutParams lp = navRail.getLayoutParams();
        lp.width = width;
        navRail.setLayoutParams(lp);
    }

    private void setNavLabelsVisible(boolean visible, float alpha) {
        for (int id : NAV_ITEM_IDS) {
            TextView label = findViewById(id).findViewById(R.id.nav_label);
            label.setVisibility(visible ? View.VISIBLE : View.GONE);
            label.setAlpha(alpha);
        }
    }

    @Override
    protected void onDestroy() {
        if (navAnimator != null) {
            navAnimator.cancel();
        }
        super.onDestroy();
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
