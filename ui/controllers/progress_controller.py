from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import QTimer

from ui import styles


class ProgressController:
    """Controlador independiente de la UI de progreso.

    Provee una API pequeña y explícita para mostrar/ocultar/actualizar el
    progreso sin exponer widgets internos ni mantener compatibilidad
    con la API legacy.

    Métodos públicos:
    - show_progress(maximum, message)
    - hide_progress()
    - update_progress(current, total, message)
    """

    def __init__(self, parent, parent_layout):
        self.parent = parent
        self.group = QGroupBox("📊 Progreso")
        layout = QVBoxLayout(self.group)

        self.label = QLabel("Listo para procesar")
        self.label.setStyleSheet(styles.STYLE_PROGRESS_LABEL)
        layout.addWidget(self.label)

        self.bar = QProgressBar()
        self.bar.setStyleSheet(styles.STYLE_PROGRESS_BAR)
        layout.addWidget(self.bar)

        # Oculto por defecto
        self.group.setVisible(False)
        parent_layout.addWidget(self.group)

    def show_progress(self, maximum, message="Procesando"):
        """Muestra el grupo de progreso.

        - Si maximum > 0: se establece en modo determinate con ese máximo.
        - Si maximum <= 0 o None: se pone en modo indeterminado (busy).
        """
        try:
            self.group.setVisible(True)
        except Exception:
            return

        try:
            if maximum and maximum > 0:
                self.bar.setMaximum(maximum)
                self.bar.setValue(0)
            else:
                # Modo indeterminado
                self.bar.setMaximum(0)
        except Exception:
            try:
                self.bar.setMaximum(100)
                self.bar.setValue(0)
            except Exception:
                pass

        try:
            self.label.setText(message)
        except Exception:
            pass

    def hide_progress(self):
        """Oculta el grupo de progreso con un pequeño retraso para suavizar la UX."""

        def _hide():
            try:
                self.bar.setMaximum(100)
                self.bar.setValue(0)
            except Exception:
                pass
            try:
                self.group.setVisible(False)
            except Exception:
                pass

        QTimer.singleShot(1000, _hide)

    def update_progress(self, current: int, total: int, message: str = None):
        """Actualiza el estado de la barra y la etiqueta.

        Si total>0 se muestra progreso determinístico; si no, se mantiene
        en modo indeterminado. message es opcional.
        """
        try:
            if total and total > 0:
                self.bar.setMaximum(total)
                self.bar.setValue(min(current, total))
            else:
                self.bar.setMaximum(0)

            if message is not None:
                self.label.setText(message)
        except Exception:
            # No romper la ejecución por fallos en la UI
            pass
