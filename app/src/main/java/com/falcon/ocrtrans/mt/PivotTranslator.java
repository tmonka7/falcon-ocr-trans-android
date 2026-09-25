package com.falcon.ocrtrans.mt;

import android.util.Log;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.core.Lang;

import java.util.List;

/**
 * Routes a translation through English when no direct model is installed.
 *
 * <p><b>Why this is not optional.</b> Helsinki-NLP publishes OPUS-MT models for
 * every pair involving English — {@code en↔ko}, {@code en↔ja}, {@code en↔zh} —
 * but publishes none for the CJK-to-CJK directions. There is no
 * {@code opus-mt-ko-ja} to download. So half the twelve directions this app
 * advertises can only be served by chaining two models, and that fact belongs in
 * the code rather than in a caveat somewhere.
 *
 * <p>The cost is real and worth stating plainly: a pivoted pair runs two full
 * encode-decode passes, so it takes about twice as long, and any error the first
 * model makes is input to the second. {@code ko→ja} is materially worse than
 * {@code ko→en}. {@link #isPivoted} lets the UI say so.
 *
 * <p>A direct model is always preferred when present, so dropping a genuine
 * {@code ko-ja} pair into {@code assets/model/mt/} makes this class step aside
 * for it with no code change.
 */
public final class PivotTranslator implements Translator {

    private static final String TAG = "PivotTranslator";

    /** The bridge language. Every published OPUS-MT pair here involves English. */
    private static final Lang PIVOT = Lang.EN;

    private final Translator delegate;

    public PivotTranslator(@NonNull Translator delegate) {
        this.delegate = delegate;
    }

    @Override
    public boolean supports(@NonNull Lang from, @NonNull Lang to) {
        if (from == to) {
            return true;
        }
        if (delegate.supports(from, to)) {
            return true;
        }
        return canPivot(from, to);
    }

    /** True when this direction would be served by two chained models. */
    public boolean isPivoted(@NonNull Lang from, @NonNull Lang to) {
        return from != to && !delegate.supports(from, to) && canPivot(from, to);
    }

    private boolean canPivot(Lang from, Lang to) {
        return from != PIVOT && to != PIVOT
                && delegate.supports(from, PIVOT)
                && delegate.supports(PIVOT, to);
    }

    @NonNull
    @Override
    public String translate(@NonNull String text, @NonNull Lang from, @NonNull Lang to)
            throws MtException {
        if (from == to) {
            return text;
        }
        if (delegate.supports(from, to)) {
            return delegate.translate(text, from, to);
        }
        requirePivot(from, to);
        String english = delegate.translate(text, from, PIVOT);
        return delegate.translate(english, PIVOT, to);
    }

    @NonNull
    @Override
    public List<String> translateAll(@NonNull List<String> texts,
                                     @NonNull Lang from,
                                     @NonNull Lang to) throws MtException {
        if (from == to) {
            return texts;
        }
        if (delegate.supports(from, to)) {
            return delegate.translateAll(texts, from, to);
        }
        requirePivot(from, to);

        // Both legs run as whole batches. The underlying translator keeps only
        // one pair loaded at a time, so doing it this way costs two model loads
        // for the page rather than two per paragraph.
        Log.d(TAG, "pivoting " + Lang.pairKey(from, to) + " through " + PIVOT.code());
        List<String> english = delegate.translateAll(texts, from, PIVOT);
        return delegate.translateAll(english, PIVOT, to);
    }

    private void requirePivot(Lang from, Lang to) throws MtException {
        if (!canPivot(from, to)) {
            throw new MtException("no model for " + Lang.pairKey(from, to)
                    + ", and it cannot be pivoted through " + PIVOT.code()
                    + " because " + Lang.pairKey(from, PIVOT) + " or "
                    + Lang.pairKey(PIVOT, to) + " is missing"
                    + " — run tools/fetch_models.sh");
        }
    }

    @Override
    public void close() {
        delegate.close();
    }
}
