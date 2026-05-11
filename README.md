# Weld Inspector — Modular PyQt5 Application

AI-powered weld defect inspection desktop app. Designed for **Raspberry Pi 3 B+** kiosk deployment and standard desktop development.

---

## Project Structure

```
weld_inspector/
│
├── main.py                        ← Entry point — run this
│
├── controller/
│   └── app_controller.py          ← Navigation + data flow between pages
│
├── ui/
│   ├── topbar.py                  ← Persistent top bar (back btn, title, status)
│   ├── page_index.py              ← Home screen
│   ├── page_new_scan.py           ← 4-step specimen details wizard
│   ├── page_camera.py             ← Live camera + capture + approval dialog
│   ├── page_history.py            ← Scrollable scan history list
│   └── page_analysis.py          ← ML results page (placeholder)
│
├── services/
│   ├── camera_service.py          ← All OpenCV camera operations
│   └── ai_service.py             ← RTMDet / ONNX inference (+ simulation fallback)
│
├── utils/
│   ├── constants.py               ← Palette, paths, storage helpers
│   └── widgets.py                 ← Reusable styled Qt widget factories
│
├── static/
│   ├── DSES-Logo.png              ← Primary logo (topbar + home hero)
│   └── DSES-Logo-2.png           ← Secondary logo (optional, swap in constants.py)
│
├── scans/                         ← Saved JPEG captures (auto-created)
└── scans.json                     ← Scan records store (auto-created)
```

---

## Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install pyqt5 opencv-python

# 3. Optional: AI inference (Linux / Raspberry Pi)
pip install onnxruntime            # CPU-only
# pip install onnxruntime-gpu      # if you have CUDA

# 4. Run
python3 main.py
```

---

## Swapping Logos

Open `utils/constants.py`:

```python
LOGO_PRIMARY   = os.path.join(STATIC_DIR, 'DSES-Logo.png')    # topbar + home
LOGO_SECONDARY = os.path.join(STATIC_DIR, 'DSES-Logo-2.png')  # ← put your file here
```

- **Topbar logo** — edit `ui/topbar.py`, change `LOGO_PRIMARY` → `LOGO_SECONDARY`
- **Home hero logo** — edit `ui/page_index.py` inside `_build_hero()`, same swap

---

## Adding the ML Model

1. Place model at `model/end2end.onnx` (or set env var `WELD_MODEL_PATH`)
2. Open `services/ai_service.py`
3. The service auto-loads on start; `_real_inference()` contains the ONNX call
4. Adjust input tensor name + output parsing to match your model format
5. Results flow: `AIService.run_inference(frame)` → `DetectionResult` → `page_analysis.set_result()`

---

## Making Changes

| What you want to change | File to edit |
|---|---|
| Page layout / UI | `ui/page_*.py` |
| Navigation / back logic | `controller/app_controller.py` |
| Camera (index, backend) | `services/camera_service.py` |
| ML model integration | `services/ai_service.py` |
| Colours / theme | `utils/constants.py` |
| Shared widgets / buttons | `utils/widgets.py` |
| Topbar appearance | `ui/topbar.py` |
| Window size / startup | `main.py` |

---

## Raspberry Pi Notes

- App auto-enters **full-screen** on Linux
- Camera: plug in USB webcam → index 0
- CSI camera: `sudo modprobe bcm2835-v4l2` then index 0
- Model path on Pi: `/home/pi/Desktop/Weld-Inspection/model/end2end.onnx`
  (set via `WELD_MODEL_PATH` env var or edit `services/ai_service.py`)
