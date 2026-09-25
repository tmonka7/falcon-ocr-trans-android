package com.falcon.ocrtrans.ui;

import android.view.View;
import android.widget.ImageButton;
import android.widget.TextView;

import androidx.annotation.DrawableRes;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.annotation.StringRes;
import androidx.appcompat.app.AppCompatActivity;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.engine.Engines;

/** Toolbar wiring and the blocking progress overlay, shared by every screen. */
public abstract class BaseActivity extends AppCompatActivity {

    @Nullable
    private View busyRoot;
    @Nullable
    private TextView busyMessage;
    @Nullable
    private TextView busyDetail;

    @NonNull
    protected Engines engines() {
        return Engines.get(this);
    }

    /** Binds the included toolbar: sets the title and makes back finish. */
    protected void setupToolbar(@StringRes int titleRes) {
        TextView title = findViewById(R.id.toolbar_title);
        if (title != null) {
            title.setText(titleRes);
        }
        ImageButton back = findViewById(R.id.toolbar_back);
        if (back != null) {
            back.setOnClickListener(v -> finish());
        }
    }

    /** Reveals the toolbar's trailing action button. */
    protected void setToolbarAction(@DrawableRes int iconRes,
                                    @StringRes int descriptionRes,
                                    @NonNull View.OnClickListener listener) {
        ImageButton action = findViewById(R.id.toolbar_action);
        if (action == null) {
            return;
        }
        action.setImageResource(iconRes);
        action.setContentDescription(getString(descriptionRes));
        action.setVisibility(View.VISIBLE);
        action.setOnClickListener(listener);
    }

    /**
     * Binds the {@code view_busy} overlay.
     *
     * @param rootId the id given to the {@code <include>} in the layout
     */
    protected void bindBusyOverlay(int rootId) {
        busyRoot = findViewById(rootId);
        if (busyRoot != null) {
            busyMessage = busyRoot.findViewById(R.id.busy_message);
            busyDetail = busyRoot.findViewById(R.id.busy_detail);
        }
    }

    protected void showBusy(@StringRes int messageRes) {
        showBusy(getString(messageRes), null);
    }

    /**
     * @param detail a secondary line such as page progress, or {@code null}
     */
    protected void showBusy(@NonNull CharSequence message, @Nullable CharSequence detail) {
        if (busyRoot == null) {
            return;
        }
        if (busyMessage != null) {
            busyMessage.setText(message);
        }
        if (busyDetail != null) {
            busyDetail.setText(detail == null ? "" : detail);
            busyDetail.setVisibility(detail == null ? View.GONE : View.VISIBLE);
        }
        busyRoot.setVisibility(View.VISIBLE);
    }

    /** Updates only the detail line, without re-showing the overlay. */
    protected void updateBusyDetail(@Nullable CharSequence detail) {
        if (busyDetail == null) {
            return;
        }
        busyDetail.setText(detail == null ? "" : detail);
        busyDetail.setVisibility(detail == null ? View.GONE : View.VISIBLE);
    }

    protected void hideBusy() {
        if (busyRoot != null) {
            busyRoot.setVisibility(View.GONE);
        }
    }

    protected boolean isBusyShowing() {
        return busyRoot != null && busyRoot.getVisibility() == View.VISIBLE;
    }

    /**
     * Runs {@code work} on the shared engine thread and delivers the outcome on
     * the UI thread — but only if this activity is still alive, so a slow job
     * cannot touch views belonging to a destroyed screen.
     */
    protected <T> void runInBackground(@NonNull BackgroundWork<T> work,
                                       @NonNull Callback<T> callback) {
        engines().worker().execute(() -> {
            T value = null;
            Exception failure = null;
            try {
                value = work.run();
            } catch (Exception e) {
                failure = e;
            }
            final T result = value;
            final Exception error = failure;
            engines().postToMain(() -> {
                if (isFinishing() || isDestroyed()) {
                    return;
                }
                if (error != null) {
                    callback.onError(error);
                } else {
                    callback.onSuccess(result);
                }
            });
        });
    }

    /** Work that runs off the main thread and may fail. */
    public interface BackgroundWork<T> {
        T run() throws Exception;
    }

    /** Delivered on the main thread. */
    public interface Callback<T> {
        void onSuccess(T result);

        void onError(@NonNull Exception error);
    }
}
