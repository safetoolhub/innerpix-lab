#!/usr/bin/env python3
"""
Test script for SimilarFilesProgressDialog.
Run from project root: python scripts/test_progress_dialog.py
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ui.dialogs.similar_files_progress_dialog import SimilarFilesProgressDialog

def test_dialog():
    app = QApplication(sys.argv)

    dialog = SimilarFilesProgressDialog(total_files=150)
    dialog.show()

    # Simulate progress
    progress = 0

    def update():
        nonlocal progress
        progress += 1
        if progress <= 150:
            dialog.update_progress(progress, 150, f"Analizando archivo_{progress}.jpg\n/path/to/archivo_{progress}.jpg")
        else:
            timer.stop()
            dialog.status_text.setText("Análisis completado")
            dialog.cancel_button.setEnabled(False)
            QTimer.singleShot(1000, app.quit)

    timer = QTimer()
    timer.timeout.connect(update)
    timer.start(10)  # Fast update

    sys.exit(app.exec())

if __name__ == "__main__":
    test_dialog()
