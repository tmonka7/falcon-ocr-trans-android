package com.falcon.ocrtrans.ui;

import android.app.AlertDialog;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.OpenableColumns;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.data.HistoryItem;
import com.falcon.ocrtrans.data.HistoryStore;
import com.falcon.ocrtrans.data.Prefs;
import com.falcon.ocrtrans.pdf.PdfJob;

import java.util.Locale;

/** Chooses a PDF, its page range and output format, then runs the whole file. */
public final class PdfActivity extends BaseActivity {

    private Prefs prefs;
    private LanguageBar languageBar;

    @Nullable
    private Uri document;
    private int firstPage = 1;
    private int lastPage = 0; // 0 means "to the end"
    private volatile boolean cancelled;

    private OptionRow rangeRow;
    private OptionRow formatRow;
    private ActivityResultLauncher<String[]> pickLauncher;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_pdf);
        setupToolbar(R.string.title_pdf);
        bindBusyOverlay(R.id.pdf_busy);

        prefs = new Prefs(this);

        pickLauncher = registerForActivityResult(
                new ActivityResultContracts.OpenDocument(), uri -> {
                    if (uri != null) {
                        onDocumentPicked(uri);
                    }
                });

        rangeRow = new OptionRow(findViewById(R.id.pdf_row_range))
                .label(R.string.pdf_page_range)
                .value(R.string.pdf_all_pages)
                .onClick(v -> promptForRange());

        formatRow = new OptionRow(findViewById(R.id.pdf_row_format))
                .label(R.string.pdf_output_format)
                .value(prefs.pdfOutput().name())
                .onClick(v -> promptForFormat());

        languageBar = new LanguageBar(this, findViewById(R.id.pdf_language_bar), prefs,
                side -> startActivity(LanguageActivity.intent(this, side)));

        findViewById(R.id.pdf_file_card).setOnClickListener(v -> openPicker());
        findViewById(R.id.pdf_file_clear).setOnClickListener(v -> clearDocument());
        findViewById(R.id.pdf_start).setOnClickListener(v -> start());
    }

    @Override
    protected void onResume() {
        super.onResume();
        languageBar.refresh();
    }

    private void openPicker() {
        pickLauncher.launch(new String[]{"application/pdf"});
    }

    private void onDocumentPicked(@NonNull Uri uri) {
        // Without this the URI stops resolving as soon as the process restarts,
        // which turns a long job into a mystery failure part-way through.
        try {
            getContentResolver().takePersistableUriPermission(
                    uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } catch (SecurityException ignored) {
            // Not all providers grant persistable access; the session grant holds.
        }
        document = uri;
        ((TextView) findViewById(R.id.pdf_file_name)).setText(displayName(uri));
        findViewById(R.id.pdf_file_clear).setVisibility(View.VISIBLE);

        TextView meta = findViewById(R.id.pdf_file_meta);
        meta.setVisibility(View.VISIBLE);
        meta.setText(R.string.working);

        // Opening the document is the only way to learn its page count.
        runInBackground(() -> {
            try (com.falcon.ocrtrans.pdf.PdfPageSource source =
                         new com.falcon.ocrtrans.pdf.PdfPageSource(this, uri)) {
                return source.pageCount();
            }
        }, new Callback<Integer>() {
            @Override
            public void onSuccess(Integer pages) {
                meta.setText(getString(R.string.pdf_pages_count, formatSize(uri), pages));
            }

            @Override
            public void onError(@NonNull Exception error) {
                meta.setText(error.getMessage() != null
                        ? error.getMessage() : getString(R.string.error_generic));
            }
        });
    }

    private void clearDocument() {
        document = null;
        firstPage = 1;
        lastPage = 0;
        ((TextView) findViewById(R.id.pdf_file_name)).setText(R.string.pdf_choose);
        findViewById(R.id.pdf_file_meta).setVisibility(View.GONE);
        findViewById(R.id.pdf_file_clear).setVisibility(View.GONE);
        rangeRow.value(getString(R.string.pdf_all_pages));
    }

    private void promptForRange() {
        final String[] options = {getString(R.string.pdf_all_pages), "1-5", "1-10", "1-20"};
        new AlertDialog.Builder(this)
                .setTitle(R.string.pdf_page_range)
                .setItems(options, (dialog, which) -> {
                    if (which == 0) {
                        firstPage = 1;
                        lastPage = 0;
                    } else {
                        firstPage = 1;
                        lastPage = Integer.parseInt(options[which].split("-")[1]);
                    }
                    rangeRow.value(options[which]);
                })
                .show();
    }

    private void promptForFormat() {
        final Prefs.PdfOutput[] values = Prefs.PdfOutput.values();
        final String[] labels = new String[values.length];
        for (int i = 0; i < values.length; i++) {
            labels[i] = values[i].name();
        }
        new AlertDialog.Builder(this)
                .setTitle(R.string.pdf_output_format)
                .setItems(labels, (dialog, which) -> {
                    prefs.setPdfOutput(values[which]);
                    formatRow.value(labels[which]);
                })
                .show();
    }

    private void start() {
        final Uri uri = document;
        if (uri == null) {
            Toast.makeText(this, R.string.pdf_choose, Toast.LENGTH_SHORT).show();
            openPicker();
            return;
        }

        cancelled = false;
        showBusy(getString(R.string.working), null);

        final com.falcon.ocrtrans.core.Lang source = prefs.sourceLang();
        final com.falcon.ocrtrans.core.Lang target = prefs.targetLang();
        final Prefs.PdfOutput format = prefs.pdfOutput();

        runInBackground(() -> {
            PdfJob job = new PdfJob(this, engines().pipeline());
            PdfJob.Output output = job.run(uri, source, target, format,
                    firstPage, lastPage, new PdfJob.Listener() {
                        @Override
                        public void onPageStarted(int page, int total) {
                            engines().postToMain(() -> updateBusyDetail(
                                    getString(R.string.pdf_progress, page, total)));
                        }

                        @Override
                        public void onPageFinished(int page, int total, @NonNull String text) {
                        }

                        @Override
                        public boolean isCancelled() {
                            return cancelled;
                        }
                    });

            HistoryStore store = new HistoryStore(this);
            try {
                store.insert(HistoryItem.Kind.PDF, source, target,
                        output.combinedText, output.combinedText, null);
            } finally {
                store.close();
            }
            return output;
        }, new Callback<PdfJob.Output>() {
            @Override
            public void onSuccess(PdfJob.Output output) {
                hideBusy();
                TextView result = findViewById(R.id.pdf_result);
                result.setVisibility(View.VISIBLE);
                result.setText(getString(R.string.pdf_done, output.file.getAbsolutePath())
                        + "\n\n" + output.combinedText);
            }

            @Override
            public void onError(@NonNull Exception error) {
                hideBusy();
                String message = error.getMessage();
                Toast.makeText(PdfActivity.this,
                        message != null ? message : getString(R.string.error_generic),
                        Toast.LENGTH_LONG).show();
            }
        });
    }

    @Override
    public void onBackPressed() {
        if (isBusyShowing()) {
            // Signal the job rather than tearing the activity down underneath it.
            cancelled = true;
            hideBusy();
            return;
        }
        super.onBackPressed();
    }

    @NonNull
    private String displayName(@NonNull Uri uri) {
        try (Cursor c = getContentResolver().query(uri, null, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                int index = c.getColumnIndex(OpenableColumns.DISPLAY_NAME);
                if (index >= 0) {
                    String name = c.getString(index);
                    if (name != null) {
                        return name;
                    }
                }
            }
        } catch (RuntimeException ignored) {
            // Provider refused the query; the path fallback below is fine.
        }
        String path = uri.getLastPathSegment();
        return path != null ? path : getString(R.string.pdf_choose);
    }

    @NonNull
    private String formatSize(@NonNull Uri uri) {
        try (Cursor c = getContentResolver().query(uri, null, null, null, null)) {
            if (c != null && c.moveToFirst()) {
                int index = c.getColumnIndex(OpenableColumns.SIZE);
                if (index >= 0 && !c.isNull(index)) {
                    long bytes = c.getLong(index);
                    return String.format(Locale.US, "%.1f MB", bytes / (1024.0 * 1024.0));
                }
            }
        } catch (RuntimeException ignored) {
            // Size is decorative here.
        }
        return "PDF";
    }
}
