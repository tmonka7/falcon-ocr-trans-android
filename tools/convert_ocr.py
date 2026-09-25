#!/usr/bin/env python3
"""Convert PaddleOCR inference models to the ONNX layout the app expects.

Run this once on a desktop; the phone only ever sees the output. Requires::

    pip install paddlepaddle paddle2onnx onnx onnxruntime

The layout written here is the one hard-coded in
``app/src/main/java/com/falcon/ocrtrans/engine/ModelPaths.java``. Change one and
you must change the other.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fix_onnx_concat  # noqa: E402  (needs the path entry above)

__all__ = ["main"]

# Each entry: destination directory -> (extracted Paddle model dir, dictionary file).
# Detection and angle classification are language independent and have no dict.
REC_MODELS = {
    "english": ("en_PP-OCRv4_rec_infer", "en_dict.txt"),
    "korean": ("korean_PP-OCRv3_rec_infer", "korean_dict.txt"),
    "japan": ("japan_PP-OCRv3_rec_infer", "japan_dict.txt"),
    "chinese": ("ch_PP-OCRv4_rec_infer", "ppocr_keys_v1.txt"),
}


def paddle2onnx_cmd() -> list[str]:
    """Locate the paddle2onnx entry point.

    It ships as a console script, not a runnable module, so ``python -m
    paddle2onnx`` fails. Prefer the executable on PATH and fall back to the
    installed script inside this interpreter's environment.
    """
    found = shutil.which("paddle2onnx")
    if found:
        return [found]

    scripts = Path(sys.executable).parent / "Scripts" / "paddle2onnx.exe"
    if scripts.is_file():
        return [str(scripts)]

    bin_dir = Path(sys.executable).parent / "paddle2onnx"
    if bin_dir.is_file():
        return [str(bin_dir)]

    sys.exit("paddle2onnx not found on PATH — pip install paddle2onnx")


def run(cmd: list[str]) -> None:
    print("  $", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(f"command failed with exit code {result.returncode}")


def to_onnx(paddle_dir: Path, out_file: Path) -> None:
    """Export one Paddle inference model to ONNX with dynamic axes.

    Batch size and image dimensions must stay dynamic: the detector is fed
    whatever multiple-of-32 size the page scales to, and the recogniser is fed
    variable-width batches of line crops.
    """
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # PaddlePaddle 3.x writes inference.json; the 2.x archives on bcebos still
    # carry inference.pdmodel. Accept whichever this model actually ships.
    model_filename = "inference.pdmodel"
    if not (paddle_dir / model_filename).is_file():
        if (paddle_dir / "inference.json").is_file():
            model_filename = "inference.json"
        else:
            sys.exit(f"no inference.pdmodel or inference.json in {paddle_dir}")

    run(paddle2onnx_cmd() + [
        "--model_dir", str(paddle_dir),
        "--model_filename", model_filename,
        "--params_filename", "inference.pdiparams",
        "--save_file", str(out_file),
        "--opset_version", "14",
        "--enable_onnx_checker", "True",
    ])

    # paddle2onnx emits Concat nodes that mix rank-0 and rank-1 shape
    # components. Paddle's runtime tolerates it; ONNX Runtime rejects the model
    # outright, so it has to be repaired before the file is usable on device.
    fix_onnx_concat.repair_file(out_file)


def main() -> None:
    # Keep progress visible when stdout is redirected into a log; otherwise the
    # prints block-buffer and only stderr warnings appear while work proceeds.
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-dir", type=Path, default=Path("build/models/paddle"),
                        help="where fetch_models.sh extracted the Paddle archives")
    parser.add_argument("--assets-dir", type=Path,
                        default=Path("app/src/main/assets/model/ocr"),
                        help="destination inside the app's assets")
    args = parser.parse_args()

    src: Path = args.download_dir
    dst: Path = args.assets_dir

    if not src.is_dir():
        sys.exit(f"{src} does not exist — run tools/fetch_models.sh first")

    print("detection")
    to_onnx(src / "ch_PP-OCRv4_det_infer", dst / "det" / "det.onnx")

    cls_src = src / "ch_ppocr_mobile_v2.0_cls_infer"
    if cls_src.is_dir():
        print("angle classifier")
        to_onnx(cls_src, dst / "cls" / "cls.onnx")
    else:
        print("angle classifier: not downloaded, skipping (optional)")

    for name, (model_dir, dict_name) in REC_MODELS.items():
        print(f"recognition: {name}")
        to_onnx(src / model_dir, dst / "rec" / name / "rec.onnx")

        dict_src = src / "dicts" / dict_name
        if not dict_src.is_file():
            sys.exit(f"missing dictionary {dict_src} — re-run tools/fetch_models.sh")
        dict_dst = dst / "rec" / name / "dict.txt"
        shutil.copyfile(dict_src, dict_dst)
        print(f"    dict -> {dict_dst}")

    print("\nOCR models written to", dst)


if __name__ == "__main__":
    main()
