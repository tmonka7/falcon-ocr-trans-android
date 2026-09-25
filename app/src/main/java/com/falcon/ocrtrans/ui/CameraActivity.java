package com.falcon.ocrtrans.ui;

import android.Manifest;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageFormat;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.ImageButton;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.core.ImageProxy;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.content.ContextCompat;

import com.falcon.ocrtrans.R;
import com.falcon.ocrtrans.ocr.ImageOps;

import java.nio.ByteBuffer;
import java.util.concurrent.ExecutionException;

/** Live camera capture, then straight into the recognition pipeline. */
public final class CameraActivity extends ProcessingActivity {

    private static final String TAG = "CameraActivity";

    private PreviewView previewView;
    @Nullable
    private ImageCapture imageCapture;
    @Nullable
    private ProcessCameraProvider cameraProvider;
    private boolean torchOn;

    private ActivityResultLauncher<String> permissionLauncher;
    private ActivityResultLauncher<String> galleryLauncher;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_camera);
        bindBusyOverlay(R.id.camera_busy);

        previewView = findViewById(R.id.camera_preview);

        permissionLauncher = registerForActivityResult(
                new ActivityResultContracts.RequestPermission(), granted -> {
                    if (granted) {
                        startCamera();
                    } else {
                        Toast.makeText(this, R.string.camera_permission_rationale,
                                Toast.LENGTH_LONG).show();
                        finish();
                    }
                });

        galleryLauncher = registerForActivityResult(
                new ActivityResultContracts.GetContent(), uri -> {
                    if (uri != null) {
                        processUri(uri);
                    }
                });

        findViewById(R.id.camera_back).setOnClickListener(v -> finish());
        findViewById(R.id.camera_shutter).setOnClickListener(v -> capture());
        findViewById(R.id.camera_gallery).setOnClickListener(v -> openGallery());
        findViewById(R.id.camera_gallery_top).setOnClickListener(v -> openGallery());
        findViewById(R.id.camera_flash).setOnClickListener(v -> toggleTorch());
        findViewById(R.id.camera_auto).setOnClickListener(
                v -> Toast.makeText(this, R.string.camera_auto, Toast.LENGTH_SHORT).show());

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED) {
            startCamera();
        } else {
            permissionLauncher.launch(Manifest.permission.CAMERA);
        }
    }

    private void openGallery() {
        galleryLauncher.launch("image/*");
    }

    private void startCamera() {
        var future = ProcessCameraProvider.getInstance(this);
        future.addListener(() -> {
            try {
                cameraProvider = future.get();
                bindUseCases();
            } catch (ExecutionException | InterruptedException e) {
                Log.e(TAG, "cannot obtain camera provider", e);
                Toast.makeText(this, R.string.camera_unavailable, Toast.LENGTH_LONG).show();
                finish();
            }
        }, ContextCompat.getMainExecutor(this));
    }

    private void bindUseCases() {
        if (cameraProvider == null) {
            return;
        }
        Preview preview = new Preview.Builder().build();
        preview.setSurfaceProvider(previewView.getSurfaceProvider());

        // Minimise-latency favours a quick shutter over maximum quality; the
        // detector downscales to 960 px anyway, so extra megapixels buy nothing.
        imageCapture = new ImageCapture.Builder()
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                .build();

        try {
            cameraProvider.unbindAll();
            cameraProvider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA,
                    preview, imageCapture);
        } catch (IllegalArgumentException | IllegalStateException e) {
            Log.e(TAG, "cannot bind camera use cases", e);
            Toast.makeText(this, R.string.camera_unavailable, Toast.LENGTH_LONG).show();
            finish();
        }
    }

    private void toggleTorch() {
        if (cameraProvider == null) {
            return;
        }
        torchOn = !torchOn;
        ImageButton flash = findViewById(R.id.camera_flash);
        flash.setAlpha(torchOn ? 1f : 0.6f);
        if (imageCapture != null) {
            imageCapture.setFlashMode(torchOn
                    ? ImageCapture.FLASH_MODE_ON : ImageCapture.FLASH_MODE_OFF);
        }
    }

    private void capture() {
        if (imageCapture == null || isBusyShowing()) {
            return;
        }
        imageCapture.takePicture(ContextCompat.getMainExecutor(this),
                new ImageCapture.OnImageCapturedCallback() {
                    @Override
                    public void onCaptureSuccess(@NonNull ImageProxy image) {
                        Bitmap bitmap = null;
                        try {
                            bitmap = toBitmap(image);
                        } finally {
                            image.close();
                        }
                        if (bitmap == null) {
                            Toast.makeText(CameraActivity.this, R.string.error_image_load,
                                    Toast.LENGTH_SHORT).show();
                            return;
                        }
                        processBitmap(bitmap);
                    }

                    @Override
                    public void onError(@NonNull ImageCaptureException exception) {
                        Log.e(TAG, "capture failed", exception);
                        Toast.makeText(CameraActivity.this, R.string.error_generic,
                                Toast.LENGTH_SHORT).show();
                    }
                });
    }

    /**
     * Converts a captured frame to an upright bitmap.
     *
     * <p>CameraX delivers JPEG bytes in sensor orientation with the correction
     * carried alongside in {@link ImageProxy#getImageInfo()}, so the rotation has
     * to be applied here or every portrait capture reaches OCR sideways — where
     * the detector finds almost nothing.
     */
    @Nullable
    private static Bitmap toBitmap(@NonNull ImageProxy image) {
        if (image.getFormat() != ImageFormat.JPEG || image.getPlanes().length == 0) {
            return null;
        }
        ByteBuffer buffer = image.getPlanes()[0].getBuffer();
        byte[] bytes = new byte[buffer.remaining()];
        buffer.get(bytes);

        Bitmap decoded = BitmapFactory.decodeByteArray(bytes, 0, bytes.length);
        if (decoded == null) {
            return null;
        }
        int rotation = image.getImageInfo().getRotationDegrees();
        if (rotation == 0) {
            return decoded;
        }
        Bitmap rotated = ImageOps.rotate(decoded, rotation);
        if (rotated != decoded) {
            decoded.recycle();
        }
        return rotated;
    }

    @Override
    protected void onDestroy() {
        if (cameraProvider != null) {
            cameraProvider.unbindAll();
        }
        super.onDestroy();
    }
}
