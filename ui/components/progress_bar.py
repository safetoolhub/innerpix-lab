from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import QTimer

from ui import styles


def create_progress_group(window, parent_layout):
    """Crea el grupo de progreso y lo ancla al layout padre.

    Esta función replica la lógica previa que vivía en `ui.ui_helpers.create_progress_bar`.
    Se usa `window` para almacenar referencias a los widgets creados, manteniendo
    la API existente del resto de la aplicación.
    """
    window.progress_group = QGroupBox("📊 Progreso")
    progress_layout = QVBoxLayout(window.progress_group)

    window.progress_label = QLabel("Listo para procesar")
    window.progress_label.setStyleSheet(styles.STYLE_PROGRESS_LABEL)
    progress_layout.addWidget(window.progress_label)

    window.progress_bar = QProgressBar()
    window.progress_bar.setStyleSheet(styles.STYLE_PROGRESS_BAR)
    progress_layout.addWidget(window.progress_bar)

    window.progress_group.setVisible(False)
    parent_layout.addWidget(window.progress_group)


def show_progress(window, maximum, message="Procesando"):
    """Muestra la barra de progreso en modo indeterminado y actualiza la etiqueta.

    Mantiene la semántica anterior: `maximum` se ignora para operaciones de
    modificación de archivos y se fuerza un modo 'busy'.
    """
    try:
        window.progress_group.setVisible(True)
    except Exception:
        return

    try:
        window.progress_bar.setMaximum(0)
    except Exception:
        try:
            window.progress_bar.setMaximum(100)
            window.progress_bar.setValue(0)
        except Exception:
            pass

    try:
        window.progress_label.setText(message)
    except Exception:
        pass


def hide_progress(window):
    def _hide():
        try:
            window.progress_bar.setMaximum(100)
            window.progress_bar.setValue(0)
        except Exception:
            pass
        try:
            window.progress_group.setVisible(False)
        except Exception:
            pass

    QTimer.singleShot(1000, _hide)
