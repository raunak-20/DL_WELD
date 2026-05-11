"""
services/camera_service.py
──────────────────────────
Handles all camera capture operations via OpenCV.
The UI never touches cv2 directly — it calls this service.

To swap cameras (USB index, CSI via V4L2, IP stream):
  → change open_camera()'s VideoCapture argument only here.
"""

import sys

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


class CameraService:
    """
    Thin wrapper around OpenCV VideoCapture.

    Usage:
        svc = CameraService()
        ok  = svc.open_camera()       # True if camera opened
        frame = svc.read_frame()      # numpy array or None
        svc.release()
    """

    def __init__(self):
        self._cap = None

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        """True if OpenCV is installed."""
        return _CV2_AVAILABLE

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def open_camera(self, index: int = 0) -> bool:
        """
        Open the camera at the given device index.
        Returns True on success.

        Platform notes:
          • Linux / RPi  → index 0 (USB) or set index via bcm2835-v4l2
          • Windows      → uses DirectShow backend for lower latency
          • macOS        → standard AVFoundation via index 0
        """
        if not _CV2_AVAILABLE:
            return False
        if sys.platform == 'win32':
            self._cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        else:
            self._cap = cv2.VideoCapture(index)
        return self._cap.isOpened()

    def read_frame(self):
        """
        Read the next frame from the camera.
        Returns a BGR numpy array, or None if unavailable.
        """
        if not self.is_open:
            return None
        ret, frame = self._cap.read()
        return frame if ret else None

    def save_frame(self, frame, path: str) -> bool:
        """Save a captured BGR frame as a JPEG file. Returns True on success."""
        if not _CV2_AVAILABLE or frame is None:
            return False
        return cv2.imwrite(path, frame)

    def release(self):
        """Release the camera resource."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    # ── Qt helpers ────────────────────────────────────────────────────────────

    def frame_to_rgb_bytes(self, frame):
        """
        Convert a BGR OpenCV frame to (data, width, height, bytes_per_line).
        The caller converts this to QImage / QPixmap.
        Returns None if cv2 not available or frame is None.
        """
        if not _CV2_AVAILABLE or frame is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        return rgb.data, w, h, ch * w
