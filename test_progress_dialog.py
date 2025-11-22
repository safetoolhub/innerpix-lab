
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
