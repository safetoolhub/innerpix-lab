#!/usr/bin/env python3
"""
Test script for CustomSpinBox widget.
Run from project root: python scripts/test_custom_spinbox.py
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QSpinBox, QLabel
from ui.styles.design_system import DesignSystem
from ui.widgets.custom_spinbox import CustomSpinBox

class TestDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test SpinBox")
        self.resize(400, 300)
        self.setStyleSheet(DesignSystem.get_stylesheet())

        layout = QVBoxLayout(self)

        label = QLabel("CustomSpinBox (qtawesome icons):")
        layout.addWidget(label)

        spin = CustomSpinBox()
        layout.addWidget(spin)

        label2 = QLabel("Another CustomSpinBox:")
        layout.addWidget(label2)

        spin2 = CustomSpinBox()
        spin2.setRange(0, 100)
        spin2.setValue(50)
        layout.addWidget(spin2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = TestDialog()
    dlg.show()
    sys.exit(app.exec())
