"""
controller/app_controller.py
────────────────────────────
Orchestrates navigation and data flow between all pages and services.

New in this version:
  • analysis page's report_ready signal → report viewer
  • history page's scan_selected signal → report viewer (re-generate or cached)
  • Services (AIService, ReportService) injected into analysis page
"""

import uuid

from PyQt5.QtCore    import QObject
from PyQt5.QtWidgets import QStackedWidget

from utils.constants import load_scans, save_scans, now_str, C_GREEN, C_GOLD
from ui              import (
    TopBar, IndexPage, NewScanPage,
    CameraPreviewPage, ScanHistoryPage, AnalysisPage,
)
from ui.page_report_viewer import ReportViewerPage
from services              import AIService, ReportService


class AppController(QObject):
    def __init__(self, stack: QStackedWidget, topbar: TopBar, parent=None):
        super().__init__(parent)
        self.stack  = stack
        self.topbar = topbar

        # ── Pages ─────────────────────────────────────────────────────────────
        self.page_index    = IndexPage()
        self.page_scan     = NewScanPage()
        self.page_camera   = CameraPreviewPage()
        self.page_history  = ScanHistoryPage()
        self.page_analysis = AnalysisPage()
        self.page_report   = ReportViewerPage()

        for page in (self.page_index, self.page_scan, self.page_camera,
                     self.page_history, self.page_analysis, self.page_report):
            self.stack.addWidget(page)

        # ── Services ──────────────────────────────────────────────────────────
        self.ai_svc     = AIService()
        self.report_svc = ReportService()

        # Inject services into analysis page
        self.page_analysis.set_services(self.ai_svc, self.report_svc)

        # ── Signals ───────────────────────────────────────────────────────────
        self.page_index.navigate_new_scan.connect(self.show_new_scan)
        self.page_index.navigate_history.connect(self.show_history)
        self.page_scan.start_camera.connect(self.start_camera)
        self.page_camera.proceed_analysis.connect(self.show_analysis)
        self.page_analysis.report_ready.connect(self.show_report)
        self.page_history.scan_selected.connect(self.show_report_for_scan)
        self.page_report.back_to_history.connect(self.show_history)
        self.page_report.new_scan.connect(self.show_new_scan)
        self.topbar.back_requested.connect(self.on_back)

        self.stack.setCurrentWidget(self.page_index)

    # ── Navigation ────────────────────────────────────────────────────────────

    def show_new_scan(self):
        self.page_scan.reset_form()
        self.topbar.set_back_visible(True)
        self.topbar.set_title('New Scan', 'Step 1 of 4 — Identification')
        self.stack.setCurrentWidget(self.page_scan)

    def show_history(self):
        self.topbar.set_back_visible(True)
        self.topbar.set_title('Scan History', 'All recorded inspections')
        self.page_history.refresh()
        self.stack.setCurrentWidget(self.page_history)

    def start_camera(self, data: dict):
        entry = {
            **data,
            'status':    'pending',
            'id':        str(uuid.uuid4())[:8],
            'scan_date': data.get('scan_date') or now_str(),
        }
        scans = load_scans(); scans.append(entry); save_scans(scans)
        self.page_camera.set_scan(entry)
        self.topbar.set_back_visible(True)
        self.topbar.set_title(
            'Camera Preview',
            f"Scan #{data.get('scan_number')} — {data.get('sample_id','')}",
        )
        self.topbar.set_status('Camera Active', C_GOLD)
        self.stack.setCurrentWidget(self.page_camera)

    def show_analysis(self, sc: dict):
        self.page_analysis.set_scan(sc)
        self.topbar.set_title('Analysis', f"Sample {sc.get('sample_id','')}")
        self.topbar.set_status('Ready for analysis', C_GOLD)
        self.stack.setCurrentWidget(self.page_analysis)

    def show_report(self, sc: dict, pdf_path: str):
        """Called after report generation — navigate to the viewer."""
        self.page_report.load_report(sc, pdf_path)
        self.topbar.set_title('Inspection Report', sc.get('report_id',''))
        self.topbar.set_status('Report Ready', C_GREEN)
        self.stack.setCurrentWidget(self.page_report)

    def show_report_for_scan(self, sc: dict):
        """
        Called when a history card is tapped.
        If the scan already has a saved report path, open it directly.
        Otherwise navigate to the analysis page so the user can run analysis first.
        """
        saved_report = sc.get('report_path', '')
        import os
        if saved_report and os.path.exists(saved_report):
            self.show_report(sc, saved_report)
        else:
            # Go to analysis — user runs analysis then generates report from there
            self.page_analysis.set_scan(sc)
            self.topbar.set_back_visible(True)
            self.topbar.set_title('Analysis', f"Sample {sc.get('sample_id','')}")
            self.topbar.set_status('Ready for analysis', C_GOLD)
            self.stack.setCurrentWidget(self.page_analysis)

    def on_back(self):
        cur = self.stack.currentWidget()
        if cur == self.page_scan:
            self._go_home()
        elif cur == self.page_camera:
            self.page_camera.stop_camera()
            self.topbar.set_status('System Ready', C_GREEN)
            self.topbar.set_title('New Scan', 'Step 1 of 4 — Identification')
            self.stack.setCurrentWidget(self.page_scan)
        elif cur == self.page_analysis:
            self.page_camera.stop_camera()
            self._go_home()
        elif cur == self.page_report:
            self.show_history()
        elif cur == self.page_history:
            self._go_home()
        else:
            self._go_home()

    def _go_home(self):
        self.topbar.set_back_visible(False)
        self.topbar.set_title('Weld Inspector', 'AI-Powered Visual Inspection System')
        self.topbar.set_status('System Ready', C_GREEN)
        self.stack.setCurrentWidget(self.page_index)

    def cleanup(self):
        self.page_camera.stop_camera()
