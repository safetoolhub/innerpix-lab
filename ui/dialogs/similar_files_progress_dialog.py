"""
Diálogo de progreso bloqueante para el análisis de archivos similares.
Muestra el progreso en tiempo real con barra y estadísticas.
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QFrame, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from utils.format_utils import format_file_count
from .base_dialog import BaseDialog


class SimilarFilesProgressDialog(BaseDialog):
    """
    Diálogo modal bloqueante que muestra el progreso del análisis de archivos similares.
    
    Detecta fotos y vídeos visualmente similares: recortes, rotaciones,
    ediciones o diferentes resoluciones.
    """
    
    cancel_requested = pyqtSignal()
    
    def __init__(self, parent=None, total_files: int = 0):
        """
        Args:
            parent: Widget padre
            total_files: Total de archivos a procesar
        """
        super().__init__(parent)
        self.total_files = total_files
        self.current_files = 0
        self.current_filename = ""
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura la interfaz del diálogo"""
        self.setWindowTitle("Analizando archivos similares")
        self.setModal(True)
        self.setFixedSize(900, 500)
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.CustomizeWindowHint | 
            Qt.WindowType.WindowTitleHint
        )
        
        # Estilo base
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
            }}
        """)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Header Compacto
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='image-search',
            title='Análisis de Similitud',
            description='Detectando similitudes visuales (recortes, rotaciones, ediciones)...',
            metrics=[
                {'value': format_file_count(self.total_files), 'label': 'Archivos', 'color': DesignSystem.COLOR_PRIMARY}
            ]
        )
        main_layout.addWidget(self.header_frame)
        
        # Contenedor de contenido
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setSpacing(DesignSystem.SPACE_20)
        content_layout.setContentsMargins(
            DesignSystem.SPACE_32,
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_32,
            DesignSystem.SPACE_24
        )
        
        # 2. Card de Progreso Principal
        progress_card = QFrame()
        progress_card.setObjectName("progress_card")
        progress_card.setStyleSheet(f"""
            QFrame#progress_card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """)
        card_layout = QVBoxLayout(progress_card)
        card_layout.setSpacing(DesignSystem.SPACE_16)
        card_layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_24, DesignSystem.SPACE_24, DesignSystem.SPACE_24)
        
        # Estado con spinner
        status_layout = QHBoxLayout()
        status_layout.setSpacing(DesignSystem.SPACE_12)
        
        self.spinner_label = QLabel()
        icon_manager.set_label_icon(
            self.spinner_label,
            "timer",
            color=DesignSystem.COLOR_PRIMARY,
            size=24
        )
        
        self.status_text = QLabel("Iniciando análisis...")
        self.status_text.setWordWrap(True)
        self.status_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_MD}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """)
        
        status_layout.addWidget(self.spinner_label, 0, Qt.AlignmentFlag.AlignTop)
        status_layout.addWidget(self.status_text, 1)
        card_layout.addLayout(status_layout)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setStyleSheet(DesignSystem.get_progressbar_style())
        card_layout.addWidget(self.progress_bar)
        
        # Info de tiempo restante (secundario)
        self.remaining_text = QLabel("Calculando tiempo restante...")
        self.remaining_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.remaining_text.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        card_layout.addWidget(self.remaining_text)
        
        content_layout.addWidget(progress_card)
        
        content_layout.addStretch()
        
        # 3. Botón Cancelar (Centrado o a la derecha)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = self.make_styled_button(
            text="Cancelar Análisis",
            icon_name="cancel",
            button_style='secondary',
            custom_style=f"""
                QPushButton {{
                    background-color: transparent;
                    border: 2px solid {DesignSystem.COLOR_DANGER};
                    color: {DesignSystem.COLOR_DANGER};
                    border-radius: {DesignSystem.RADIUS_FULL}px;
                    padding: 8px 24px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_DANGER};
                    color: white;
                }}
            """
        )
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        
        content_layout.addLayout(button_layout)
        
        main_layout.addWidget(content_wrapper)
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """
        Actualiza el progreso del análisis
        
        Args:
            current: Archivos procesados
            total: Total de archivos
            message: Mensaje de estado (nombre del archivo actual)
        """
        self.current_files = current
        self.total_files = total
        
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        
        # Actualizar métrica de procesados en header
        # self._update_header_metric(self.header_frame, 'Procesados', format_file_count(current))
        
        # Actualizar mensaje con el archivo actual
        if message:
            self.status_text.setText(message)
            # Extraer el nombre del archivo después del salto de línea
            if "\n" in message:
                self.current_filename = message.split("\n", 1)[1]
            else:
                self.current_filename = message
    
    def _on_cancel_clicked(self):
        """Maneja el clic en cancelar con confirmación"""
        reply = QMessageBox.question(
            self,
            "Cancelar análisis",
            "¿Estás seguro de que deseas cancelar el análisis?\n"
            "El progreso actual se perderá.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.cancel_requested.emit()
            self.status_text.setText("Cancelando análisis...")
            self.cancel_button.setEnabled(False)
    
    def closeEvent(self, event):
        """Previene el cierre manual del diálogo"""
        # Solo permitir cierre si el análisis fue cancelado o completado
        if self.cancel_button.isEnabled():
            event.ignore()
        else:
            event.accept()
