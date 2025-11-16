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
        self.current_filename = ""
        
        self._setup_ui()
        self._apply_styles()
        self._start_timer()
    
    def _setup_ui(self):
        """Configura la interfaz del diálogo"""
        self.setWindowTitle("Analizando archivos similares")
        self.setModal(True)
        self.setFixedSize(580, 650)
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
        
        # Header con icono y título
        header_layout = QHBoxLayout()
        header_layout.setSpacing(DesignSystem.SPACE_12)
        
        header_icon = QLabel()
        icon_manager.set_label_icon(
            header_icon,
            "image-search",
            color=DesignSystem.COLOR_PRIMARY,
            size=32
        )
        
        header_text = QLabel("Análisis de similitud")
        header_text.setObjectName("header_text")
        
        header_layout.addWidget(header_icon)
        header_layout.addWidget(header_text)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Descripción del proceso
        description = QLabel(
            "Este proceso analiza cada imagen y vídeo comparándolos entre sí "
            "para detectar similitudes visuales (recortes, rotaciones, ediciones). "
            "Puede tardar varios minutos según la cantidad de archivos."
        )
        description.setObjectName("description_text")
        description.setWordWrap(True)
        main_layout.addWidget(description)
        
        main_layout.addSpacing(DesignSystem.SPACE_16)
        
        # Card de progreso principal
        progress_card = QFrame()
        progress_card.setObjectName("progress_card")
        progress_card_layout = QVBoxLayout(progress_card)
        progress_card_layout.setSpacing(DesignSystem.SPACE_16)
        progress_card_layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_20
        )
        
        # Estado actual con spinner - ALTURA FIJA
        status_container = QFrame()
        status_container.setObjectName("status_container")
        status_container.setFixedHeight(48)  # Altura fija para evitar movimiento
        
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(DesignSystem.SPACE_12)
        
        self.spinner_label = QLabel()
        icon_manager.set_label_icon(
            self.spinner_label,
            "timer",
            color=DesignSystem.COLOR_PRIMARY,
            size=20
        )
        
        self.status_text = QLabel("Iniciando análisis...")
        self.status_text.setObjectName("status_text")
        self.status_text.setWordWrap(True)
        self.status_text.setMaximumHeight(44)  # Altura máxima para 2 líneas
        
        status_layout.addWidget(self.spinner_label, 0, Qt.AlignmentFlag.AlignTop)
        status_layout.addWidget(self.status_text, 1)
        
        progress_card_layout.addWidget(status_container)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(36)
        progress_card_layout.addWidget(self.progress_bar)
        
        # Estadísticas
        stats_container = self._create_stats_container()
        progress_card_layout.addWidget(stats_container)
        
        main_layout.addWidget(progress_card)
        
        # Card de tiempo
        time_card = self._create_time_card()
        main_layout.addWidget(time_card)
        
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
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_12
        )
        layout.setSpacing(DesignSystem.SPACE_10)
        
        icon = QLabel()
        icon_manager.set_label_icon(
            icon,
            "chart-bar",
            color=DesignSystem.COLOR_PRIMARY,
            size=18
        )
        
        self.stats_text = QLabel(f"0 de {format_file_count(self.total_files)}")
        self.stats_text.setObjectName("stats_text")
        
        layout.addWidget(icon)
        layout.addWidget(self.stats_text)
        layout.addStretch()
        
        return container
    
    def _create_time_card(self) -> QFrame:
        """Crea la card de tiempo con diseño mejorado"""
        card = QFrame()
        card.setObjectName("time_card")
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_16
        )
        layout.setSpacing(DesignSystem.SPACE_12)
        
        # Tiempo transcurrido
        elapsed_layout = QHBoxLayout()
        elapsed_layout.setSpacing(DesignSystem.SPACE_10)
        
        elapsed_icon = QLabel()
        icon_manager.set_label_icon(
            elapsed_icon,
            "clock",
            color=DesignSystem.COLOR_TEXT_SECONDARY,
            size=16
        )
        
        self.elapsed_text = QLabel("Tiempo transcurrido: 0s")
        self.elapsed_text.setObjectName("time_text")
        
        elapsed_layout.addWidget(elapsed_icon)
        elapsed_layout.addWidget(self.elapsed_text)
        elapsed_layout.addStretch()
        layout.addLayout(elapsed_layout)
        
        # Tiempo estimado - EN UNA SOLA LÍNEA
        remaining_layout = QHBoxLayout()
        remaining_layout.setSpacing(DesignSystem.SPACE_10)
        
        remaining_icon = QLabel()
        icon_manager.set_label_icon(
            remaining_icon,
            "timer",
            color=DesignSystem.COLOR_TEXT_SECONDARY,
            size=16
        )
        
        self.remaining_text = QLabel("Tiempo restante: calculando...")
        self.remaining_text.setObjectName("time_text")
        
        remaining_layout.addWidget(remaining_icon)
        remaining_layout.addWidget(self.remaining_text)
        remaining_layout.addStretch()
        layout.addLayout(remaining_layout)
        
        return card
    
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
                        self.remaining_text.setText(f"Tiempo restante: ~{remaining_minutes}m {remaining_seconds}s")
                    else:
                        self.remaining_text.setText(f"Tiempo restante: ~{remaining_seconds}s")
                else:
                    self.remaining_text.setText("Tiempo restante: finalizando...")
    
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
        
        # Actualizar estadísticas
        self.stats_text.setText(f"{format_file_count(current)} de {format_file_count(total)}")
        
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
    
    def _apply_styles(self):
        """Aplica estilos siguiendo el DesignSystem con diseño Material"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
            }}
            
            /* Header */
            QLabel#header_text {{
                font-size: {DesignSystem.FONT_SIZE_3XL}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            /* Descripción */
            QLabel#description_text {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                line-height: {int(DesignSystem.FONT_SIZE_BASE * DesignSystem.LINE_HEIGHT_RELAXED)}px;
            }}
            
            /* Cards con elevación */
            QFrame#progress_card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border-radius: {DesignSystem.RADIUS_LG}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
            
            QFrame#time_card {{
                background-color: {DesignSystem.COLOR_BG_1};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
            
            /* Status container - altura fija */
            QFrame#status_container {{
                background-color: transparent;
            }}
            
            QLabel#status_text {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            /* Barra de progreso mejorada */
            QProgressBar#progress_bar {{
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                background-color: {DesignSystem.COLOR_BG_2};
                text-align: center;
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            
            QProgressBar#progress_bar::chunk {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {DesignSystem.COLOR_PRIMARY},
                    stop:1 {DesignSystem.COLOR_ACCENT}
                );
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            
            /* Stats container */
            QFrame#stats_container {{
                background-color: {DesignSystem.COLOR_BG_1};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
            
            QLabel#stats_text {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            /* Time labels */
            QLabel#time_text {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            /* Botón cancelar */
            QPushButton#cancel_button {{
                background-color: transparent;
                border: 2px solid {DesignSystem.COLOR_ERROR};
                color: {DesignSystem.COLOR_ERROR};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                padding: {DesignSystem.SPACE_10}px {DesignSystem.SPACE_32}px;
                border-radius: {DesignSystem.RADIUS_FULL}px;
                min-width: 160px;
            }}
            
            QPushButton#cancel_button:hover {{
                background-color: {DesignSystem.COLOR_ERROR};
                color: white;
            }}
            
            QPushButton#cancel_button:disabled {{
                background-color: {DesignSystem.COLOR_SURFACE_DISABLED};
                border-color: {DesignSystem.COLOR_BORDER};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """)
