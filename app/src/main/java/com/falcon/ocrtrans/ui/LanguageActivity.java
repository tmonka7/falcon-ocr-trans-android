package com.falcon.ocrtrans.ui;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.data.Prefs;
import com.falcon.ocrtrans.engine.ModelValidator;
import com.google.android.material.tabs.TabLayout;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Picks the source and target language.
 *
 * <p>Each row reports what the installed models can actually do for that choice:
 * a pair with no direct model is flagged as going through English, and one with
 * no route at all is shown as unavailable rather than silently failing later.
 */
public final class LanguageActivity extends BaseActivity {

    /** Which half of the pair the screen opened on. */
    public enum Side {SOURCE, TARGET}

    private static final String EXTRA_SIDE = "side";

    private Prefs prefs;
    private ModelValidator.Report report;
    private Adapter adapter;
    private Side side = Side.SOURCE;
    private String query = "";

    public static Intent intent(@NonNull Context context, @NonNull Side side) {
        return new Intent(context, LanguageActivity.class).putExtra(EXTRA_SIDE, side.name());
    }

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_language);
        setupToolbar(R.string.title_languages);

        prefs = new Prefs(this);
        report = engines().models();

        String raw = getIntent().getStringExtra(EXTRA_SIDE);
        side = Side.TARGET.name().equals(raw) ? Side.TARGET : Side.SOURCE;

        TabLayout tabs = findViewById(R.id.language_tabs);
        tabs.addTab(tabs.newTab().setText(R.string.lang_source));
        tabs.addTab(tabs.newTab().setText(R.string.lang_target));
        TabLayout.Tab initial = tabs.getTabAt(side == Side.SOURCE ? 0 : 1);
        if (initial != null) {
            initial.select();
        }
        tabs.addOnTabSelectedListener(new TabLayout.OnTabSelectedListener() {
            @Override
            public void onTabSelected(TabLayout.Tab tab) {
                side = tab.getPosition() == 0 ? Side.SOURCE : Side.TARGET;
                rebuild();
            }

            @Override
            public void onTabUnselected(TabLayout.Tab tab) {
            }

            @Override
            public void onTabReselected(TabLayout.Tab tab) {
            }
        });

        EditText search = findViewById(R.id.language_search);
        search.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int st, int c, int a) {
            }

            @Override
            public void onTextChanged(CharSequence s, int st, int b, int c) {
            }

            @Override
            public void afterTextChanged(Editable s) {
                query = s.toString().trim().toLowerCase(Locale.US);
                rebuild();
            }
        });

        RecyclerView list = findViewById(R.id.language_list);
        list.setLayoutManager(new LinearLayoutManager(this));
        adapter = new Adapter();
        list.setAdapter(adapter);
        rebuild();
    }

    private void rebuild() {
        List<Row> rows = new ArrayList<>();
        Lang selected = side == Side.SOURCE ? prefs.sourceLang() : prefs.targetLang();

        // userFacing(), not values(): implemented-but-hidden languages stay out of the picker.
        for (Lang lang : Lang.userFacing()) {
            if (!matchesQuery(lang)) {
                continue;
            }
            rows.add(new Row(lang, lang == selected, noteFor(lang)));
        }
        adapter.submit(rows);
    }

    private boolean matchesQuery(Lang lang) {
        if (query.isEmpty()) {
            return true;
        }
        return lang.englishName().toLowerCase(Locale.US).contains(query)
                || lang.nativeName().toLowerCase(Locale.US).contains(query)
                || lang.code().contains(query);
    }

    /**
     * Explains any limitation on choosing this language for the current side,
     * or {@code null} when it works normally.
     */
    @Nullable
    private String noteFor(Lang candidate) {
        Lang source = side == Side.SOURCE ? candidate : prefs.sourceLang();
        Lang target = side == Side.SOURCE ? prefs.targetLang() : candidate;

        if (side == Side.SOURCE && !report.canRecognize(candidate)) {
            return getString(R.string.lang_unavailable);
        }
        if (source == target) {
            return null;
        }
        if (!report.canTranslate(source, target)) {
            return getString(R.string.lang_unavailable);
        }
        if (report.isPivoted(source, target)) {
            return getString(R.string.lang_pivoted);
        }
        return null;
    }

    private void choose(Lang lang) {
        if (side == Side.SOURCE) {
            prefs.setSourceLang(lang);
        } else {
            prefs.setTargetLang(lang);
        }
        rebuild();
        finish();
    }

    /** One selectable language plus its availability note. */
    private static final class Row {
        final Lang lang;
        final boolean selected;
        @Nullable
        final String note;

        Row(Lang lang, boolean selected, @Nullable String note) {
            this.lang = lang;
            this.selected = selected;
            this.note = note;
        }
    }

    private final class Adapter extends RecyclerView.Adapter<Adapter.Holder> {

        private final List<Row> rows = new ArrayList<>();

        void submit(List<Row> updated) {
            rows.clear();
            rows.addAll(updated);
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public Holder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_language, parent, false);
            return new Holder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull Holder holder, int position) {
            holder.bind(rows.get(position));
        }

        @Override
        public int getItemCount() {
            return rows.size();
        }

        final class Holder extends RecyclerView.ViewHolder {
            private final TextView flag;
            private final TextView name;
            private final TextView note;
            private final ImageView check;

            Holder(@NonNull View itemView) {
                super(itemView);
                flag = itemView.findViewById(R.id.language_item_flag);
                name = itemView.findViewById(R.id.language_item_name);
                note = itemView.findViewById(R.id.language_item_note);
                check = itemView.findViewById(R.id.language_item_check);
            }

            void bind(Row row) {
                flag.setText(Flags.of(row.lang));
                name.setText(row.lang.displayName());
                check.setVisibility(row.selected ? View.VISIBLE : View.INVISIBLE);

                if (row.note == null) {
                    note.setVisibility(View.GONE);
                } else {
                    note.setVisibility(View.VISIBLE);
                    note.setText(row.note);
                }
                itemView.setOnClickListener(v -> choose(row.lang));
            }
        }
    }
}
