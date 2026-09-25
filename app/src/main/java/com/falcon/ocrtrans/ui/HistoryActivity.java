package com.falcon.ocrtrans.ui;

import android.app.AlertDialog;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.data.HistoryItem;
import com.falcon.ocrtrans.data.HistoryStore;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/** Lists saved translations; tapping one reopens its text. */
public final class HistoryActivity extends BaseActivity {

    private static final int PAGE_SIZE = 200;

    private final List<HistoryItem> items = new ArrayList<>();
    private final SimpleDateFormat timestampFormat =
            new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US);

    private HistoryStore store;
    private Adapter adapter;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_history);
        setupToolbar(R.string.title_history);
        setToolbarAction(R.drawable.ic_delete, R.string.history_clear, v -> confirmClear());

        store = new HistoryStore(this);

        RecyclerView list = findViewById(R.id.history_list);
        list.setLayoutManager(new LinearLayoutManager(this));
        adapter = new Adapter();
        list.setAdapter(adapter);
    }

    @Override
    protected void onResume() {
        super.onResume();
        reload();
    }

    private void reload() {
        runInBackground(() -> store.recent(PAGE_SIZE), new Callback<List<HistoryItem>>() {
            @Override
            public void onSuccess(List<HistoryItem> loaded) {
                items.clear();
                items.addAll(loaded);
                adapter.notifyDataSetChanged();

                boolean empty = items.isEmpty();
                findViewById(R.id.history_empty).setVisibility(empty ? View.VISIBLE : View.GONE);
                findViewById(R.id.history_list).setVisibility(empty ? View.GONE : View.VISIBLE);
            }

            @Override
            public void onError(@NonNull Exception error) {
                Toast.makeText(HistoryActivity.this, R.string.error_generic,
                        Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void confirmClear() {
        if (items.isEmpty()) {
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle(R.string.history_clear)
                .setMessage(R.string.history_clear_confirm)
                .setNegativeButton(R.string.action_cancel, null)
                .setPositiveButton(R.string.action_delete, (dialog, which) -> clearAll())
                .show();
    }

    private void clearAll() {
        runInBackground(() -> {
            store.clear();
            return null;
        }, new Callback<Void>() {
            @Override
            public void onSuccess(Void ignored) {
                Toast.makeText(HistoryActivity.this, R.string.history_cleared,
                        Toast.LENGTH_SHORT).show();
                reload();
            }

            @Override
            public void onError(@NonNull Exception error) {
                Toast.makeText(HistoryActivity.this, R.string.error_generic,
                        Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void confirmDelete(@NonNull HistoryItem item) {
        new AlertDialog.Builder(this)
                .setTitle(item.title())
                .setNegativeButton(R.string.action_cancel, null)
                .setPositiveButton(R.string.action_delete, (dialog, which) ->
                        runInBackground(() -> {
                            store.delete(item.id);
                            return null;
                        }, new Callback<Void>() {
                            @Override
                            public void onSuccess(Void ignored) {
                                reload();
                            }

                            @Override
                            public void onError(@NonNull Exception error) {
                                Toast.makeText(HistoryActivity.this, R.string.error_generic,
                                        Toast.LENGTH_SHORT).show();
                            }
                        }))
                .show();
    }

    private void showDetail(@NonNull HistoryItem item) {
        new AlertDialog.Builder(this)
                .setTitle(item.directionLabel())
                .setMessage(item.sourceText + "\n\n—\n\n" + item.translatedText)
                .setPositiveButton(R.string.action_ok, null)
                .show();
    }

    private static int iconFor(HistoryItem.Kind kind) {
        switch (kind) {
            case PDF:
                return R.drawable.ic_pdf;
            case CAMERA:
                return R.drawable.ic_camera;
            case MANUAL:
                return R.drawable.ic_translate;
            case IMAGE:
            default:
                return R.drawable.ic_image;
        }
    }

    @Override
    protected void onDestroy() {
        store.close();
        super.onDestroy();
    }

    private final class Adapter extends RecyclerView.Adapter<Adapter.Holder> {

        @NonNull
        @Override
        public Holder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            return new Holder(LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_history, parent, false));
        }

        @Override
        public void onBindViewHolder(@NonNull Holder holder, int position) {
            holder.bind(items.get(position));
        }

        @Override
        public int getItemCount() {
            return items.size();
        }

        final class Holder extends RecyclerView.ViewHolder {
            private final ImageView icon;
            private final TextView title;
            private final TextView direction;
            private final TextView timestamp;

            Holder(@NonNull View itemView) {
                super(itemView);
                icon = itemView.findViewById(R.id.history_icon);
                title = itemView.findViewById(R.id.history_title);
                direction = itemView.findViewById(R.id.history_direction);
                timestamp = itemView.findViewById(R.id.history_timestamp);
            }

            void bind(HistoryItem item) {
                icon.setImageResource(iconFor(item.kind));
                title.setText(item.title());
                direction.setText(item.directionLabel());
                timestamp.setText(timestampFormat.format(new Date(item.createdAt)));

                itemView.setOnClickListener(v -> showDetail(item));
                itemView.setOnLongClickListener(v -> {
                    confirmDelete(item);
                    return true;
                });
            }
        }
    }
}
