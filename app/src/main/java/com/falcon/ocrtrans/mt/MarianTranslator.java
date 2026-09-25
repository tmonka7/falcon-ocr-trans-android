package com.falcon.ocrtrans.mt;

import android.content.Context;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.engine.ModelPaths;
import com.falcon.ocrtrans.util.Assets;

import java.io.IOException;
import java.nio.LongBuffer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;
import ai.onnxruntime.TensorInfo;

/**
 * OPUS-MT (Marian) translation on int8 ONNX weights, running fully offline.
 *
 * <p>The encoder is run once per input and its hidden states are reused for
 * every decode step; the decoder is then stepped greedily until it emits
 * end-of-sequence.
 *
 * <p><b>On the absent KV cache.</b> The exported {@code decoder_model.onnx} is
 * the cacheless variant, so each step re-attends over the whole prefix and
 * decoding a sequence of length <em>n</em> costs O(n²) attention rather than
 * O(n). That is a deliberate trade: wiring up {@code decoder_with_past} means
 * threading several dozen cache tensors through every step by name, and the
 * inputs here are OCR lines and short paragraphs, where the quadratic term stays
 * small. It is the first thing to revisit if long-document translation gets slow.
 *
 * <p>Only one pair's sessions are held at a time — each is roughly 35 MB, and
 * keeping several resident is the quickest way to get killed by the low-memory
 * killer mid-page.
 *
 * <p>Instances are not thread-safe; confine one to a single worker thread.
 */
public final class MarianTranslator implements Translator {

    private static final String TAG = "MarianTranslator";

    /** Beyond this many source tokens, text is split and translated in parts. */
    private static final int MAX_SOURCE_TOKENS = 192;
    /** Stop if output runs past the source length by this factor. */
    private static final float LENGTH_SAFETY_FACTOR = 3f;

    private final Context context;
    private final OrtEnvironment env;

    @Nullable
    private LoadedPair loaded;
    private boolean closed;

    public MarianTranslator(@NonNull Context context) {
        this.context = context.getApplicationContext();
        this.env = OrtEnvironment.getEnvironment();
    }

    @Override
    public boolean supports(@NonNull Lang from, @NonNull Lang to) {
        return from != to
                && Assets.exists(context, ModelPaths.mtEncoder(from, to))
                && Assets.exists(context, ModelPaths.mtDecoder(from, to));
    }

    @NonNull
    @Override
    public String translate(@NonNull String text, @NonNull Lang from, @NonNull Lang to)
            throws MtException {
        return translateAll(Collections.singletonList(text), from, to).get(0);
    }

    @NonNull
    @Override
    public List<String> translateAll(@NonNull List<String> texts, @NonNull Lang from, @NonNull Lang to)
            throws MtException {
        if (closed) {
            throw new MtException("translator is closed");
        }
        List<String> out = new ArrayList<>(texts.size());
        if (texts.isEmpty()) {
            return out;
        }
        if (from == to) {
            out.addAll(texts);
            return out;
        }

        LoadedPair pair = ensureLoaded(from, to);
        for (String text : texts) {
            if (text == null || text.trim().isEmpty()) {
                out.add("");
                continue;
            }
            out.add(translateOne(pair, text));
        }
        return out;
    }

    /** Splits overlong input, translates each chunk, and rejoins the results. */
    private String translateOne(LoadedPair pair, String text) throws MtException {
        List<String> chunks = splitToChunks(pair, text);
        StringBuilder sb = new StringBuilder();
        for (String chunk : chunks) {
            String piece = decodeChunk(pair, chunk);
            if (piece.isEmpty()) {
                continue;
            }
            if (sb.length() > 0) {
                sb.append(' ');
            }
            sb.append(piece);
        }
        return sb.toString().trim();
    }

    /**
     * Breaks text at sentence boundaries so no chunk exceeds
     * {@link #MAX_SOURCE_TOKENS}.
     *
     * <p>Marian degrades badly past its trained sequence length, and splitting at
     * punctuation keeps each chunk a coherent unit. A single sentence longer than
     * the budget is passed through whole rather than cut mid-clause, which
     * translates worse than a clean split but far better than a severed one.
     */
    private List<String> splitToChunks(LoadedPair pair, String text) {
        List<String> out = new ArrayList<>();
        if (pair.spm.encode(text).size() <= MAX_SOURCE_TOKENS) {
            out.add(text);
            return out;
        }

        // Keep the delimiter attached to the sentence it ends.
        String[] sentences = text.split("(?<=[.!?。！？…\\n])\\s*");
        StringBuilder current = new StringBuilder();
        for (String sentence : sentences) {
            if (sentence.isEmpty()) {
                continue;
            }
            String candidate = current.length() == 0 ? sentence : current + " " + sentence;
            if (pair.spm.encode(candidate).size() > MAX_SOURCE_TOKENS && current.length() > 0) {
                out.add(current.toString().trim());
                current.setLength(0);
                current.append(sentence);
            } else {
                current.setLength(0);
                current.append(candidate);
            }
        }
        if (current.length() > 0) {
            out.add(current.toString().trim());
        }
        if (out.isEmpty()) {
            out.add(text);
        }
        return out;
    }

    /** Encodes one chunk, then greedily decodes it to a string. */
    private String decodeChunk(LoadedPair pair, String chunk) throws MtException {
        List<String> pieces = pair.spm.encode(chunk);
        if (pieces.isEmpty()) {
            return "";
        }

        long[] inputIds = new long[pieces.size() + 1];
        for (int i = 0; i < pieces.size(); i++) {
            inputIds[i] = pair.sourceVocab.idOf(pieces.get(i));
        }
        inputIds[pieces.size()] = pair.config.eosId;

        long[] attentionMask = new long[inputIds.length];
        java.util.Arrays.fill(attentionMask, 1L);
        long[] shape = {1, inputIds.length};

        try (OnnxTensor idsTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(inputIds), shape);
             OnnxTensor maskTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(attentionMask), shape)) {

            Map<String, OnnxTensor> encoderInputs = new HashMap<>();
            encoderInputs.put(pair.encInputIds, idsTensor);
            encoderInputs.put(pair.encAttentionMask, maskTensor);

            try (OrtSession.Result encoded = pair.encoder.run(encoderInputs)) {
                OnnxTensor hidden = (OnnxTensor) encoded.get(0);
                return greedyDecode(pair, hidden, maskTensor, inputIds.length);
            }
        } catch (OrtException e) {
            throw new MtException("translation failed while encoding", e);
        }
    }

    /**
     * Steps the decoder, taking the highest-scoring token each time.
     *
     * <p>Greedy rather than beam search: a beam of 4 roughly quadruples decode
     * cost for a modest quality gain, and this runs on a phone while the user
     * waits with the page already on screen.
     */
    private String greedyDecode(LoadedPair pair,
                                OnnxTensor encoderHidden,
                                OnnxTensor encoderMask,
                                int sourceLength) throws MtException {
        int limit = Math.min(pair.config.maxLength,
                Math.max(16, (int) (sourceLength * LENGTH_SAFETY_FACTOR) + 8));

        List<Integer> generated = new ArrayList<>(limit);
        long[] decoderIds = new long[]{pair.config.decoderStartId};

        for (int step = 0; step < limit; step++) {
            try (OnnxTensor decIn = OnnxTensor.createTensor(
                    env, LongBuffer.wrap(decoderIds), new long[]{1, decoderIds.length})) {

                Map<String, OnnxTensor> inputs = new HashMap<>();
                inputs.put(pair.decInputIds, decIn);
                inputs.put(pair.decEncoderHidden, encoderHidden);
                inputs.put(pair.decEncoderMask, encoderMask);

                try (OrtSession.Result result = pair.decoder.run(inputs)) {
                    OnnxTensor logits = (OnnxTensor) result.get(0);
                    long[] shape = ((TensorInfo) logits.getInfo()).getShape();
                    int steps = (int) shape[1];
                    int vocab = (int) shape[2];

                    // Only the final position predicts the next token; skip
                    // straight to it instead of copying the whole [t, V] block.
                    float[] all = new float[steps * vocab];
                    logits.getFloatBuffer().get(all);

                    int base = (steps - 1) * vocab;
                    int best = 0;
                    float bestVal = Float.NEGATIVE_INFINITY;
                    for (int v = 0; v < vocab; v++) {
                        float value = all[base + v];
                        if (value > bestVal) {
                            bestVal = value;
                            best = v;
                        }
                    }

                    if (best == pair.config.eosId || best == pair.config.padId) {
                        break;
                    }
                    generated.add(best);

                    long[] next = new long[decoderIds.length + 1];
                    System.arraycopy(decoderIds, 0, next, 0, decoderIds.length);
                    next[decoderIds.length] = best;
                    decoderIds = next;
                }
            } catch (OrtException e) {
                throw new MtException("translation failed while decoding", e);
            }
        }

        List<String> pieces = new ArrayList<>(generated.size());
        for (int id : generated) {
            String token = pair.vocab.tokenOf(id);
            // Drop residual specials rather than printing them to the user.
            if (token.isEmpty() || (token.startsWith("<") && token.endsWith(">"))) {
                continue;
            }
            pieces.add(token);
        }
        return SpmEncoder.decodePieces(pieces);
    }

    // ------------------------------------------------------------ session setup

    private LoadedPair ensureLoaded(Lang from, Lang to) throws MtException {
        String key = Lang.pairKey(from, to);
        if (loaded != null && loaded.key.equals(key)) {
            return loaded;
        }
        if (loaded != null) {
            loaded.close();
            loaded = null;
        }

        try {
            OrtSession.SessionOptions opts = new OrtSession.SessionOptions();
            opts.setIntraOpNumThreads(Math.max(1,
                    Math.min(4, Runtime.getRuntime().availableProcessors() - 1)));
            opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);

            OrtSession encoder = env.createSession(
                    Assets.readBytes(context, ModelPaths.mtEncoder(from, to)), opts);
            OrtSession decoder = env.createSession(
                    Assets.readBytes(context, ModelPaths.mtDecoder(from, to)), opts);

            LoadedPair pair = new LoadedPair(
                    key,
                    encoder,
                    decoder,
                    SpmEncoder.load(context, ModelPaths.mtSourceSpm(from, to)),
                    MtVocab.load(context, ModelPaths.mtVocab(from, to)),
                    // Separate-vocabulary models encode with their own source table.
                    Assets.exists(context, ModelPaths.mtSourceVocab(from, to))
                            ? MtVocab.load(context, ModelPaths.mtSourceVocab(from, to))
                            : null,
                    MtConfig.load(context, ModelPaths.mtConfig(from, to)));
            pair.resolveInputNames();
            loaded = pair;
            Log.d(TAG, "loaded MT pair " + key);
            return pair;
        } catch (IOException e) {
            throw new MtException("model assets missing for " + key
                    + " — run tools/fetch_models.sh", e);
        } catch (OrtException e) {
            throw new MtException("cannot initialise ONNX sessions for " + key, e);
        }
    }

    @Override
    public void close() {
        closed = true;
        if (loaded != null) {
            loaded.close();
            loaded = null;
        }
    }

    /** One directed pair's sessions and the tables that go with them. */
    private static final class LoadedPair {
        final String key;
        final OrtSession encoder;
        final OrtSession decoder;
        final SpmEncoder spm;
        /** Target vocabulary: decodes generated ids. */
        final MtVocab vocab;
        /** Encodes source pieces; the same table as {@link #vocab} for joint vocabularies. */
        final MtVocab sourceVocab;
        final MtConfig config;

        String encInputIds = "input_ids";
        String encAttentionMask = "attention_mask";
        String decInputIds = "input_ids";
        String decEncoderMask = "encoder_attention_mask";
        String decEncoderHidden = "encoder_hidden_states";

        LoadedPair(String key, OrtSession encoder, OrtSession decoder,
                   SpmEncoder spm, MtVocab vocab, @Nullable MtVocab sourceVocab, MtConfig config) {
            this.key = key;
            this.encoder = encoder;
            this.decoder = decoder;
            this.spm = spm;
            this.vocab = vocab;
            this.sourceVocab = sourceVocab != null ? sourceVocab : vocab;
            this.config = config;
        }

        /**
         * Binds to the graph's actual input names.
         *
         * <p>Optimum's exporter has renamed these between releases, and a
         * mismatch surfaces as an opaque ONNX Runtime error about an unexpected
         * input rather than anything naming the offender — so match by substring
         * and keep the documented default when nothing matches.
         */
        void resolveInputNames() throws MtException {
            encInputIds = pick(encoder, "input_ids", encInputIds);
            encAttentionMask = pick(encoder, "attention_mask", encAttentionMask);
            decEncoderHidden = pick(decoder, "encoder_hidden_states", decEncoderHidden);
            decEncoderMask = pick(decoder, "encoder_attention_mask", decEncoderMask);

            // The decoder has two id-like inputs; its own must not collide with
            // the encoder mask that also contains "attention_mask".
            String chosen = null;
            for (String name : decoder.getInputNames()) {
                if (name.equals("input_ids") || name.equals("decoder_input_ids")) {
                    chosen = name;
                    break;
                }
            }
            if (chosen == null) {
                throw new MtException("decoder graph for " + key
                        + " exposes no input_ids; inputs are " + decoder.getInputNames());
            }
            decInputIds = chosen;
        }

        private static String pick(OrtSession session, String wanted, String fallback) {
            for (String name : session.getInputNames()) {
                if (name.equals(wanted)) {
                    return name;
                }
            }
            for (String name : session.getInputNames()) {
                if (name.contains(wanted)) {
                    return name;
                }
            }
            return fallback;
        }

        void close() {
            try {
                encoder.close();
            } catch (OrtException e) {
                Log.w(TAG, "error closing encoder", e);
            }
            try {
                decoder.close();
            } catch (OrtException e) {
                Log.w(TAG, "error closing decoder", e);
            }
        }
    }
}
