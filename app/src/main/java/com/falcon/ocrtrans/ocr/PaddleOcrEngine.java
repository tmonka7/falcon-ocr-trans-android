package com.falcon.ocrtrans.ocr;

import android.content.Context;
import android.graphics.Bitmap;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.falcon.ocrtrans.core.Lang;
import com.falcon.ocrtrans.core.OcrResult;
import com.falcon.ocrtrans.core.Paragraph;
import com.falcon.ocrtrans.core.Quad;
import com.falcon.ocrtrans.core.TextLine;
import com.falcon.ocrtrans.engine.ModelPaths;
import com.falcon.ocrtrans.util.Assets;

import java.io.IOException;
import java.nio.FloatBuffer;
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
 * PP-OCR detection, angle classification and recognition, executed by ONNX
 * Runtime entirely on-device.
 *
 * <p>The three stages run in sequence: the detector finds text regions in a
 * downscaled copy of the page, each region is straightened into its own crop,
 * the classifier flips any crop that came out upside down, and the recogniser
 * reads the crops in batches.
 *
 * <p>Sessions are created on first use and cached, because loading a recognition
 * head costs far more than running it — switching source language mid-session
 * should not mean paying that twice.
 *
 * <p>Instances are not thread-safe; confine one to a single worker thread.
 */
public final class PaddleOcrEngine implements OcrEngine {

    private static final String TAG = "PaddleOcrEngine";

    /** Default long-edge cap fed to the detector; see {@link #setDetectionLimit}. */
    private static final int DEFAULT_DET_LIMIT = 960;
    /** Input height both the classifier and recogniser expect (PP-OCRv4). */
    private static final int REC_HEIGHT = 48;
    private static final int CLS_HEIGHT = 48;
    private static final int CLS_WIDTH = 192;
    /** Crops per recognition batch — a memory/throughput compromise. */
    private static final int REC_BATCH = 6;
    /** Widest padded crop; anything longer is squeezed rather than padded. */
    private static final int REC_MAX_WIDTH = 1200;
    /** Below this mean CTC confidence a line is treated as noise. */
    private static final float MIN_LINE_CONFIDENCE = 0.5f;
    /** Classifier confidence needed before a crop is actually flipped. */
    private static final float CLS_FLIP_THRESHOLD = 0.9f;

    private final Context context;
    private final OrtEnvironment env;
    private final DbPostProcessor postProcessor = new DbPostProcessor();

    @Nullable
    private OrtSession detSession;
    @Nullable
    private OrtSession clsSession;
    private boolean clsUnavailable;

    private final Map<Lang, OrtSession> recSessions = new HashMap<>();
    private final Map<Lang, CharDict> recDicts = new HashMap<>();

    private int detectionLimit = DEFAULT_DET_LIMIT;
    private boolean closed;

    public PaddleOcrEngine(@NonNull Context context) {
        this.context = context.getApplicationContext();
        this.env = OrtEnvironment.getEnvironment();
    }

    /**
     * Sets the long-edge size the page is scaled to before detection.
     *
     * <p>This is the one knob that genuinely trades accuracy for speed: the
     * detector sees a fixed input size, so a larger value means small print
     * survives downscaling, at a roughly quadratic cost in inference time. It
     * backs the Image Quality setting.
     */
    public void setDetectionLimit(int longEdgePixels) {
        this.detectionLimit = Math.max(320, Math.min(2048, longEdgePixels));
    }

    @NonNull
    @Override
    public OcrResult recognize(@NonNull Bitmap bitmap, @NonNull Lang lang) throws OcrException {
        if (closed) {
            throw new OcrException("engine is closed");
        }
        long started = System.currentTimeMillis();

        List<Quad> quads = detect(bitmap);
        if (quads.isEmpty()) {
            return OcrResult.empty(bitmap.getWidth(), bitmap.getHeight());
        }

        List<Bitmap> crops = new ArrayList<>(quads.size());
        for (Quad q : quads) {
            crops.add(ImageOps.cropQuad(bitmap, q));
        }

        try {
            classifyAndFlip(crops);
            List<CtcDecoder.Decoded> decoded = recognizeCrops(crops, lang);

            List<TextLine> lines = new ArrayList<>();
            for (int i = 0; i < decoded.size(); i++) {
                CtcDecoder.Decoded d = decoded.get(i);
                if (d.text.trim().isEmpty() || d.confidence < MIN_LINE_CONFIDENCE) {
                    continue;
                }
                TextLine line = new TextLine(quads.get(i), d.text.trim(), d.confidence);
                int[] colors = ImageOps.sampleColors(crops.get(i));
                line.setColors(colors[0], colors[1]);
                lines.add(line);
            }

            List<TextLine> ordered = LineGrouper.sortReadingOrder(lines);
            List<Paragraph> paragraphs = LineGrouper.group(ordered);
            long elapsed = System.currentTimeMillis() - started;
            Log.d(TAG, "recognised " + ordered.size() + " line(s) in " + elapsed + " ms");
            return new OcrResult(ordered, paragraphs,
                    bitmap.getWidth(), bitmap.getHeight(), elapsed);
        } finally {
            for (Bitmap b : crops) {
                if (!b.isRecycled()) {
                    b.recycle();
                }
            }
        }
    }

    // ---------------------------------------------------------------- detection

    @NonNull
    private List<Quad> detect(@NonNull Bitmap bitmap) throws OcrException {
        Bitmap resized = ImageOps.resizeForDetection(bitmap, detectionLimit);
        int rw = resized.getWidth();
        int rh = resized.getHeight();

        float[] input = ImageOps.detectionTensor(resized);
        if (resized != bitmap) {
            resized.recycle();
        }

        OrtSession session = detectionSession();
        String inputName = firstInputName(session);

        try (OnnxTensor tensor = OnnxTensor.createTensor(
                env, FloatBuffer.wrap(input), new long[]{1, 3, rh, rw});
             OrtSession.Result result = session.run(Collections.singletonMap(inputName, tensor))) {

            OnnxTensor out = (OnnxTensor) result.get(0);
            long[] shape = ((TensorInfo) out.getInfo()).getShape();
            // Expected [1, 1, H, W]; the map's own dimensions are authoritative
            // because the exported graph may round them differently than we did.
            int mapH = (int) shape[shape.length - 2];
            int mapW = (int) shape[shape.length - 1];

            FloatBuffer buf = out.getFloatBuffer();
            float[] prob = new float[mapH * mapW];
            buf.get(prob);

            float scaleX = bitmap.getWidth() / (float) mapW;
            float scaleY = bitmap.getHeight() / (float) mapH;
            return postProcessor.extract(prob, mapW, mapH, scaleX, scaleY);
        } catch (OrtException e) {
            throw new OcrException("text detection failed", e);
        }
    }

    // ----------------------------------------------------------- classification

    /** Rotates any crop the classifier reports as 180 degrees out. */
    private void classifyAndFlip(@NonNull List<Bitmap> crops) {
        OrtSession session;
        try {
            session = classifierSession();
        } catch (OcrException e) {
            return;
        }
        if (session == null) {
            return;
        }
        String inputName = firstInputName(session);

        for (int i = 0; i < crops.size(); i++) {
            Bitmap crop = crops.get(i);
            float[] input = ImageOps.recognitionTensor(crop, CLS_HEIGHT, CLS_WIDTH);
            try (OnnxTensor tensor = OnnxTensor.createTensor(
                    env, FloatBuffer.wrap(input), new long[]{1, 3, CLS_HEIGHT, CLS_WIDTH});
                 OrtSession.Result result = session.run(Collections.singletonMap(inputName, tensor))) {

                OnnxTensor out = (OnnxTensor) result.get(0);
                float[] scores = new float[2];
                out.getFloatBuffer().get(scores);
                // Class 1 is "rotated 180". Only act on a confident call: a wrong
                // flip is unrecoverable, whereas leaving it alone merely degrades.
                if (scores[1] > CLS_FLIP_THRESHOLD) {
                    Bitmap flipped = ImageOps.rotate(crop, 180);
                    crops.set(i, flipped);
                    crop.recycle();
                }
            } catch (OrtException e) {
                Log.w(TAG, "angle classification failed; keeping original orientation", e);
                return;
            }
        }
    }

    // -------------------------------------------------------------- recognition

    @NonNull
    private List<CtcDecoder.Decoded> recognizeCrops(@NonNull List<Bitmap> crops, @NonNull Lang lang)
            throws OcrException {
        OrtSession session = recognitionSession(lang);
        CharDict dict = recDicts.get(lang);
        if (dict == null) {
            throw new OcrException("no character dictionary loaded for " + lang.code());
        }
        String inputName = firstInputName(session);

        // Sort by aspect ratio so each batch pads to a similar width. Batching
        // crops of wildly different lengths together wastes most of the tensor
        // on padding, which is the single biggest avoidable cost in this stage.
        Integer[] order = new Integer[crops.size()];
        for (int i = 0; i < order.length; i++) {
            order[i] = i;
        }
        final float[] ratios = new float[crops.size()];
        for (int i = 0; i < crops.size(); i++) {
            Bitmap b = crops.get(i);
            ratios[i] = b.getWidth() / (float) Math.max(1, b.getHeight());
        }
        java.util.Arrays.sort(order, (a, b) -> Float.compare(ratios[a], ratios[b]));

        CtcDecoder.Decoded[] results = new CtcDecoder.Decoded[crops.size()];

        for (int start = 0; start < order.length; start += REC_BATCH) {
            int end = Math.min(order.length, start + REC_BATCH);
            int batch = end - start;

            float maxRatio = 0f;
            for (int i = start; i < end; i++) {
                maxRatio = Math.max(maxRatio, ratios[order[i]]);
            }
            int padW = (int) Math.ceil(maxRatio * REC_HEIGHT / 8.0) * 8;
            padW = Math.max(16, Math.min(REC_MAX_WIDTH, padW));

            float[] input = new float[batch * 3 * REC_HEIGHT * padW];
            int stride = 3 * REC_HEIGHT * padW;
            for (int i = 0; i < batch; i++) {
                float[] one = ImageOps.recognitionTensor(crops.get(order[start + i]), REC_HEIGHT, padW);
                System.arraycopy(one, 0, input, i * stride, stride);
            }

            try (OnnxTensor tensor = OnnxTensor.createTensor(
                    env, FloatBuffer.wrap(input), new long[]{batch, 3, REC_HEIGHT, padW});
                 OrtSession.Result result = session.run(Collections.singletonMap(inputName, tensor))) {

                OnnxTensor out = (OnnxTensor) result.get(0);
                long[] shape = ((TensorInfo) out.getInfo()).getShape();
                int steps = (int) shape[1];
                int classes = (int) shape[2];

                float[] flat = new float[batch * steps * classes];
                out.getFloatBuffer().get(flat);

                for (int i = 0; i < batch; i++) {
                    float[] one = new float[steps * classes];
                    System.arraycopy(flat, i * steps * classes, one, 0, one.length);
                    results[order[start + i]] = CtcDecoder.decode(one, steps, classes, dict);
                }
            } catch (OrtException e) {
                throw new OcrException("text recognition failed", e);
            }
        }

        List<CtcDecoder.Decoded> out = new ArrayList<>(results.length);
        for (CtcDecoder.Decoded d : results) {
            out.add(d != null ? d : new CtcDecoder.Decoded("", 0f));
        }
        return out;
    }

    // ------------------------------------------------------------ session setup

    private OrtSession detectionSession() throws OcrException {
        if (detSession == null) {
            detSession = createSession(ModelPaths.DET_MODEL);
        }
        return detSession;
    }

    @Nullable
    private OrtSession classifierSession() throws OcrException {
        if (clsUnavailable) {
            return null;
        }
        if (clsSession == null) {
            if (!Assets.exists(context, ModelPaths.CLS_MODEL)) {
                // Optional stage; note it once and carry on without flipping.
                Log.i(TAG, "no angle classifier bundled; skipping orientation correction");
                clsUnavailable = true;
                return null;
            }
            clsSession = createSession(ModelPaths.CLS_MODEL);
        }
        return clsSession;
    }

    private OrtSession recognitionSession(@NonNull Lang lang) throws OcrException {
        OrtSession cached = recSessions.get(lang);
        if (cached != null) {
            return cached;
        }
        OrtSession session = createSession(ModelPaths.recModel(lang));
        recSessions.put(lang, session);

        // The dictionary has to agree with the head's class count, so read the
        // count off the loaded graph rather than trusting the file on disk.
        int classes;
        try {
            TensorInfo info = (TensorInfo) session.getOutputInfo()
                    .values().iterator().next().getInfo();
            long[] shape = info.getShape();
            classes = (int) shape[shape.length - 1];
        } catch (OrtException e) {
            throw new OcrException("cannot read recognition output shape", e);
        }
        if (classes <= 1) {
            throw new OcrException("recognition model for " + lang.code()
                    + " reports a dynamic class count; re-export it with a fixed vocabulary");
        }

        try {
            recDicts.put(lang, CharDict.load(context, ModelPaths.recDict(lang), classes));
        } catch (IOException e) {
            throw new OcrException("cannot load dictionary for " + lang.code(), e);
        }
        return session;
    }

    private OrtSession createSession(@NonNull String assetPath) throws OcrException {
        try {
            byte[] model = Assets.readBytes(context, assetPath);
            OrtSession.SessionOptions opts = new OrtSession.SessionOptions();
            opts.setIntraOpNumThreads(Math.max(1,
                    Math.min(4, Runtime.getRuntime().availableProcessors() - 1)));
            opts.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
            return env.createSession(model, opts);
        } catch (IOException e) {
            throw new OcrException("model asset missing: " + assetPath
                    + " — run tools/fetch_models.sh", e);
        } catch (OrtException e) {
            throw new OcrException("cannot initialise ONNX session for " + assetPath, e);
        }
    }

    private static String firstInputName(@NonNull OrtSession session) {
        return session.getInputNames().iterator().next();
    }

    @Override
    public void close() {
        closed = true;
        closeQuietly(detSession);
        closeQuietly(clsSession);
        for (OrtSession s : recSessions.values()) {
            closeQuietly(s);
        }
        recSessions.clear();
        recDicts.clear();
        detSession = null;
        clsSession = null;
    }

    private static void closeQuietly(@Nullable OrtSession session) {
        if (session == null) {
            return;
        }
        try {
            session.close();
        } catch (OrtException e) {
            Log.w(TAG, "error closing session", e);
        }
    }
}
