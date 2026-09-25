package com.falcon.ocrtrans.ui;

import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.annotation.DrawableRes;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.annotation.StringRes;

import com.falcon.ocrtrans.R;
import com.google.android.material.materialswitch.MaterialSwitch;

/** Binds one {@code item_option_row} include: label, value, chevron or switch. */
public final class OptionRow {

    private final View root;
    private final ImageView icon;
    private final TextView label;
    private final TextView value;
    private final MaterialSwitch toggle;
    private final ImageView chevron;

    public OptionRow(@NonNull View root) {
        this.root = root;
        this.icon = root.findViewById(R.id.option_icon);
        this.label = root.findViewById(R.id.option_label);
        this.value = root.findViewById(R.id.option_value);
        this.toggle = root.findViewById(R.id.option_switch);
        this.chevron = root.findViewById(R.id.option_chevron);
    }

    public OptionRow icon(@DrawableRes int iconRes) {
        icon.setImageResource(iconRes);
        icon.setVisibility(View.VISIBLE);
        return this;
    }

    public OptionRow label(@StringRes int labelRes) {
        label.setText(labelRes);
        return this;
    }

    public OptionRow value(@Nullable CharSequence text) {
        value.setText(text == null ? "" : text);
        value.setVisibility(text == null ? View.GONE : View.VISIBLE);
        return this;
    }

    public OptionRow value(@StringRes int valueRes) {
        value.setText(valueRes);
        value.setVisibility(View.VISIBLE);
        return this;
    }

    /** Turns the row into a toggle: the switch replaces the chevron. */
    public OptionRow asSwitch(boolean checked, @NonNull OnToggle onToggle) {
        chevron.setVisibility(View.GONE);
        value.setVisibility(View.GONE);
        toggle.setVisibility(View.VISIBLE);
        toggle.setChecked(checked);

        // Route taps on the row into the switch so the whole row is the target,
        // and drive the callback from the switch alone to avoid a double fire.
        toggle.setOnCheckedChangeListener((button, isChecked) -> onToggle.onToggle(isChecked));
        root.setOnClickListener(v -> toggle.toggle());
        return this;
    }

    public OptionRow onClick(@NonNull View.OnClickListener listener) {
        root.setOnClickListener(listener);
        return this;
    }

    public void setEnabled(boolean enabled) {
        root.setEnabled(enabled);
        root.setAlpha(enabled ? 1f : 0.5f);
    }

    /** Switch state changed. */
    public interface OnToggle {
        void onToggle(boolean checked);
    }
}
