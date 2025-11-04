"""
Dropzone Widget - Área para arrastrar y soltar carpetas
"""
from pathlib import Path
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager


class DropzoneWidget(QFrame):
    """
    Widget que acepta arrastrar y soltar carpetas
    Muestra área visual con instrucciones
    """
    
    # Señales
    folder_dropped = pyqtSignal(str)  # Emite la ruta de la carpeta
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._is_dragging = False
        self._setup_ui()
        self._apply_styles()
        
        # Configurar iconos después de que QApplication esté corriendo
        QTimer.singleShot(0, self._setup_icons)
    
    def _setup_ui(self):
        """Configura la interfaz del dropzone"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DesignSystem.SPACE_24, 
            DesignSystem.SPACE_20, 
            DesignSystem.SPACE_24, 
            DesignSystem.SPACE_20
        )
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icono de carpeta usando icon_manager (configurado después)
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setMinimumSize(48, 48)
        layout.addWidget(self.icon_label)
        
        # Texto principal (más corto)
        self.main_text = QLabel("Arrastra una carpeta aquí")
        self.main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(self.main_text)
        
        # Texto secundario (hint sutil, más corto)
        self.hint_text = QLabel("o usa el botón de 'Seleccionar carpeta' abajo")
        self.hint_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(self.hint_text)
        
        # Tamaño mínimo (usando las dimensiones definidas en DesignSystem)
        self.setMinimumSize(
            DesignSystem.DROPZONE_WIDTH,
            DesignSystem.DROPZONE_HEIGHT
        )
    
    def _setup_icons(self):
        """Configura los iconos después de que QApplication esté corriendo"""
        icon_manager.set_label_icon(
            self.icon_label, 
            'folder-open', 
            color=DesignSystem.COLOR_PRIMARY, 
            size=48
        )
        self.update()
    
    def _apply_styles(self):
        """Aplica estilos al widget"""
        self._update_appearance(dragging=False)
    
    def _update_appearance(self, dragging=False):
        """Actualiza la apariencia según el estado"""
        if dragging:
            self.setStyleSheet(f"""
                DropzoneWidget {{
                    background-color: rgba(37, 99, 235, 0.15);
                    border: 2px solid {DesignSystem.COLOR_PRIMARY};
                    border-radius: {DesignSystem.RADIUS_LG}px;
                }}
            """)
            self.main_text.setText("Suelta para analizar")
            self.hint_text.hide()
            # Cambiar color del icono a primary más intenso
            icon_manager.set_label_icon(
                self.icon_label, 
                'folder-open', 
                color=DesignSystem.COLOR_PRIMARY, 
                size=48
            )
            self.update()
        else:
            bg_color = "rgba(245, 245, 245, 0.8)"
            border_color = DesignSystem.COLOR_BORDER
            
            self.setStyleSheet(f"""
                DropzoneWidget {{
                    background-color: {bg_color};
                    border: 2px dashed {border_color};
                    border-radius: {DesignSystem.RADIUS_LG}px;
                }}
                DropzoneWidget:hover {{
                    border: 2px dashed {DesignSystem.COLOR_PRIMARY};
                    background-color: rgba(37, 99, 235, 0.05);
                }}
            """)
            self.main_text.setText("Arrastra una carpeta aquí")
            self.hint_text.show()
            # Restaurar color del icono
            icon_manager.set_label_icon(
                self.icon_label, 
                'folder-open', 
                color=DesignSystem.COLOR_PRIMARY, 
                size=48
            )
            self.update()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Maneja cuando se arrastra algo sobre el widget"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                path = Path(urls[0].toLocalFile())
                if path.is_dir():
                    event.acceptProposedAction()
                    self._is_dragging = True
                    self._update_appearance(dragging=True)
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """Maneja cuando se sale del área de drop"""
        self._is_dragging = False
        self._update_appearance(dragging=False)
    
    def dropEvent(self, event: QDropEvent):
        """Maneja cuando se suelta algo en el widget"""
        self._is_dragging = False
        self._update_appearance(dragging=False)
        
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                path = Path(urls[0].toLocalFile())
                if path.is_dir():
                    event.acceptProposedAction()
                    self.folder_dropped.emit(str(path))
                    return
        event.ignore()
