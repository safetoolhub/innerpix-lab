#!/usr/bin/env python3
"""
Test script for CustomSpinBox widget.
Run from project root: python dev-tools/test_custom_spinbox.py
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QSpinBox, QLabel
    from PyQt6.QtCore import QTimer
    from ui.styles.design_system import DesignSystem
    from ui.screens.custom_spinbox import CustomSpinBox
except ImportError as e:
    print("Error: PyQt6 not found. Please activate the virtual environment:")
    print("  source .venv/bin/activate")
    print("Then run: python dev-tools/test_custom_spinbox.py")
    sys.exit(1)

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
    
    # Auto-close after 2 seconds for testing purposes
    QTimer.singleShot(2000, app.quit)
    
    sys.exit(app.exec())
