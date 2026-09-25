package com.falcon.ocrtrans.mt;

import android.content.Context;

import androidx.annotation.NonNull;

import com.falcon.ocrtrans.util.Assets;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;

/**
 * Special token ids and decode limits for one OPUS-MT pair, as written by
 * {@code tools/convert_mt.py} from the model's own {@code config.json}.
 *
 * <p>These are read rather than hard-coded because they genuinely differ between
 * Helsinki-NLP releases — and a wrong {@code decoderStartId} does not fail
 * loudly, it just makes the decoder emit plausible text that ignores the input.
 */
public final class MtConfig {

    public final int padId;
    public final int eosId;
    public final int unkId;
    /** The token fed as the decoder's first input; Marian reuses pad for this. */
    public final int decoderStartId;
    /** Hard ceiling on generated tokens, a backstop against runaway decoding. */
    public final int maxLength;
    public final int vocabSize;

    private MtConfig(int padId, int eosId, int unkId, int decoderStartId, int maxLength, int vocabSize) {
        this.padId = padId;
        this.eosId = eosId;
        this.unkId = unkId;
        this.decoderStartId = decoderStartId;
        this.maxLength = maxLength;
        this.vocabSize = vocabSize;
    }

    @NonNull
    public static MtConfig load(@NonNull Context ctx, @NonNull String assetPath) throws IOException {
        try {
            JSONObject o = new JSONObject(Assets.readText(ctx, assetPath));
            int pad = o.optInt("pad_token_id", 58100);
            int eos = o.optInt("eos_token_id", 0);
            int unk = o.optInt("unk_token_id", 1);
            int start = o.optInt("decoder_start_token_id", pad);
            int maxLen = Math.max(8, Math.min(512, o.optInt("max_length", 256)));
            int vocab = o.optInt("vocab_size", 0);
            return new MtConfig(pad, eos, unk, start, maxLen, vocab);
        } catch (JSONException e) {
            throw new IOException("malformed MT config: " + assetPath, e);
        }
    }
}
