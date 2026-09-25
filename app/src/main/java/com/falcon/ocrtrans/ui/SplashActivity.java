package com.falcon.ocrtrans.ui;

import android.content.Intent;
import android.os.Bundle;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.engine.ModelValidator;

/**
 * Launch screen. Scans the bundled model tree while the brand mark is up, so the
 * first real screen already knows what the install can do.
 */
public final class SplashActivity extends BaseActivity {

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_splash);

        TextView status = findViewById(R.id.splash_status);

        // The scan stats a few hundred asset entries. That is fast, but doing it
        // here rather than on first use keeps it off the path of a user who has
        // just framed a photo and is waiting on a result.
        runInBackground(() -> engines().models(), new Callback<ModelValidator.Report>() {
            @Override
            public void onSuccess(ModelValidator.Report report) {
                status.setText(report.canRunOcr()
                        ? getString(R.string.app_tagline)
                        : getString(R.string.error_models_missing));
                proceed();
            }

            @Override
            public void onError(@NonNull Exception error) {
                // Home surfaces the problem properly; never strand the user here.
                status.setText(R.string.error_generic);
                proceed();
            }
        });
    }

    private void proceed() {
        startActivity(new Intent(this, MainActivity.class));
        finish();
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out);
    }
}
