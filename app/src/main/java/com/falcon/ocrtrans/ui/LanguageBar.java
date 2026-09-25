package com.falcon.ocrtrans.ui;

import android.app.Activity;
import android.view.View;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.data.Prefs;

/**
 * Drives the source/swap/target strip included by several screens.
 *
 * <p>The strip appears on Home, PDF and manual Translation, all reading the same
 * stored pair — so the behaviour lives here once rather than three times.
 */
public final class LanguageBar {

    /** Notified after the stored pair changes, so the host can re-render. */
    public interface Listener {
        void onLanguagesChanged(@NonNull Lang source, @NonNull Lang target);
    }

    private final Prefs prefs;
    private final TextView sourceFlag;
    private final TextView sourceName;
    private final TextView targetFlag;
    private final TextView targetName;

    @Nullable
    private Listener listener;

    /**
     * @param root the {@code view_language_bar} include
     * @param onPick invoked with the side to edit when a selector is tapped
     */
    public LanguageBar(@NonNull Activity activity,
                       @NonNull View root,
                       @NonNull Prefs prefs,
                       @NonNull PickListener onPick) {
        this.prefs = prefs;
        this.sourceFlag = root.findViewById(R.id.language_source_flag);
        this.sourceName = root.findViewById(R.id.language_source_name);
        this.targetFlag = root.findViewById(R.id.language_target_flag);
        this.targetName = root.findViewById(R.id.language_target_name);

        root.findViewById(R.id.language_source)
                .setOnClickListener(v -> onPick.onPick(LanguageActivity.Side.SOURCE));
        root.findViewById(R.id.language_target)
                .setOnClickListener(v -> onPick.onPick(LanguageActivity.Side.TARGET));
        root.findViewById(R.id.language_swap).setOnClickListener(v -> {
            prefs.swapLanguages();
            refresh();
        });

        refresh();
    }

    /** Tapping one of the two language chips. */
    public interface PickListener {
        void onPick(@NonNull LanguageActivity.Side side);
    }

    public void setListener(@Nullable Listener listener) {
        this.listener = listener;
    }

    /** Re-reads the stored pair. Call from {@code onResume}. */
    public void refresh() {
        Lang source = prefs.sourceLang();
        Lang target = prefs.targetLang();

        sourceFlag.setText(Flags.of(source));
        sourceName.setText(source.englishName());
        targetFlag.setText(Flags.of(target));
        targetName.setText(target.englishName());

        if (listener != null) {
            listener.onLanguagesChanged(source, target);
        }
    }
}
