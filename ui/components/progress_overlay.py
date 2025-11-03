"""
ProgressOverlay - Barra de progreso superpuesta para TopBar.

Componente que se superpone sobre la zona de stats durante el análisis,
mostrando progreso detallado sin afectar el layout principal.
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect

from ui import styles


class ProgressOverlay(QFrame):
    """Overlay de progreso superpuesto sobre Smart Stats.
    
    Muestra información de progreso durante análisis:
    - Label de estado (fase actual)
    - Barra de progreso animada
    - Detalle adicional (opcional)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation = None
        self._init_ui()
    
    def _init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setStyleSheet(styles.STYLE_TOPBAR_PROGRESS_CONTAINER)
        self.setVisible(False)
        
        # Posicionamiento inicial (se ajustará dinámicamente)
        self.setGeometry(0, 60, 800, 0)
        
        progress_layout = QVBoxLayout(self)
        progress_layout.setContentsMargins(24, 16, 24, 16)
        progress_layout.setSpacing(12)
        
        # Container interno con diseño moderno
        inner_container = QFrame()
        inner_container.setStyleSheet(styles.STYLE_TOPBAR_PROGRESS_INNER)
        inner_layout = QVBoxLayout(inner_container)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(12)
        
        # Label de estado con diseño limpio
        self.progress_label = QLabel("⏳ Preparando análisis...")
        self.progress_label.setStyleSheet(styles.STYLE_TOPBAR_PROGRESS_LABEL)
        inner_layout.addWidget(self.progress_label)
        
        # Barra de progreso moderna
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(styles.STYLE_TOPBAR_PROGRESS_BAR)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(32)
        inner_layout.addWidget(self.progress_bar)
        
        # Detalle adicional con diseño sutil
        self.progress_detail = QLabel("")
        self.progress_detail.setStyleSheet(styles.STYLE_TOPBAR_PROGRESS_DETAIL)
        self.progress_detail.setWordWrap(True)
        inner_layout.addWidget(self.progress_detail)
        
        progress_layout.addWidget(inner_container)
        progress_layout.addStretch()
    
    def show_animated(self, parent_width: int):
        """Muestra el overlay con animación
        
        Args:
            parent_width: Ancho del contenedor padre para ajustar geometría
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
    
    def hide_animated(self):
        """Oculta el overlay con animación"""
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
    
    def update_progress(self, value: int, label_text: str = None, detail_text: str = None):
        """Actualiza el progreso mostrado
        
        Args:
            value: Valor de progreso (0-100)
            label_text: Texto del label de estado (opcional)
            detail_text: Texto del detalle adicional (opcional)
        """
        self.progress_bar.setValue(value)
        
        if label_text is not None:
            self.progress_label.setText(label_text)
        
        if detail_text is not None:
            self.progress_detail.setText(detail_text)
    
    def adjust_width(self, width: int):
        """Ajusta el ancho del overlay
        
        Args:
            width: Nuevo ancho
        """
        current_geo = self.geometry()
        self.setGeometry(0, current_geo.y(), width, current_geo.height())
