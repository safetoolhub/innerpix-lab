"""
Diálogo de progreso bloqueante para el análisis de archivos similares.
Muestra el progreso en tiempo real con barra y estadísticas.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QTime

from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from utils.format_utils import format_file_count


class SimilarFilesProgressDialog(QDialog):
    """
    Diálogo modal bloqueante que muestra el progreso del análisis de archivos similares.
    
    Detecta fotos y vídeos visualmente similares: recortes, rotaciones,
    ediciones o diferentes resoluciones.
    
    Muestra:
    - Estado actual con spinner animado
    - Barra de progreso
    - Estadísticas (archivos procesados)
    - Tiempo transcurrido y estimado
    - Botón de cancelación con confirmación
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
        self.start_time = QTime.currentTime()
        
        self._setup_ui()
        self._apply_styles()
        self._start_timer()
    
    def _setup_ui(self):
        """Configura la interfaz del diálogo"""
        self.setWindowTitle("Analizando archivos similares")
        self.setModal(True)
        self.setFixedSize(520, 500)
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.CustomizeWindowHint | 
            Qt.WindowType.WindowTitleHint
        )
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(DesignSystem.SPACE_20)
        main_layout.setContentsMargins(
            DesignSystem.SPACE_32,
            DesignSystem.SPACE_32,
            DesignSystem.SPACE_32,
            DesignSystem.SPACE_32
        )
        
        # Estado actual con spinner
        status_layout = QHBoxLayout()
        status_layout.setSpacing(DesignSystem.SPACE_12)
        
        self.spinner_label = QLabel()
        icon_manager.set_label_icon(
            self.spinner_label,
            "loading",
            color=DesignSystem.COLOR_PRIMARY,
            size=24
        )
        
        self.status_text = QLabel("Identificando imágenes similares...")
        self.status_text.setObjectName("status_text")
        self.status_text.setWordWrap(True)
        
        status_layout.addWidget(self.spinner_label)
        status_layout.addWidget(self.status_text)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)
        
        main_layout.addSpacing(DesignSystem.SPACE_8)
        
        # Barra de progreso
        progress_container = QFrame()
        progress_container.setObjectName("progress_container")
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(DesignSystem.SPACE_8)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(progress_container)
        main_layout.addSpacing(DesignSystem.SPACE_12)
        
        # Estadísticas
        stats_container = self._create_stats_container()
        main_layout.addWidget(stats_container)
        
        # Tiempo
        time_container = self._create_time_container()
        main_layout.addWidget(time_container)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        main_layout.addWidget(separator)
        
        # Información
        info_layout = QHBoxLayout()
        info_icon = QLabel()
        icon_manager.set_label_icon(
            info_icon,
            "info",
            color=DesignSystem.COLOR_PRIMARY,
            size=16
        )
        
        info_text = QLabel(
            "El análisis está en progreso. La ventana se cerrará\n"
            "automáticamente al completarse."
        )
        info_text.setObjectName("info_text")
        info_text.setWordWrap(True)
        
        info_layout.addWidget(info_icon)
        info_layout.addWidget(info_text)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)
        
        # Espaciador
        main_layout.addStretch()
        
        # Botón cancelar
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancelar análisis")
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        
        buttons_layout.addWidget(self.cancel_button)
        main_layout.addLayout(buttons_layout)
    
    def _create_stats_container(self) -> QFrame:
        """Crea el contenedor de estadísticas"""
        container = QFrame()
        container.setObjectName("stats_container")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12
        )
        layout.setSpacing(DesignSystem.SPACE_8)
        
        icon = QLabel()
        icon_manager.set_label_icon(
            icon,
            "chart-bar",
            color=DesignSystem.COLOR_TEXT_SECONDARY,
            size=16
        )
        
        self.stats_text = QLabel(f"0 de {format_file_count(self.total_files)} procesados")
        self.stats_text.setObjectName("stats_text")
        self.stats_text.setWordWrap(True)
        
        layout.addWidget(icon)
        layout.addWidget(self.stats_text)
        layout.addStretch()
        
        return container
    
    def _create_time_container(self) -> QFrame:
        """Crea el contenedor de tiempo"""
        container = QFrame()
        container.setObjectName("time_container")
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_12
        )
        layout.setSpacing(DesignSystem.SPACE_4)
        
        # Tiempo transcurrido
        elapsed_layout = QHBoxLayout()
        elapsed_icon = QLabel()
        icon_manager.set_label_icon(
            elapsed_icon,
            "clock",
            color=DesignSystem.COLOR_TEXT_SECONDARY,
            size=16
        )
        
        self.elapsed_text = QLabel("Tiempo transcurrido: 0s")
        self.elapsed_text.setObjectName("time_text")
        self.elapsed_text.setWordWrap(True)
        
        elapsed_layout.addWidget(elapsed_icon)
        elapsed_layout.addWidget(self.elapsed_text)
        elapsed_layout.addStretch()
        layout.addLayout(elapsed_layout)
        
        # Tiempo estimado
        remaining_layout = QHBoxLayout()
        remaining_icon = QLabel()
        icon_manager.set_label_icon(
            remaining_icon,
            "clock",
            color=DesignSystem.COLOR_TEXT_SECONDARY,
            size=16
        )
        
        self.remaining_text = QLabel("Tiempo estimado restante: calculando...")
        self.remaining_text.setObjectName("time_text")
        self.remaining_text.setWordWrap(True)
        
        remaining_layout.addWidget(remaining_icon)
        remaining_layout.addWidget(self.remaining_text)
        remaining_layout.addStretch()
        layout.addLayout(remaining_layout)
        
        return container
    
    def _start_timer(self):
        """Inicia el timer para actualizar el tiempo transcurrido"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_elapsed_time)
        self.timer.start(1000)  # Actualizar cada segundo
    
    def _update_elapsed_time(self):
        """Actualiza el label de tiempo transcurrido"""
        elapsed = self.start_time.secsTo(QTime.currentTime())
        minutes = elapsed // 60
        seconds = elapsed % 60
        
        if minutes > 0:
            self.elapsed_text.setText(f"Tiempo transcurrido: {minutes}m {seconds}s")
        else:
            self.elapsed_text.setText(f"Tiempo transcurrido: {seconds}s")
        
        # Actualizar tiempo estimado restante si hay progreso
        if self.current_files > 0 and self.total_files > 0:
            progress_ratio = self.current_files / self.total_files
            if progress_ratio > 0:
                total_estimated = elapsed / progress_ratio
                remaining = int(total_estimated - elapsed)
                
                if remaining > 0:
                    remaining_minutes = remaining // 60
                    remaining_seconds = remaining % 60
                    
                    if remaining_minutes > 0:
                        self.remaining_text.setText(
                            f"Tiempo estimado restante: ~{remaining_minutes}m {remaining_seconds}s"
                        )
                    else:
                        self.remaining_text.setText(
                            f"Tiempo estimado restante: ~{remaining_seconds}s"
                        )
                else:
                    self.remaining_text.setText("Tiempo estimado restante: finalizando...")
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """
        Actualiza el progreso del análisis
        
        Args:
            current: Archivos procesados
            total: Total de archivos
            message: Mensaje de estado (opcional)
        """
        self.current_files = current
        self.total_files = total
        
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        
        # Actualizar estadísticas
        self.stats_text.setText(f"{format_file_count(current)} de {format_file_count(total)} procesados")
        
        # Actualizar mensaje si se proporciona
        if message:
            self.status_text.setText(message)
    
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
    
    def _apply_styles(self):
        """Aplica estilos siguiendo el DesignSystem"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            
            QLabel#status_text {{
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QFrame#progress_container {{
                background-color: transparent;
            }}
            
            QProgressBar#progress_bar {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                background-color: {DesignSystem.COLOR_BG_1};
                text-align: center;
                height: 32px;
            }}
            
            QProgressBar#progress_bar::chunk {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            
            QFrame#stats_container {{
                background-color: {DesignSystem.COLOR_BG_1};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            
            QLabel#stats_text {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QFrame#time_container {{
                background-color: {DesignSystem.COLOR_BG_1};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            
            QLabel#time_text {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QFrame#separator {{
                background-color: {DesignSystem.COLOR_BORDER};
                max-height: 1px;
            }}
            
            QLabel#info_text {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QPushButton#cancel_button {{
                background-color: transparent;
                border: 2px solid {DesignSystem.COLOR_ERROR};
                color: {DesignSystem.COLOR_ERROR};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_24}px;
                border-radius: {DesignSystem.RADIUS_FULL}px;
                min-width: 140px;
            }}
            
            QPushButton#cancel_button:hover {{
                background-color: {DesignSystem.COLOR_ERROR};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
            }}
            
            QPushButton#cancel_button:disabled {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                border-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """)
