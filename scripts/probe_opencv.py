"""P0 compatibility probe. All inference explicitly selects OpenCV's new DNN engine."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import cv2
import numpy as np

from resonance.runtime import provenance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, default=Path("models"))
    parser.add_argument(
        "--output", type=Path, default=Path("eval/results/api_reality.json")
    )
    args = parser.parse_args()
    result: dict[str, object] = {"provenance": provenance().model_dump(), "seed": 42}
    result["apis"] = {
        name: {"create": getattr(cv2, name).create.__doc__}
        for name in ("ALIKED", "DISK", "LightGlueMatcher", "ANNIndex")
    }
    params = cv2.ALIKED_Params()
    result["aliked_params"] = {
        "engine": params.engine,
        "input_size": params.inputSize,
        "backend": params.backend,
        "target": params.target,
    }
    result["dnn_engine"] = "ENGINE_NEW"
    models: dict[str, object] = {}
    rng = np.random.default_rng(42)
    for name in (
        "object_detection_yolox_2022nov.onnx",
        "aliked-n16rot-top1k-640.onnx",
        "aliked_lightglue.onnx",
    ):
        path = args.models / name
        if not path.exists():
            models[name] = {"status": "missing"}
            continue
        record: dict[str, object] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()
        }
        started = time.perf_counter()
        try:
            net = cv2.dnn.readNetFromONNX(str(path), cv2.dnn.ENGINE_NEW)
            record["load_seconds"] = time.perf_counter() - started
            record["outputs"] = list(net.getUnconnectedOutLayersNames())
            started = time.perf_counter()
            if "lightglue" in name:
                kpts = rng.uniform(-1, 1, size=(1, 32, 2)).astype(np.float32)
                desc = rng.normal(size=(1, 32, 128)).astype(np.float32)
                desc /= np.linalg.norm(desc, axis=-1, keepdims=True)
                for key, array in {
                    "kpts0": kpts,
                    "kpts1": kpts,
                    "desc0": desc,
                    "desc1": desc,
                }.items():
                    net.setInput(array, key)
            else:
                image = rng.uniform(0, 1, size=(1, 3, 640, 640)).astype(np.float32)
                net.setInput(image, "image") if "aliked" in name else net.setInput(
                    image
                )
            outputs = net.forward(net.getUnconnectedOutLayersNames())
            record["forward_seconds"] = time.perf_counter() - started
            record["output_shapes"] = [list(array.shape) for array in outputs]
            record["status"] = "forward_passed"
        except cv2.error as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
        models[name] = record
        print(f"{name}: {record['status']}", flush=True)
    result["models"] = models
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
