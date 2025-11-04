"""
Dropzone Widget - Área para arrastrar y soltar carpetas
"""
from pathlib import Path
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
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
        
        # Icono de carpeta usando icon_manager
        self.icon_label = QLabel()
        icon_manager.set_label_icon(
            self.icon_label, 
            'folder-open', 
            color=DesignSystem.COLOR_PRIMARY, 
            size=64
        )
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)
        
        # Texto principal (todo en una línea)
        self.main_text = QLabel("Arrastra una carpeta aquí")
        self.main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(self.main_text)
        
        # Texto secundario (hint sutil)
        self.hint_text = QLabel("o usa el botón de abajo")
        self.hint_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(self.hint_text)
        
        # Tamaño fijo (más compacto y proporcional)
        self.setFixedSize(
            DesignSystem.DROPZONE_WIDTH,
            160
        )
    
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
                size=64
            )
        else:
            bg_color = "rgba(245, 245, 245, 0.8)"
            border_color = DesignSystem.COLOR_BORDER
            
            self.setStyleSheet(f"""
                DropzoneWidget {{
                    background-color: {bg_color};
                    border: 2px dashed {border_color};
                    border-radius: {DesignSystem.RADIUS_LG}px;
                    transition: all 0.3s ease;
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
                size=64
            )
    
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
