package com.falcon.ocrtrans.ui;

import android.graphics.Bitmap;
import android.net.Uri;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.util.ImageLoader;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Picks one or more images and runs them through the pipeline.
 *
 * <p>With several selected, each is processed in turn and only the last is shown
 * on the result screen — the earlier ones are saved to history, which is what
 * makes batch mode worth having over repeating a single-image flow.
 */
public final class ImageImportActivity extends ProcessingActivity {

    private final List<Uri> available = new ArrayList<>();
    private final Set<Uri> selected = new LinkedHashSet<>();

    private Adapter adapter;
    private TextView countLabel;
    private ActivityResultLauncher<String> pickLauncher;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_image_import);
        setupToolbar(R.string.title_image_import);
        bindBusyOverlay(R.id.import_busy);

        countLabel = findViewById(R.id.import_count);

        RecyclerView grid = findViewById(R.id.import_grid);
        grid.setLayoutManager(new GridLayoutManager(this, 3));
        adapter = new Adapter();
        grid.setAdapter(adapter);

        pickLauncher = registerForActivityResult(
                new ActivityResultContracts.GetMultipleContents(), uris -> {
                    if (uris == null || uris.isEmpty()) {
                        return;
                    }
                    for (Uri uri : uris) {
                        if (!available.contains(uri)) {
                            available.add(uri);
                        }
                        selected.add(uri);
                    }
                    adapter.notifyDataSetChanged();
                    updateCount();
                });

        findViewById(R.id.import_add).setOnClickListener(v -> pickLauncher.launch("image/*"));
        findViewById(R.id.import_next).setOnClickListener(v -> processSelection());

        updateCount();
        // Open the picker straight away: an empty grid is not a useful first view.
        pickLauncher.launch("image/*");
    }

    private void updateCount() {
        int n = selected.size();
        countLabel.setText(getResources().getQuantityString(R.plurals.import_selected, n, n));
        findViewById(R.id.import_empty)
                .setVisibility(available.isEmpty() ? View.VISIBLE : View.GONE);
        findViewById(R.id.import_grid)
                .setVisibility(available.isEmpty() ? View.GONE : View.VISIBLE);
    }

    private void processSelection() {
        if (selected.isEmpty()) {
            Toast.makeText(this, R.string.import_none_selected, Toast.LENGTH_SHORT).show();
            return;
        }
        List<Uri> queue = new ArrayList<>(selected);
        if (queue.size() == 1) {
            processUri(queue.get(0));
            return;
        }
        processBatch(queue);
    }

    /**
     * Runs every selected image, saving each to history, then opens the last.
     *
     * <p>Progress is reported per image because a batch of ten pages is a
     * multi-minute job, and an overlay with no counter reads as a hang.
     */
    private void processBatch(@NonNull List<Uri> queue) {
        showBusy(getString(R.string.working), getString(R.string.pdf_progress, 1, queue.size()));

        runInBackground(() -> {
            com.falcon.ocrtrans.data.Prefs prefs = new com.falcon.ocrtrans.data.Prefs(this);
            com.falcon.ocrtrans.data.HistoryStore store =
                    new com.falcon.ocrtrans.data.HistoryStore(this);
            com.falcon.ocrtrans.engine.ResultHolder.Payload last = null;
            try {
                for (int i = 0; i < queue.size(); i++) {
                    final int index = i + 1;
                    engines().postToMain(() -> updateBusyDetail(
                            getString(R.string.pdf_progress, index, queue.size())));

                    Bitmap bitmap = ImageLoader.load(this, queue.get(i));
                    com.falcon.ocrtrans.engine.TranslationPipeline.Options options =
                            new com.falcon.ocrtrans.engine.TranslationPipeline.Options();
                    options.translate = prefs.autoTranslate();
                    options.autoDetectSource = prefs.autoDetectScript();

                    com.falcon.ocrtrans.engine.TranslationPipeline.Result result =
                            engines().pipeline().process(
                                    bitmap, prefs.sourceLang(), prefs.targetLang(), options);

                    Bitmap toSave = result.rendered != null ? result.rendered : bitmap;
                    String path = ImageLoader.saveToAppStorage(this, toSave, "batch");
                    store.insert(com.falcon.ocrtrans.data.HistoryItem.Kind.IMAGE,
                            result.detectedSource, prefs.targetLang(),
                            result.ocr.plainText(), result.ocr.translatedText(), path);

                    last = new com.falcon.ocrtrans.engine.ResultHolder.Payload(
                            bitmap, result.rendered, result,
                            result.detectedSource, prefs.targetLang());
                }
            } finally {
                store.close();
            }
            return last;
        }, new Callback<com.falcon.ocrtrans.engine.ResultHolder.Payload>() {
            @Override
            public void onSuccess(com.falcon.ocrtrans.engine.ResultHolder.Payload payload) {
                hideBusy();
                if (payload == null) {
                    return;
                }
                com.falcon.ocrtrans.engine.ResultHolder.put(payload);
                startActivity(new android.content.Intent(
                        ImageImportActivity.this, ResultActivity.class));
            }

            @Override
            public void onError(@NonNull Exception error) {
                hideBusy();
                String message = error.getMessage();
                Toast.makeText(ImageImportActivity.this,
                        message != null ? message : getString(R.string.error_generic),
                        Toast.LENGTH_LONG).show();
            }
        });
    }

    private final class Adapter extends RecyclerView.Adapter<Adapter.Holder> {

        @NonNull
        @Override
        public Holder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            return new Holder(LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_import_image, parent, false));
        }

        @Override
        public void onBindViewHolder(@NonNull Holder holder, int position) {
            holder.bind(available.get(position));
        }

        @Override
        public int getItemCount() {
            return available.size();
        }

        final class Holder extends RecyclerView.ViewHolder {
            private final ImageView thumb;
            private final View frame;
            private final View check;

            Holder(@NonNull View itemView) {
                super(itemView);
                thumb = itemView.findViewById(R.id.import_thumb);
                frame = itemView.findViewById(R.id.import_selection_frame);
                check = itemView.findViewById(R.id.import_check);
            }

            void bind(Uri uri) {
                // Thumbnails decode on the UI thread only because they are
                // heavily subsampled; a full decode here would drop frames.
                thumb.setImageURI(null);
                thumb.setImageURI(uri);

                boolean isSelected = selected.contains(uri);
                frame.setVisibility(isSelected ? View.VISIBLE : View.GONE);
                check.setVisibility(isSelected ? View.VISIBLE : View.GONE);

                itemView.setOnClickListener(v -> {
                    if (selected.contains(uri)) {
                        selected.remove(uri);
                    } else {
                        selected.add(uri);
                    }
                    notifyItemChanged(getBindingAdapterPosition());
                    updateCount();
                });
            }
        }
    }
}
