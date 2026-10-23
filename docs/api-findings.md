# P0: executed OpenCV reality check

Status: local runtime and model forward passes verified. This is a pip wheel on a local Arm Mac, not COOL or AWS evidence. `eval/results/api_reality.json` records the runtime path, build hash, signatures, model hashes, output shapes and observed single-run timings. These timings are smoke checks, not benchmarks.

## Reproduce

```sh
uv sync --project engine --extra local
make models
make probe
```

The Python package pin is `opencv-python-headless==5.0.0.93`. Its imported version is recorded in the JSON. The source checkout inspected is OpenCV `5.x` commit `3f12ad88abb751701c3f48464652283710d06cdb`; the current branch can differ from the wheel, so execution against the wheel is decisive.

## Native Python APIs

The installed wheel exposes all requested feature classes directly under `cv2`, rather than a Python `cv2.features` namespace:

```python
import cv2
params = cv2.ALIKED_Params()
params.engine = cv2.dnn.ENGINE_NEW
aliked = cv2.ALIKED.create("models/aliked-n16rot-top1k-640.onnx", params)
keypoints, descriptors = aliked.detectAndCompute(image, background_mask)

matcher = cv2.LightGlueMatcher.create("models/aliked_lightglue.onnx")
matcher.setPairInfo(query_xy, train_xy, query_image_size, train_image_size)
matches = matcher.match(query_descriptors, train_descriptors)

disk = cv2.DISK.create("disk.onnx")
index = cv2.ANNIndex.create(descriptor_dimension)
```

Only the class signatures above were introspected in the native wrapper. Model inference was tested explicitly through DNN, below. Native end-to-end matching and DISK model inference are not claimed as verified. The inspected native ALIKED implementation ignores the mask argument shown in the example, so that call cannot enforce static-background selection. The implemented stabilization adapter explicitly filters keypoints outside a whole-structure box. It also uses DNN directly because LightGlue's native wrapper lacks an explicit engine parameter in this wheel.

```python
net = cv2.dnn.readNetFromONNX(model_path, cv2.dnn.ENGINE_NEW)
net.setInput(input_blob, input_name)
outputs = net.forward(net.getUnconnectedOutLayersNames())
```

The committed probe executed forward passes for ALIKED, ALIKED LightGlue and OpenCV Zoo YOLOX with explicit `ENGINE_NEW`. ALIKED uses `image`; LightGlue uses `kpts0`, `kpts1`, `desc0`, `desc1` with normalized keypoints; output names and dimensions are in the probe JSON. Random inputs establish operator compatibility, not detector accuracy or stabilization quality.

## Model selection and licensing

- ALIKED/LightGlue exports were selected from the [official OpenCV extra test manifest](https://github.com/opencv/opencv_extra/blob/5.x/testdata/dnn/download_models.py). Downloaded files match that manifest's SHA-1 values; their SHA-256 and byte counts are in `eval/results/model_downloads.json`.
- [ALIKED upstream](https://github.com/Shiaoming/ALIKED/blob/main/LICENSE) is BSD-3-Clause; [LightGlue upstream](https://github.com/cvg/LightGlue/blob/main/LICENSE) is Apache-2.0. The export repository's root LICENSE URL returned not found. The ONNX export redistribution license therefore remains unresolved; do not bundle these weights in the public repo or cloud image until that is resolved. Local compatibility experiments are kept separate from redistribution.
- [OpenCV Zoo YOLOX](https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox) provides a ready ONNX export under Apache-2.0. Reuse it rather than introducing a PyTorch export dependency. Its forward pass works in `ENGINE_NEW`; a real vehicle detection sample is still required in P2.
- No PyTorch or ONNX Runtime API was used for inference. Every tested model explicitly selects ENGINE_NEW.

License notices are retained under `docs/model-licenses/`. Weights are ignored by Git.

## Optional VLM enrollment

The official sample is [`samples/dnn/vlm_inference.py`](https://github.com/opencv/opencv/blob/3f12ad88abb751701c3f48464652283710d06cdb/samples/dnn/vlm_inference.py). It uses a SigLIP vision encoder, embedding network, Gemma language model and OpenCV-format tokenizer configuration. The current source sample uses `ENGINE_OPENCV`, which is absent in this installed wheel; check against `ENGINE_NEW` before adapting it.

```sh
python samples/dnn/vlm_inference.py \
  --siglip=siglip/onnx/vision_model.onnx \
  --embedding=embedding/onnx/embedding.onnx \
  --gemma=gemma/onnx/gemma2_3b.onnx \
  --tokenizer_path=opencv-tokenizer-config.json \
  --input=bridge.jpg --prompt='cap en'
```

The [sample-linked export inventory](https://huggingface.co/nklskyoy/paligemma2-3b-pt-224-onnx/tree/main) is recorded in `eval/results/vlm_inventory.json`, including external tensor files. Download and CPU timing were deferred because of model footprint and the core build priority. No inference speed or enrollment capability is claimed. VLM remains disabled, and the build continues without it as permitted by the cut list.

## Open boundaries

COOL execution requires a subscribed AWS AMI and real instance access. `scripts/verify_cool.py` rejects this local wheel. Background matching and shake cancellation now execute on a synthetic scene in `eval/stabilization.py`. Vehicle detection on a real clip, real handheld validation, and export redistribution rights remain pending P2 gates. These do not block the pure numerical P1 slice.

Signal processing follows the pinned [SciPy Welch API](https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.signal.welch.html). No upstream model accuracy or bridge statistics are reused as project evaluation results.
