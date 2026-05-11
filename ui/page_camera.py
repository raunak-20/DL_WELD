"""
ui/page_camera.py
─────────────────
Camera preview page.

Key behaviour:
  • When a photo is captured it is CROPPED to the exact specimen bounding box
    before the approval dialog is shown.  The operator confirms the cropped image.
  • On approval → proceed_analysis signal emitted with the scan dict.
"""

import os
import datetime

from PyQt5.QtCore    import Qt, QTimer, pyqtSignal
from PyQt5.QtGui     import QPixmap, QImage, QPainter, QColor, QPen, QBrush, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QDialog,
)

from utils.constants import (
    C_NAVY, C_NAVY_MID, C_GOLD, C_BG, C_WHITE, C_BORDER,
    C_TEXT_MID, C_GREEN, C_RED, C_AMBER, SCANS_DIR,
    load_scans, save_scans, now_str,
)
from utils.widgets  import ToastWidget, make_btn_primary, make_btn_secondary
from services       import CameraService


class CameraPreviewPage(QWidget):
    proceed_analysis = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scan           = {}
        self._mode          = 'photo'
        self._recording     = False
        self.current_frame  = None
        self._camera_svc    = CameraService()
        self._grab_timer    = QTimer(self)
        self._grab_timer.timeout.connect(self._grab_frame)
        self._bbox          = None   # (bx, by, bw, bh) in viewport px

        self.setStyleSheet(f'background: {C_BG};')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.guide_panel = self._build_guide()
        self.cam_area    = self._build_cam_area()
        self.cam_area.setVisible(False)
        root.addWidget(self.guide_panel)
        root.addWidget(self.cam_area, stretch=1)

        self.toast = ToastWidget(self)

    # ── Guide panel ───────────────────────────────────────────────────────────

    def _build_guide(self):
        w = QWidget()
        w.setStyleSheet(f'background: {C_WHITE};')
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        title = QLabel('Alignment Guide — Read Before Scanning')
        title.setStyleSheet(f'color:{C_NAVY};font-size:16px;font-weight:800;border:none;background:transparent;')
        lay.addWidget(title)

        cols = QHBoxLayout(); cols.setSpacing(16)
        for heading, items, bg, border, hdr_col in [
            ("Do's", ['Place specimen on a plain white / light background',
                      'Ensure even, diffused lighting across the weld bead',
                      'Align weld bead within the yellow bounding box',
                      'Keep camera steady and perpendicular to specimen'],
             '#F0FDF4', '#BBF7D0', C_GREEN),
            ("Don'ts", ['Avoid harsh directional or shadow-casting light',
                        "Don't include background clutter or other objects",
                        "Don't tilt the camera at an angle",
                        "Don't move specimen during capture"],
             '#FEF2F2', '#FECACA', C_RED),
        ]:
            txt = '#166534' if hdr_col == C_GREEN else '#991B1B'
            col = QWidget()
            col.setStyleSheet(f'background:{bg};border-radius:10px;border:1px solid {border};')
            cl = QVBoxLayout(col); cl.setContentsMargins(16,12,16,14); cl.setSpacing(8)
            hdr = QLabel(('✓  ' if hdr_col==C_GREEN else '✗  ')+heading)
            hdr.setStyleSheet(f'color:{hdr_col};font-size:14px;font-weight:700;border:none;background:transparent;')
            cl.addWidget(hdr)
            for item in items:
                lbl = QLabel(f'• {item}')
                lbl.setStyleSheet(f'color:{txt};font-size:12px;border:none;background:transparent;')
                lbl.setWordWrap(True); cl.addWidget(lbl)
            cols.addWidget(col)
        lay.addLayout(cols)

        btn = make_btn_primary('Got it — Open Camera')
        btn.setFixedWidth(220); btn.clicked.connect(self._open_camera)
        lay.addWidget(btn, alignment=Qt.AlignCenter)
        return w

    # ── Camera area ───────────────────────────────────────────────────────────

    def _build_cam_area(self):
        w = QWidget(); w.setStyleSheet(f'background:{C_BG};')
        lay = QVBoxLayout(w); lay.setContentsMargins(16,16,16,16); lay.setSpacing(12)

        self.viewport = QLabel()
        self.viewport.setAlignment(Qt.AlignCenter)
        self.viewport.setStyleSheet('background:#111;border-radius:12px;')
        self.viewport.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(self.viewport, stretch=1)

        ctrl = QWidget(); ctrl.setObjectName('ctrlBar')
        ctrl.setStyleSheet(
            f'QWidget#ctrlBar{{background:{C_WHITE};border-radius:12px;border:1px solid {C_BORDER};}}'
            'QWidget#ctrlBar QLabel{border:none;background:transparent;}'
        )
        cl = QHBoxLayout(ctrl); cl.setContentsMargins(16,10,16,10); cl.setSpacing(12)

        self._active_style = (
            f'QPushButton{{background:{C_NAVY};color:#fff;border:1px solid {C_NAVY};'
            'border-radius:8px;padding:8px 18px;font-size:13px;font-weight:600;}}'
            f'QPushButton:hover{{background:{C_NAVY_MID};}}'
        )
        self._inactive_style = (
            f'QPushButton{{background:#F9FAFB;color:{C_TEXT_MID};border:1px solid {C_BORDER};'
            'border-radius:8px;padding:8px 18px;font-size:13px;font-weight:600;}}'
            'QPushButton:hover{background:#F3F4F6;}'
        )
        self.photo_btn = QPushButton('📷  Photo')
        self.photo_btn.setCursor(Qt.PointingHandCursor)
        self.photo_btn.setStyleSheet(self._active_style)
        self.photo_btn.clicked.connect(lambda: self._set_mode('photo'))

        self.video_btn = QPushButton('🎥  Video')
        self.video_btn.setCursor(Qt.PointingHandCursor)
        self.video_btn.setStyleSheet(self._inactive_style)
        self.video_btn.clicked.connect(lambda: self._set_mode('video'))

        cl.addWidget(self.photo_btn); cl.addWidget(self.video_btn); cl.addStretch()

        self.upload_btn = QPushButton('📁  Upload')
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.setStyleSheet(self._inactive_style)
        self.upload_btn.clicked.connect(self._upload_image)
        cl.addWidget(self.upload_btn)

        self.capture_btn = make_btn_primary('📸  Capture Photo')
        self.capture_btn.setEnabled(False); self.capture_btn.setFixedWidth(200)
        self.capture_btn.clicked.connect(self._capture)
        cl.addWidget(self.capture_btn)
        lay.addWidget(ctrl)
        return w

    # ── Camera control ────────────────────────────────────────────────────────

    def set_scan(self, scan: dict):
        self.scan = scan

    def _open_camera(self):
        self.guide_panel.setVisible(False)
        self.cam_area.setVisible(True)
        if self._camera_svc.open_camera():
            self.capture_btn.setEnabled(True)
            self._grab_timer.start(33)
        else:
            msg = 'Camera not detected' if self._camera_svc.available else 'OpenCV not installed'
            self.toast.show_toast(msg, '⚠', C_AMBER, 5000)
            self._show_placeholder()

    def _show_placeholder(self):
        pix = QPixmap(640, 480); pix.fill(QColor('#1a1a1a'))
        p = QPainter(pix); p.setPen(QPen(QColor('#555'))); p.setFont(QFont('Arial', 14))
        p.drawText(pix.rect(), Qt.AlignCenter, 'Camera Preview\n(Camera unavailable)'); p.end()
        self.viewport.setPixmap(pix)

    def _set_mode(self, mode: str):
        self._mode = mode
        self.photo_btn.setStyleSheet(self._active_style if mode=='photo' else self._inactive_style)
        self.video_btn.setStyleSheet(self._active_style if mode=='video' else self._inactive_style)
        self.capture_btn.setText(
            '📸  Capture Photo' if mode=='photo'
            else ('⏹  Stop Recording' if self._recording else '⏺  Start Recording')
        )

    # ── Frame grab ────────────────────────────────────────────────────────────

    def _grab_frame(self):
        frame = self._camera_svc.read_frame()
        if frame is None: return
        self.current_frame = frame
        vw = max(self.viewport.width(), 320)
        vh = max(self.viewport.height(), 240)
        pix = self._to_pixmap(frame, vw, vh)
        bbox = self._compute_bbox(vw, vh)
        self._bbox = bbox
        self._draw_overlay(pix, vw, vh, bbox)
        self.viewport.setPixmap(pix)

    def _to_pixmap(self, frame, tw, th):
        r = self._camera_svc.frame_to_rgb_bytes(frame)
        if r is None: return QPixmap(tw, th)
        data, w, h, bpl = r
        return QPixmap.fromImage(
            QImage(data, w, h, bpl, QImage.Format_RGB888)
        ).scaled(tw, th, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

    def _compute_bbox(self, vw, vh):
        spec_w = max(self.scan.get('width', 300), 1)
        spec_h = max(self.scan.get('height', 300), 1)
        bw = int(vw * 0.65)
        bh = min(int(bw * spec_h / spec_w), int(vh * 0.80))
        return (vw-bw)//2, (vh-bh)//2, bw, bh

    def _draw_overlay(self, pix, vw, vh, bbox):
        bx, by, bw, bh = bbox
        p = QPainter(pix); p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(0,0,0,100))); p.setPen(Qt.NoPen)
        for rx,ry,rw,rh in [(0,0,vw,by),(0,by+bh,vw,vh-by-bh),(0,by,bx,bh),(bx+bw,by,vw-bx-bw,bh)]:
            p.drawRect(rx,ry,rw,rh)
        p.setPen(QPen(QColor(C_GOLD),2,Qt.DashLine)); p.setBrush(Qt.NoBrush)
        p.drawRect(bx,by,bw,bh)
        cl=16; p.setPen(QPen(QColor(C_GOLD),3,Qt.SolidLine))
        for cx,cy,dx,dy in [(bx,by,1,1),(bx+bw,by,-1,1),(bx,by+bh,1,-1),(bx+bw,by+bh,-1,-1)]:
            p.drawLine(cx,cy,cx+dx*cl,cy); p.drawLine(cx,cy,cx,cy+dy*cl)
        p.setPen(QPen(QColor(C_GOLD))); p.setFont(QFont('Arial',9,QFont.Bold))
        p.drawText(bx+6, by-6, 'Align specimen here')
        p.end()

    # ── Capture → crop → approve ──────────────────────────────────────────────

    def _capture(self):
        if self._mode == 'video':
            self._toggle_recording(); return
        if self.current_frame is None:
            self.toast.show_toast('No frame available','⚠',C_AMBER); return

        ts   = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        sid  = self.scan.get('sample_id', 'scan').replace('/', '-')
        path = os.path.join(SCANS_DIR, f'{sid}_{ts}.jpg')
        if not self._camera_svc.save_frame(self.current_frame, path):
            self.toast.show_toast('Failed to save frame','⚠',C_AMBER); return

        cropped_path = self._crop_to_bbox(path)
        self._stop_camera()

        dlg = PhotoApprovalDialog(cropped_path, self)
        if dlg.exec_() == QDialog.Accepted:
            entry = {**self.scan, 'status':'captured', 'photo':cropped_path, 'scan_date':now_str()}
            scans = load_scans(); scans.append(entry); save_scans(scans)
            self.toast.show_toast('Photo saved — proceeding to analysis','✓',C_GREEN)
            QTimer.singleShot(700, lambda: self.proceed_analysis.emit(entry))
        else:
            for f in [path, cropped_path]:
                try: os.remove(f)
                except: pass
            self._open_camera()

    def _upload_image(self):
        from PyQt5.QtWidgets import QFileDialog
        import shutil
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.avif)")
        if path:
            self._stop_camera()
            
            # Copy to scans dir
            ts   = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            sid  = self.scan.get('sample_id', 'scan').replace('/', '-')
            ext = os.path.splitext(path)[1]
            dest_path = os.path.join(SCANS_DIR, f'{sid}_{ts}{ext}')
            shutil.copy2(path, dest_path)

            dlg = PhotoApprovalDialog(dest_path, self)
            if dlg.exec_() == QDialog.Accepted:
                entry = {**self.scan, 'status':'captured', 'photo':dest_path, 'scan_date':now_str()}
                scans = load_scans(); scans.append(entry); save_scans(scans)
                self.toast.show_toast('Photo uploaded — proceeding to analysis','✓',C_GREEN)
                QTimer.singleShot(700, lambda: self.proceed_analysis.emit(entry))
            else:
                try: os.remove(dest_path)
                except: pass
                self._open_camera()

    def _crop_to_bbox(self, full_path: str) -> str:
        """Scale the viewport bbox back to original frame resolution and crop."""
        try:
            import cv2
            frame = cv2.imread(full_path)
            if frame is None or self._bbox is None: return full_path
            fh, fw = frame.shape[:2]
            vw = max(self.viewport.width(), 320)
            vh = max(self.viewport.height(), 240)
            bx, by, bw, bh = self._bbox
            x1 = max(0,  int(bx       * fw / vw))
            y1 = max(0,  int(by       * fh / vh))
            x2 = min(fw, int((bx+bw)  * fw / vw))
            y2 = min(fh, int((by+bh)  * fh / vh))
            cropped = frame[y1:y2, x1:x2]
            base, ext = os.path.splitext(full_path)
            out = f'{base}_cropped{ext}'
            cv2.imwrite(out, cropped)
            return out
        except Exception as e:
            print(f'[CameraPage] crop error: {e}')
            return full_path

    def _toggle_recording(self):
        self._recording = not self._recording
        self.capture_btn.setText('⏹  Stop Recording' if self._recording else '⏺  Start Recording')
        if not self._recording:
            self.toast.show_toast('Recording stopped','✓',C_NAVY)

    def stop_camera(self):
        self._stop_camera()
        self.guide_panel.setVisible(True)
        self.cam_area.setVisible(False)
        self.capture_btn.setEnabled(False)
        self.current_frame = None

    def _stop_camera(self):
        if self._grab_timer.isActive(): self._grab_timer.stop()
        self._camera_svc.release()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.toast._reposition()


# ── Photo approval dialog ─────────────────────────────────────────────────────

class PhotoApprovalDialog(QDialog):
    def __init__(self, photo_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Approve Captured Photo')
        self.setModal(True); self.setMinimumSize(520, 460)
        self.setStyleSheet(f'background:{C_BG};')
        v = QVBoxLayout(self); v.setContentsMargins(24,24,24,24); v.setSpacing(16)

        t = QLabel('Review Captured Photo')
        t.setStyleSheet(f'color:{C_NAVY};font-size:18px;font-weight:800;border:none;background:transparent;')
        v.addWidget(t)

        img = QLabel()
        pm = QPixmap(photo_path)
        if not pm.isNull(): pm = pm.scaled(460,320,Qt.KeepAspectRatio,Qt.SmoothTransformation)
        img.setPixmap(pm); img.setAlignment(Qt.AlignCenter)
        img.setStyleSheet('background:#111;border-radius:10px;border:none;padding:4px;')
        v.addWidget(img)

        note = QLabel('Image is cropped to the specimen bounding box. Approve to proceed to analysis.')
        note.setStyleSheet(f'color:{C_TEXT_MID};font-size:12px;border:none;background:transparent;')
        note.setWordWrap(True); v.addWidget(note)

        row = QHBoxLayout(); row.setSpacing(12)
        r = make_btn_secondary('↺  Retake'); r.clicked.connect(self.reject)
        a = make_btn_primary('✓  Approve & Proceed to Analysis'); a.clicked.connect(self.accept)
        row.addWidget(r); row.addWidget(a); v.addLayout(row)
