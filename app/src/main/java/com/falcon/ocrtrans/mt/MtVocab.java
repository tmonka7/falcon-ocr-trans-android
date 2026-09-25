package com.falcon.ocrtrans.mt;

import android.content.Context;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.util.Assets;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * The token to id table shared by an OPUS-MT pair's encoder and decoder.
 *
 * <p>Marian models use one joint vocabulary for both languages, which is why a
 * single table serves the source and target sides.
 */
public final class MtVocab {

    private final Map<String, Integer> tokenToId;
    private final String[] idToToken;
    private final int unkId;

    private MtVocab(Map<String, Integer> tokenToId, String[] idToToken, int unkId) {
        this.tokenToId = tokenToId;
        this.idToToken = idToToken;
        this.unkId = unkId;
    }

    /** Loads a {@code token<TAB>id} table. Ids need not be contiguous or sorted. */
    @NonNull
    public static MtVocab load(@NonNull Context ctx, @NonNull String assetPath) throws IOException {
        List<String> lines = Assets.readLines(ctx, assetPath);
        Map<String, Integer> map = new HashMap<>(lines.size() * 2);
        int maxId = -1;

        for (String line : lines) {
            if (line.isEmpty()) {
                continue;
            }
            // Split on the LAST tab: a token may itself be a tab character.
            int tab = line.lastIndexOf('\t');
            if (tab <= 0) {
                continue;
            }
            int id;
            try {
                id = Integer.parseInt(line.substring(tab + 1).trim());
            } catch (NumberFormatException e) {
                continue;
            }
            map.put(line.substring(0, tab), id);
            maxId = Math.max(maxId, id);
        }
        if (map.isEmpty() || maxId < 0) {
            throw new IOException("no vocabulary entries in " + assetPath);
        }

        String[] reverse = new String[maxId + 1];
        for (Map.Entry<String, Integer> e : map.entrySet()) {
            reverse[e.getValue()] = e.getKey();
        }
        Integer unk = map.get("<unk>");
        return new MtVocab(map, reverse, unk != null ? unk : 0);
    }

    public int size() {
        return idToToken.length;
    }

    public int unkId() {
        return unkId;
    }

    public int idOf(@NonNull String token) {
        Integer id = tokenToId.get(token);
        return id != null ? id : unkId;
    }

    public boolean contains(@NonNull String token) {
        return tokenToId.containsKey(token);
    }

    /** @return the token for an id, or the empty string if out of range. */
    @NonNull
    public String tokenOf(int id) {
        if (id < 0 || id >= idToToken.length || idToToken[id] == null) {
            return "";
        }
        return idToToken[id];
    }
}
