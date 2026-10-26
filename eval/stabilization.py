"""Ground-truth synthetic camera-motion test; not a substitute for handheld field clips."""

import argparse
import time as clock
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from eval.synthetic import git_revision, source_tree_sha256
from resonance.models import Roi
from resonance.motion.phase_corr import extract_phase_correlation
from resonance.runtime import provenance
from resonance.stabilize.ego_motion import EgoMotion


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-frames", type=int, default=30)
    parser.add_argument(
        "--output", type=Path, default=Path("eval/results/stabilization.json")
    )
    args = parser.parse_args()
    cv2.setRNGSeed(42)
    rng = np.random.default_rng(42)
    width, height, fps, count = 384, 256, 60, 240
    image = rng.normal(size=(height, width)).astype(np.float32)
    image = np.asarray(cv2.GaussianBlur(image, (0, 0), 1), dtype=np.float32)
    image = np.clip((image - image.mean()) / image.std() * 40 + 128, 0, 255)
    # Distinct static markings make the synthetic background suitable for learned features.
    image = image.astype(np.uint8)
    for index in range(30):
        x, y = rng.integers(10, width - 40), rng.integers(10, height - 10)
        cv2.putText(
            image, str(index), (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, 40, 1
        )
    structure = Roi(id="whole-structure", x=96, y=80, width=192, height=96)
    roi = Roi(id="deck", x=128, y=96, width=96, height=64)
    time = np.arange(count) / fps
    truth = 0.5 * np.sqrt(2) * np.sin(2 * np.pi * 7.1 * time)
    shake = 2 * np.sqrt(2) * np.sin(2 * np.pi * 1.7 * time)
    aliked_path = Path("models/aliked-n16rot-top1k-640.onnx")
    lightglue_path = Path("models/aliked_lightglue.onnx")
    stabilizer = EgoMotion(
        aliked_path, lightglue_path, [structure], refresh_frames=args.refresh_frames
    )
    raw = []
    corrected = []
    digest = hashlib.sha256()
    started = clock.perf_counter()
    for index in range(count):
        transform = np.array([[1, 0, 0], [0, 1, truth[index]]], np.float32)
        shifted_deck = cv2.warpAffine(
            image,
            transform,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101,
        )
        frame = image.copy()
        frame[80:176, 96:288] = shifted_deck[80:176, 96:288]
        camera = cv2.getRotationMatrix2D(
            (width / 2, height / 2), 0.1 * np.sin(2 * np.pi * 0.7 * time[index]), 1
        )
        camera[1, 2] += shake[index]
        frame = np.asarray(
            cv2.warpAffine(
                frame,
                camera,
                (width, height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REFLECT_101,
            ),
            dtype=np.uint8,
        )
        digest.update(frame.tobytes())
        corrected_frame = stabilizer.apply(frame)
        raw.append(
            frame[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width].astype(
                np.float32
            )
        )
        corrected.append(
            corrected_frame[
                roi.y : roi.y + roi.height, roi.x : roi.x + roi.width
            ].astype(np.float32)
        )
    elapsed = clock.perf_counter() - started
    raw_series = extract_phase_correlation(raw, fps, "deck")
    corrected_series = extract_phase_correlation(corrected, fps, "deck")
    raw_error = float(
        np.sqrt(np.mean((np.asarray(raw_series.displacement_px) - truth) ** 2))
    )
    corrected_error = float(
        np.sqrt(np.mean((np.asarray(corrected_series.displacement_px) - truth) ** 2))
    )
    result = {
        "kind": "synthetic_camera_shake",
        "seed": 42,
        "git_revision": git_revision(),
        "source_tree_sha256": source_tree_sha256(),
        "input_sha256": digest.hexdigest(),
        "provenance": provenance().model_dump(),
        "fps": fps,
        "frames": count,
        "configuration": {
            "displacement_rms_px": 0.5,
            "frequency_hz": 7.1,
            "camera_translation_rms_px": 2,
            "refresh_frames": args.refresh_frames,
        },
        "model_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (aliked_path, lightglue_path)
        },
        "processing_seconds": elapsed,
        "processing_fps": count / elapsed,
        "raw_rmse_px": raw_error,
        "stabilized_rmse_px": corrected_error,
        "benefit_observed": corrected_error < raw_error,
        "limitations": [
            "Synthetic planar camera motion only",
            "No real handheld clip in this run",
            "Timing includes generated scene transforms and stabilization; one exploratory repeat",
            "No amplitude-accuracy claim",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("raw_rmse_px", "stabilized_rmse_px", "benefit_observed")
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
