package com.falcon.ocrtrans.data;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.core.Lang;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

/**
 * SQLite-backed store of past translations.
 *
 * <p>Plain {@link SQLiteOpenHelper} rather than Room: the schema is one table
 * with no relations, and Room would add an annotation processor to a
 * Java-only build for no benefit here.
 *
 * <p>All methods touch disk and must be called off the main thread.
 */
public final class HistoryStore {

    private static final String DB_NAME = "history.db";
    private static final int DB_VERSION = 1;
    private static final String TABLE = "history";

    private static final String COL_ID = "_id";
    private static final String COL_KIND = "kind";
    private static final String COL_SOURCE_LANG = "source_lang";
    private static final String COL_TARGET_LANG = "target_lang";
    private static final String COL_SOURCE_TEXT = "source_text";
    private static final String COL_TRANSLATED = "translated_text";
    private static final String COL_IMAGE_PATH = "image_path";
    private static final String COL_CREATED = "created_at";

    private final Helper helper;

    public HistoryStore(@NonNull Context context) {
        this.helper = new Helper(context.getApplicationContext());
    }

    /** @return the new row id. */
    public long insert(@NonNull HistoryItem.Kind kind,
                       @NonNull Lang source,
                       @NonNull Lang target,
                       @NonNull String sourceText,
                       @NonNull String translatedText,
                       @Nullable String imagePath) {
        ContentValues v = new ContentValues();
        v.put(COL_KIND, kind.name());
        v.put(COL_SOURCE_LANG, source.code());
        v.put(COL_TARGET_LANG, target.code());
        v.put(COL_SOURCE_TEXT, sourceText);
        v.put(COL_TRANSLATED, translatedText);
        v.put(COL_IMAGE_PATH, imagePath);
        v.put(COL_CREATED, System.currentTimeMillis());
        return helper.getWritableDatabase().insert(TABLE, null, v);
    }

    @NonNull
    public List<HistoryItem> recent(int limit) {
        List<HistoryItem> out = new ArrayList<>();
        try (Cursor c = helper.getReadableDatabase().query(
                TABLE, null, null, null, null, null,
                COL_CREATED + " DESC", String.valueOf(limit))) {
            while (c.moveToNext()) {
                out.add(read(c));
            }
        }
        return out;
    }

    @Nullable
    public HistoryItem byId(long id) {
        try (Cursor c = helper.getReadableDatabase().query(
                TABLE, null, COL_ID + "=?", new String[]{String.valueOf(id)},
                null, null, null, "1")) {
            return c.moveToFirst() ? read(c) : null;
        }
    }

    /** Removes a row and the rendered image it owns. */
    public void delete(long id) {
        HistoryItem item = byId(id);
        if (item != null && item.imagePath != null) {
            deleteFileQuietly(item.imagePath);
        }
        helper.getWritableDatabase().delete(TABLE, COL_ID + "=?", new String[]{String.valueOf(id)});
    }

    /** Empties the table, removing every rendered image with it. */
    public void clear() {
        // Collect paths before the rows go, or the files are orphaned on disk
        // with nothing left pointing at them.
        List<String> paths = new ArrayList<>();
        try (Cursor c = helper.getReadableDatabase().query(
                TABLE, new String[]{COL_IMAGE_PATH}, COL_IMAGE_PATH + " IS NOT NULL",
                null, null, null, null)) {
            while (c.moveToNext()) {
                paths.add(c.getString(0));
            }
        }
        helper.getWritableDatabase().delete(TABLE, null, null);
        for (String p : paths) {
            deleteFileQuietly(p);
        }
    }

    public int count() {
        try (Cursor c = helper.getReadableDatabase()
                .rawQuery("SELECT COUNT(*) FROM " + TABLE, null)) {
            return c.moveToFirst() ? c.getInt(0) : 0;
        }
    }

    public void close() {
        helper.close();
    }

    private static void deleteFileQuietly(String path) {
        try {
            File f = new File(path);
            if (f.exists()) {
                //noinspection ResultOfMethodCallIgnored
                f.delete();
            }
        } catch (SecurityException ignored) {
            // Nothing useful to do; the row is going away regardless.
        }
    }

    private static HistoryItem read(Cursor c) {
        return new HistoryItem(
                c.getLong(c.getColumnIndexOrThrow(COL_ID)),
                HistoryItem.Kind.fromName(c.getString(c.getColumnIndexOrThrow(COL_KIND))),
                Lang.fromCodeOr(c.getString(c.getColumnIndexOrThrow(COL_SOURCE_LANG)), Lang.EN),
                Lang.fromCodeOr(c.getString(c.getColumnIndexOrThrow(COL_TARGET_LANG)), Lang.ZH),
                orEmpty(c.getString(c.getColumnIndexOrThrow(COL_SOURCE_TEXT))),
                orEmpty(c.getString(c.getColumnIndexOrThrow(COL_TRANSLATED))),
                c.getString(c.getColumnIndexOrThrow(COL_IMAGE_PATH)),
                c.getLong(c.getColumnIndexOrThrow(COL_CREATED)));
    }

    private static String orEmpty(@Nullable String s) {
        return s != null ? s : "";
    }

    private static final class Helper extends SQLiteOpenHelper {

        Helper(Context context) {
            super(context, DB_NAME, null, DB_VERSION);
        }

        @Override
        public void onCreate(SQLiteDatabase db) {
            db.execSQL("CREATE TABLE " + TABLE + " ("
                    + COL_ID + " INTEGER PRIMARY KEY AUTOINCREMENT, "
                    + COL_KIND + " TEXT NOT NULL, "
                    + COL_SOURCE_LANG + " TEXT NOT NULL, "
                    + COL_TARGET_LANG + " TEXT NOT NULL, "
                    + COL_SOURCE_TEXT + " TEXT NOT NULL, "
                    + COL_TRANSLATED + " TEXT NOT NULL, "
                    + COL_IMAGE_PATH + " TEXT, "
                    + COL_CREATED + " INTEGER NOT NULL)");
            db.execSQL("CREATE INDEX idx_history_created ON " + TABLE + "(" + COL_CREATED + " DESC)");
        }

        @Override
        public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
            // No shipped versions to migrate from yet; history is a cache and
            // rebuilding it costs the user nothing.
            db.execSQL("DROP TABLE IF EXISTS " + TABLE);
            onCreate(db);
        }
    }
}
