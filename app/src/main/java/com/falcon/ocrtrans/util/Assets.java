package com.falcon.ocrtrans.util;

import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.content.res.AssetManager;

import androidx.annotation.NonNull;

import java.io.ByteArrayOutputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/** Small helpers for pulling model blobs and text tables out of {@code assets/}. */
public final class Assets {

    private Assets() {
    }

    public static boolean exists(@NonNull Context ctx, @NonNull String path) {
        try (InputStream in = ctx.getAssets().open(path)) {
            return true;
        } catch (IOException e) {
            return false;
        }
    }

    /**
     * Reads an asset fully into a byte array.
     *
     * <p>Models are declared {@code noCompress} in {@code build.gradle}, so the
     * descriptor reports the real length up front and the array is allocated once
     * at the right size instead of growing through a dozen reallocations — which
     * matters when the blob is 40 MB and the device is already under pressure.
     */
    @NonNull
    public static byte[] readBytes(@NonNull Context ctx, @NonNull String path) throws IOException {
        AssetManager am = ctx.getAssets();
        long declared = -1L;
        try (AssetFileDescriptor afd = am.openFd(path)) {
            declared = afd.getLength();
        } catch (IOException ignored) {
            // Compressed or unaligned entry — fall through to a growing read.
        }
        try (InputStream in = am.open(path, AssetManager.ACCESS_STREAMING)) {
            if (declared > 0 && declared <= Integer.MAX_VALUE) {
                byte[] out = new byte[(int) declared];
                int off = 0;
                while (off < out.length) {
                    int n = in.read(out, off, out.length - off);
                    if (n < 0) {
                        break;
                    }
                    off += n;
                }
                if (off == out.length) {
                    return out;
                }
                // Short read means the declared length lied; restart generically.
            }
        }
        try (InputStream in = am.open(path, AssetManager.ACCESS_STREAMING);
             ByteArrayOutputStream bos = new ByteArrayOutputStream(1 << 20)) {
            byte[] buf = new byte[1 << 16];
            int n;
            while ((n = in.read(buf)) > 0) {
                bos.write(buf, 0, n);
            }
            return bos.toByteArray();
        }
    }

    /** Reads a UTF-8 asset as a list of lines, preserving blank lines. */
    @NonNull
    public static List<String> readLines(@NonNull Context ctx, @NonNull String path) throws IOException {
        List<String> out = new ArrayList<>();
        try (BufferedReader r = new BufferedReader(
                new InputStreamReader(ctx.getAssets().open(path), StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) {
                out.add(line);
            }
        }
        if (out.isEmpty()) {
            throw new FileNotFoundException("asset is empty: " + path);
        }
        return out;
    }

    @NonNull
    public static String readText(@NonNull Context ctx, @NonNull String path) throws IOException {
        return new String(readBytes(ctx, path), StandardCharsets.UTF_8);
    }
}
