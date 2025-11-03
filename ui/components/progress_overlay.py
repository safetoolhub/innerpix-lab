"""
ProgressOverlay - Barra de progreso superpuesta para el TopBar.

Componente que muestra el progreso del análisis de forma no intrusiva,
superponiéndose sobre el Smart Stats Bar durante el análisis.
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import QPropertyAnimation, QRect, QEasingCurve


class ProgressOverlay(QFrame):
    """Overlay de progreso que se superpone sobre el TopBar durante análisis."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._animation = None
    
    def _init_ui(self):
        """Inicializa la interfaz"""
        self.setStyleSheet(
            "QFrame {"
            "  background: rgba(255, 255, 255, 0.98);"
            "  border: none;"
            "  border-radius: 0px;"
            "}"
        )
        self.setVisible(False)
        
        # Posicionamiento absoluto (se calculará dinámicamente)
        self.setGeometry(0, 60, 0, 0)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)
        
        # Container interno con diseño moderno
        inner_container = QFrame()
        inner_container.setStyleSheet(
            "QFrame {"
            "  background: white;"
            "  border: 1px solid #e1e8ed;"
            "  border-radius: 12px;"
            "  padding: 20px;"
            "}"
        )
        inner_layout = QVBoxLayout(inner_container)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(12)
        
        # Label de estado con diseño limpio
        self.progress_label = QLabel("⏳ Preparando análisis...")
        self.progress_label.setStyleSheet(
            "color: #334155;"
            "font-weight: 600;"
            "font-size: 13px;"
            "background: transparent;"
            "border: none;"
        )
        inner_layout.addWidget(self.progress_label)
        
        # Barra de progreso moderna
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            "QProgressBar {"
            "  border: none;"
            "  border-radius: 8px;"
            "  text-align: center;"
            "  background-color: #f1f5f9;"
            "  height: 32px;"
            "  font-size: 12px;"
            "  font-weight: 600;"
            "  color: #475569;"
            "}"
            "QProgressBar::chunk {"
            "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "    stop:0 #3b82f6, stop:1 #60a5fa);"
            "  border-radius: 8px;"
            "}"
        )
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(32)
        inner_layout.addWidget(self.progress_bar)
        
        # Detalle adicional con diseño sutil
        self.progress_detail = QLabel("")
        self.progress_detail.setStyleSheet(
            "color: #64748b;"
            "font-size: 11px;"
            "background: transparent;"
            "border: none;"
        )
        self.progress_detail.setWordWrap(True)
        inner_layout.addWidget(self.progress_detail)
        
        layout.addWidget(inner_container)
        layout.addStretch()
    
    def show_progress(self, parent_width: int):
        """Muestra el overlay de progreso con animación.
        
        Args:
            parent_width: Ancho del widget padre para ajustar el overlay
        """
        target_height = 200
        
        # Ajustar geometría para cubrir smart_stats
        self.setGeometry(0, 60, parent_width, 0)
        self.setVisible(True)
        self.raise_()  # Traer al frente
        
        # Animar altura
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(250)
        self._animation.setStartValue(self.geometry())
        self._animation.setEndValue(QRect(0, 60, parent_width, target_height))
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()
    
    def hide_progress(self):
        """Oculta el overlay de progreso con animación"""
        if not self.isVisible():
            return
        
        # Animar hacia 0 altura
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(250)
        self._animation.setStartValue(self.geometry())
        current_geo = self.geometry()
        self._animation.setEndValue(QRect(0, 60, current_geo.width(), 0))
        self._animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._animation.finished.connect(lambda: self.setVisible(False))
        self._animation.start()
    
    def update_progress(self, value: int, text: str = ""):
        """Actualiza el valor de la barra de progreso.
        
        Args:
            value: Valor de 0-100
            text: Texto opcional para mostrar en la barra
        """
        self.progress_bar.setValue(value)
        if text:
            self.progress_bar.setFormat(text)
    
    def set_label(self, text: str):
        """Actualiza el label de estado.
        
        Args:
            text: Texto a mostrar en el label principal
        """
        self.progress_label.setText(text)
    
    def set_detail(self, text: str):
        """Actualiza el detalle adicional.
        
        Args:
            text: Texto a mostrar en el detalle
        """
        self.progress_detail.setText(text)
