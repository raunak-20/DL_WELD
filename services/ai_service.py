"""
services/ai_service.py
──────────────────────
AI / ML inference service for weld defect detection.

Current status: PLACEHOLDER — returns simulated results.

To integrate a model:
  1. Place model file at:  <project_root>/model/best-2.pt or best.onnx
  2. Set MODEL_PATH below (or pass it to AIService.__init__)
  3. For .pt models install ultralytics + torch, for .onnx install onnxruntime.

The rest of the application (controller, UI) calls only run_inference()
and reads DetectionResult objects — no other changes needed.
"""

import os
import sys
import random
import datetime
from dataclasses import dataclass, field
from typing import List, Optional

# ─── Model path ───────────────────────────────────────────────────────────────
# On Raspberry Pi the model lives at:
#   /home/pi/Desktop/Weld-Inspection/model/end2end.onnx
# On other systems set the env var  WELD_MODEL_PATH  or change this default.
def _resolve_default_model() -> str:
    model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'model')
    candidates = [
        'best-2.pt',
        'best.pt',
        'best.onnx',
        'end2end.onnx',
    ]
    for name in candidates:
        candidate = os.path.join(model_dir, name)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(model_dir, 'best.onnx')


_ENV_MODEL = os.environ.get('WELD_MODEL_PATH')
_DEFAULT_MODEL = _ENV_MODEL or _resolve_default_model()

try:
    import onnxruntime as ort
    _ORT_AVAILABLE = True
except ImportError:
    _ORT_AVAILABLE = False


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    label: str          # e.g. "porosity", "crack", "undercut"
    label_id: int = 0


@dataclass
class DetectionResult:
    boxes: List[BoundingBox]   = field(default_factory=list)
    inference_time_ms: float   = 0.0
    frame_width: int           = 0
    frame_height: int          = 0
    is_simulated: bool         = True   # False once real model is loaded
    timestamp: str             = ''

    @property
    def defect_count(self) -> int:
        return len(self.boxes)

    @property
    def has_defects(self) -> bool:
        return bool(self.boxes)

    @property
    def severity(self) -> str:
        n = self.defect_count
        if n == 0:  return 'Pass'
        if n <= 2:  return 'Minor'
        if n <= 5:  return 'Moderate'
        return 'Severe'


# ─── Service ──────────────────────────────────────────────────────────────────

class AIService:
    """
    Weld defect detection service.

    Loads an ONNX model on Linux/RPi if onnxruntime is installed.
    Falls back to a deterministic simulation on other platforms.
    """

    # Input resolution expected by the model
    INPUT_W = 640
    INPUT_H = 640

    # Confidence threshold — detections below this are discarded
    CONF_THRESHOLD = 0.45

    # Exact classes from the custom ONNX model metadata
    CLASS_NAMES = [
        'crack', 'excess_reinforcement', 'porosity', 'spatters'
    ]

    def __init__(self, model_path: str = _DEFAULT_MODEL):
        self._model_path = model_path
        self._session = None
        self._yolo = None
        self._backend = None
        self._class_names = list(self.CLASS_NAMES)
        self._load_model()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _load_model(self):
        """Load .onnx or .pt model; silently fall back to simulation."""
        self._session = None
        self._yolo = None
        self._backend = None

        if not os.path.exists(self._model_path):
            with open('ai_error.log', 'a') as f:
                f.write(f'Model path not found: {self._model_path}\n')
            return

        ext = os.path.splitext(self._model_path)[1].lower()
        if ext == '.onnx':
            self._load_onnx_model()
        elif ext in ('.pt', '.pth'):
            self._load_pt_model()
        else:
            with open('ai_error.log', 'a') as f:
                f.write(f'Unsupported model extension: {ext}\n')

    def _load_onnx_model(self):
        if not _ORT_AVAILABLE:
            with open('ai_error.log', 'a') as f:
                f.write('ORT NOT AVAILABLE\n')
            return
        try:
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self._session = ort.InferenceSession(self._model_path, providers=providers)
            self._backend = 'onnx'
        except Exception as e:
            print(f'[AIService] Could not load ONNX model: {e}')
            with open('ai_error.log', 'a') as f:
                f.write(f'Could not load ONNX model: {e}\n')
            self._session = None

    def _load_pt_model(self):
        try:
            from ultralytics import YOLO
        except ImportError:
            with open('ai_error.log', 'a') as f:
                f.write('Ultralytics not available for .pt model\n')
            return
        try:
            self._yolo = YOLO(self._model_path)
            self._backend = 'ultralytics'
            if hasattr(self._yolo, 'names') and self._yolo.names:
                self._class_names = self._yolo.names
        except Exception as e:
            print(f'[AIService] Could not load .pt model: {e}')
            with open('ai_error.log', 'a') as f:
                f.write(f'Could not load .pt model: {e}\n')
            self._yolo = None

    @property
    def model_loaded(self) -> bool:
        return self._backend is not None

    # ── Public API ────────────────────────────────────────────────────────────

    def run_inference(self, frame) -> DetectionResult:
        """
        Run defect detection on a BGR OpenCV frame.
        Returns a DetectionResult.  Always succeeds (falls back to simulation).
        """
        ts = datetime.datetime.now().isoformat(timespec='milliseconds')
        if frame is None:
            return DetectionResult(timestamp=ts)

        h, w = frame.shape[:2]

        if self.model_loaded:
            if self._backend == 'onnx':
                return self._real_inference_onnx(frame, w, h, ts)
            if self._backend == 'ultralytics':
                return self._real_inference_pt(frame, w, h, ts)
        return self._simulated_inference(w, h, ts)

    # ── Real inference (ONNX) ─────────────────────────────────────────────────

    # def _real_inference(self, frame, w: int, h: int, ts: str) -> DetectionResult:
        """
        Preprocess → infer → postprocess using the loaded ONNX session.

        ┌─ TODO when you have the real model ─────────────────────────────────┐
        │  Adjust the input tensor name (self._session.get_inputs()[0].name)  │
        """
    def _real_inference_onnx(self, frame, w: int, h: int, ts: str) -> DetectionResult:
        try:
            import cv2
            import numpy as np
            import time

            t0 = time.perf_counter()

            # ── Preprocess with Letterbox to maintain aspect ratio ──────
            shape = frame.shape[:2]  # h, w
            r = min(self.INPUT_W / shape[1], self.INPUT_H / shape[0])
            new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
            dw, dh = self.INPUT_W - new_unpad[0], self.INPUT_H - new_unpad[1]
            dw /= 2  # pad both sides
            dh /= 2

            if shape[::-1] != new_unpad:
                resized = cv2.resize(frame, new_unpad, interpolation=cv2.INTER_LINEAR)
            else:
                resized = frame.copy()

            top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
            left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
            resized = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))

            resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            blob = resized.astype('float32') / 255.0
            blob = blob.transpose(2, 0, 1)[None]  # NCHW

            input_name = self._session.get_inputs()[0].name
            outputs = self._session.run(None, {input_name: blob})

            # ── YOLOv8 output parsing ──────────────────────────
            output = outputs[0]
            output = np.squeeze(output)      # (84, 8400)
            output = output.T               # (8400, 84)

            boxes_nms = []
            confidences = []
            class_ids = []

            for row in output:
                cx, cy, bw, bh = row[:4]
                class_scores = row[4:]

                cls_id = int(np.argmax(class_scores))
                conf = float(class_scores[cls_id])

                if conf < self.CONF_THRESHOLD:
                    continue

                # Convert (cx,cy,w,h) → (x1,y1,w,h) for NMS
                x1 = cx - bw / 2
                y1 = cy - bh / 2
                boxes_nms.append([int(x1), int(y1), int(bw), int(bh)])
                confidences.append(float(conf))
                class_ids.append(cls_id)

            # Apply Non-Maximum Suppression (NMS) to remove overlapping boxes
            indices = cv2.dnn.NMSBoxes(boxes_nms, confidences, self.CONF_THRESHOLD, 0.45)

            boxes = []
            if len(indices) > 0:
                for i in indices.flatten():
                    x_min, y_min, bw, bh = boxes_nms[i]
                    x_max = x_min + bw
                    y_max = y_min + bh

                    # Unpad and scale back to original image size
                    x1 = (x_min - left) / r
                    y1 = (y_min - top) / r
                    x2 = (x_max - left) / r
                    y2 = (y_max - top) / r

                    cls_id = class_ids[i]
                    label = self._get_label(cls_id)

                    boxes.append(BoundingBox(
                        x1=float(x1),
                        y1=float(y1),
                        x2=float(x2),
                        y2=float(y2),
                        confidence=confidences[i],
                        label=label,
                        label_id=cls_id,
                    ))

            elapsed = (time.perf_counter() - t0) * 1000

            return DetectionResult(
                boxes=boxes,
                inference_time_ms=elapsed,
                frame_width=w,
                frame_height=h,
                is_simulated=False,
                timestamp=ts,
            )

        except Exception as e:
            print(f'[AIService] Inference error: {e}')
            import traceback
            with open('ai_error.log', 'a') as f: 
                f.write(f'Inference error: {e}\n')
                f.write(traceback.format_exc() + '\n')
            return self._simulated_inference(w, h, ts)

    # ── Real inference (.pt / Ultralytics) ────────────────────────────────────

    def _real_inference_pt(self, frame, w: int, h: int, ts: str) -> DetectionResult:
        try:
            import time
            import numpy as np

            t0 = time.perf_counter()
            results = self._yolo.predict(
                source=frame,
                imgsz=self.INPUT_W,
                conf=self.CONF_THRESHOLD,
                verbose=False,
            )
            boxes = []
            if results:
                result = results[0]
                if result.boxes is not None and len(result.boxes) > 0:
                    xyxy = result.boxes.xyxy.cpu().numpy()
                    if result.boxes.conf is None or result.boxes.cls is None:
                        raise ValueError(
                            'Model output missing confidence/class data. '
                            'This may indicate an incompatible or corrupted .pt model.'
                        )
                    confs = result.boxes.conf.cpu().numpy()
                    clss = result.boxes.cls.cpu().numpy()
                    for (x1, y1, x2, y2), conf, cls_id in zip(xyxy, confs, clss):
                        cls_id = int(cls_id)
                        boxes.append(BoundingBox(
                            x1=float(x1),
                            y1=float(y1),
                            x2=float(x2),
                            y2=float(y2),
                            confidence=float(conf),
                            label=self._get_label(cls_id),
                            label_id=cls_id,
                        ))

            elapsed = (time.perf_counter() - t0) * 1000
            return DetectionResult(
                boxes=boxes,
                inference_time_ms=elapsed,
                frame_width=w,
                frame_height=h,
                is_simulated=False,
                timestamp=ts,
            )
        except Exception as e:
            print(f'[AIService] .pt inference error: {e}')
            import traceback
            with open('ai_error.log', 'a') as f:
                f.write(f'.pt inference error: {e}\n')
                f.write(traceback.format_exc() + '\n')
            return self._simulated_inference(w, h, ts)

    def _get_label(self, cls_id: int) -> str:
        if isinstance(self._class_names, dict):
            return self._class_names.get(cls_id, 'defect')
        if isinstance(self._class_names, (list, tuple)) and cls_id < len(self._class_names):
            return self._class_names[cls_id]
        if cls_id < len(self.CLASS_NAMES):
            return self.CLASS_NAMES[cls_id]
        return 'defect'

    # ── Simulation (non-RPi / no model) ──────────────────────────────────────

    def _simulated_inference(self, w: int, h: int, ts: str) -> DetectionResult:
        """Return plausible-looking fake results for UI development."""
        rng   = random.Random(hash(ts) % 2**32)
        count = rng.randint(0, 3)
        boxes = []
        for _ in range(count):
            x1 = rng.uniform(0.15, 0.55) * w
            y1 = rng.uniform(0.15, 0.55) * h
            x2 = x1 + rng.uniform(30, 100)
            y2 = y1 + rng.uniform(20, 60)
            label = rng.choice(self.CLASS_NAMES[:4])
            boxes.append(BoundingBox(
                x1=x1, y1=y1, x2=min(x2, w), y2=min(y2, h),
                confidence=rng.uniform(0.55, 0.97),
                label=label,
            ))
        return DetectionResult(
            boxes=boxes, inference_time_ms=rng.uniform(18, 45),
            frame_width=w, frame_height=h,
            is_simulated=True, timestamp=ts,
        )
