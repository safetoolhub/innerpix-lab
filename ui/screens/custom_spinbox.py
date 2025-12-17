"""
Custom SpinBox con flechas visibles usando qtawesome
"""
from PyQt6.QtWidgets import QSpinBox, QStyleOptionSpinBox, QStyle
from PyQt6.QtGui import QPainter, QIcon
from PyQt6.QtCore import QRect, Qt
import qtawesome as qta
from ui.styles.design_system import DesignSystem


class CustomSpinBox(QSpinBox):
    """
    SpinBox personalizado con iconos de qtawesome para las flechas
    Compatible con todos los sistemas operativos
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Crear iconos con qtawesome
        self._up_icon = qta.icon('mdi.chevron-up', color=DesignSystem.COLOR_TEXT)
        self._down_icon = qta.icon('mdi.chevron-down', color=DesignSystem.COLOR_TEXT)
        
        # Aplicar estilo base sin flechas personalizadas
        self.setStyleSheet(f"""
            QSpinBox {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_8}px;
                padding-right: 36px;
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                min-height: 38px;
                min-width: 120px;
            }}
            QSpinBox:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QSpinBox:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 32px;
                height: 18px;
                border-left: 1px solid {DesignSystem.COLOR_BORDER};
                border-bottom: 1px solid {DesignSystem.COLOR_BORDER};
                background-color: {DesignSystem.COLOR_BACKGROUND};
                border-top-right-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            QSpinBox::up-button:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
            }}
            QSpinBox::up-button:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
            }}
            QSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 32px;
                height: 18px;
                border-left: 1px solid {DesignSystem.COLOR_BORDER};
                background-color: {DesignSystem.COLOR_BACKGROUND};
                border-bottom-right-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            QSpinBox::down-button:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
            }}
            QSpinBox::down-button:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
            }}
        """)
    
    def paintEvent(self, event):
        """Override paintEvent para dibujar los iconos"""
        # Primero dibujar el spinbox normal
        super().paintEvent(event)
        
        # Ahora dibujar los iconos
        painter = QPainter(self)
        option = QStyleOptionSpinBox()
        self.initStyleOption(option)
        
        # Obtener las posiciones de los botones
        up_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_SpinBox,
            option,
            QStyle.SubControl.SC_SpinBoxUp,
            self
        )
        down_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_SpinBox,
            option,
            QStyle.SubControl.SC_SpinBoxDown,
            self
        )
        
        # Dibujar icono de arriba
        icon_size = 14
        up_icon_rect = QRect(
            up_rect.center().x() - icon_size // 2,
            up_rect.center().y() - icon_size // 2,
            icon_size,
            icon_size
        )
        self._up_icon.paint(painter, up_icon_rect)
        
        # Dibujar icono de abajo
        down_icon_rect = QRect(
            down_rect.center().x() - icon_size // 2,
            down_rect.center().y() - icon_size // 2,
            icon_size,
            icon_size
        )
        self._down_icon.paint(painter, down_icon_rect)
