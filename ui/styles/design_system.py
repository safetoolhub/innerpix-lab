"""Design System para Innerpix Lab.

Sistema de diseño centralizado que proporciona tokens CSS consistentes
y métodos de estilo reutilizables para toda la aplicación.

Este módulo define:
- Tokens de diseño (colores, tipografía, espaciado, etc.)
- Métodos de estilo QSS para componentes comunes
- Estilos Material Design modernos y coherentes

Usage:
    from ui.styles.design_system import DesignSystem
    
    # Usar tokens
    button.setStyleSheet(f"color: {DesignSystem.COLOR_PRIMARY};")
    
    # Usar métodos de estilo
    button.setStyleSheet(DesignSystem.get_primary_button_style())
"""


class DesignSystem:
    """Sistema de diseño centralizado con tokens y estilos reutilizables.
    
    Proporciona constantes de diseño (colores, tipografía, espaciado) y
    métodos estáticos que retornan estilos QSS para componentes de PyQt6.
    Sigue principios de Material Design para una experiencia moderna y coherente.
    """
    
    # ==================== COLORES ====================
    
    # Colores base
    COLOR_BACKGROUND = "#F8F9FA"  # Gris muy claro y moderno
    COLOR_SURFACE = "#FFFFFF"
    COLOR_TEXT = "#212529"
    COLOR_TEXT_SECONDARY = "#6C757D"
    
    # Colores primarios (Azul vibrante profesional)
    COLOR_PRIMARY = "#0D6EFD"
    COLOR_PRIMARY_HOVER = "#0B5ED7"
    COLOR_PRIMARY_ACTIVE = "#0A58CA"
    COLOR_PRIMARY_LIGHT = "#E7F1FF"  # Fondos sutiles
    COLOR_PRIMARY_SUBTLE = "rgba(37, 99, 235, 0.02)"  # Fondos muy sutiles
    COLOR_PRIMARY_TEXT = "#FFFFFF"
    
    # Colores secundarios (Gris neutro)
    COLOR_SECONDARY = "#6C757D"
    COLOR_SECONDARY_HOVER = "#5C636A"
    COLOR_SECONDARY_LIGHT = "#E9ECEF"
    
    # Estados semánticos
    COLOR_SUCCESS = "#198754"
    COLOR_SUCCESS_BG = "#D1E7DD"
    COLOR_SUCCESS_SOFT_BG = "#E6F4EA"  # Verde muy suave y agradable
    COLOR_WARNING = "#FFC107"
    COLOR_WARNING_BG = "#FFF3CD"
    COLOR_DANGER = "#DC3545"
    COLOR_DANGER_HOVER = "#BB2D3B"
    COLOR_DANGER_BG = "#F8D7DA"
    COLOR_INFO = "#0DCAF0"
    COLOR_INFO_BG = "#CFF4FC"
    COLOR_INFO_TEXT = "#055160"  # Texto legible sobre fondo info
    
    # Bordes
    COLOR_BORDER = "#DEE2E6"
    COLOR_BORDER_LIGHT = "#E9ECEF"
    COLOR_CARD_BORDER = "#DEE2E6"  # Alias para compatibilidad
    
    # ==================== TIPOGRAFÍA ====================
    
    FONT_FAMILY_BASE = "'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif"
    FONT_FAMILY_MONO = "'Consolas', 'Monaco', monospace"
    
    FONT_SIZE_XS = 11
    FONT_SIZE_SM = 13
    FONT_SIZE_BASE = 14
    FONT_SIZE_MD = 16
    FONT_SIZE_LG = 18
    FONT_SIZE_XL = 24
    FONT_SIZE_2XL = 32
    
    FONT_WEIGHT_NORMAL = 400
    FONT_WEIGHT_MEDIUM = 500
    FONT_WEIGHT_SEMIBOLD = 600
    FONT_WEIGHT_BOLD = 700
    
    # ==================== ESPACIADO ====================
    
    SPACE_2 = 2
    SPACE_4 = 4
    SPACE_6 = 6
    SPACE_8 = 8
    SPACE_10 = 10
    SPACE_12 = 12
    SPACE_16 = 16
    SPACE_20 = 20
    SPACE_24 = 24
    SPACE_32 = 32
    SPACE_40 = 40
    SPACE_48 = 48
    
    # ==================== BORDER RADIUS ====================
    
    RADIUS_SM = 4
    RADIUS_BASE = 6
    RADIUS_MD = 8
    RADIUS_LG = 12
    RADIUS_XL = 16
    RADIUS_FULL = 9999
    
    # ==================== SOMBRAS ====================
    
    SHADOW_SM = "rgba(0, 0, 0, 0.05) 0px 1px 2px 0px"
    SHADOW_MD = "rgba(0, 0, 0, 0.1) 0px 4px 6px -1px, rgba(0, 0, 0, 0.06) 0px 2px 4px -1px"
    SHADOW_LG = "rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.05) 0px 4px 6px -2px"
    
    # ==================== ANIMACIONES ====================
    
    TRANSITION_QUICK = 150
    TRANSITION_BASE = 250
    TRANSITION_SLOW = 400
    
    # ==================== DIMENSIONES ====================
    
    WINDOW_MIN_WIDTH = 800
    WINDOW_MIN_HEIGHT = 600
    WINDOW_DEFAULT_WIDTH = 1200
    WINDOW_DEFAULT_HEIGHT = 800
    
    # Resoluciones de referencia para lógica de ventana
    FULLHD_WIDTH = 1920
    FULLHD_HEIGHT = 1080
    
    HEADER_HEIGHT = 50
    DROPZONE_WIDTH = 300
    DROPZONE_HEIGHT = 200
    DROPZONE_WIDTH_MOBILE = 250
    DROPZONE_HEIGHT_MOBILE = 180
    
    # ==================== ALIASES PARA COMPATIBILIDAD ====================
    # Mantenidos para retrocompatibilidad con diálogos existentes
    
    COLOR_ACCENT = COLOR_PRIMARY
    COLOR_BG_1 = COLOR_BACKGROUND
    COLOR_BG_2 = COLOR_SECONDARY_LIGHT
    COLOR_BG_4 = COLOR_WARNING_BG
    COLOR_SURFACE_DISABLED = COLOR_SECONDARY_LIGHT
    COLOR_ERROR = COLOR_DANGER
    RADIUS_SMALL = RADIUS_SM
    
    # ==================== ICONOS ====================
    
    ICON_SIZE_SM = 16
    ICON_SIZE_MD = 20
    ICON_SIZE_LG = 24
    ICON_SIZE_XL = 32
    
    # ==================== HELPERS PRIVADOS (Estilos comunes reutilizables) ====================
    
    @staticmethod
    def _get_button_disabled_style():
        """Helper interno: estilo disabled compartido por todos los botones."""
        return f"""
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """
    
    # ==================== MÉTODOS DE AYUDA ====================
    
    @staticmethod
    def hex_to_qcolor(hex_color: str):
        """Convierte un color hexadecimal a QColor.
        
        Args:
            hex_color: Color en formato hexadecimal (#RRGGBB o rgba(r, g, b, a))
            
        Returns:
            QColor: Objeto QColor correspondiente
        """
        from PyQt6.QtGui import QColor
        
        # Manejar colores rgba
        if hex_color.startswith('rgba'):
            # Extraer valores de rgba(r, g, b, a)
            import re
            match = re.match(r'rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)', hex_color)
            if match:
                r, g, b, a = match.groups()
                color = QColor(int(r), int(g), int(b))
                color.setAlpha(int(float(a) * 255))
                return color
        
        # Colores hexadecimales estándar
        return QColor(hex_color)
    
    @staticmethod
    def get_stylesheet():
        """Retorna el stylesheet QSS global de la aplicación.
        
        Incluye estilos base para QMainWindow, QWidget y componentes comunes
        como botones primarios/secundarios, cards y labels.
        
        Returns:
            str: Stylesheet QSS global.
        """
        return f"""
            * {{
                font-family: {DesignSystem.FONT_FAMILY_BASE};
            }}
            
            QMainWindow {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
            }}
            
            QWidget {{
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            /* Botones primarios */
            QPushButton#primary-button {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 10px 24px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            
            QPushButton#primary-button:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            
            QPushButton#primary-button:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY};
            }}
            
            /* Botones secundarios */
            QPushButton.secondary {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 8px 16px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            
            QPushButton.secondary:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
            }}
            
            /* Botones secundarios pequeños */
            QPushButton.secondary-small {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 6px 12px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            
            QPushButton.secondary-small:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
            }}
            
            /* Cards */
            QFrame.card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
            
            /* Labels */
            QLabel.header {{
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QLabel.secondary {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QLabel.small {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QLabel.title {{
                font-size: {DesignSystem.FONT_SIZE_2XL}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QLabel.mono {{
                font-family: {DesignSystem.FONT_FAMILY_MONO};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """
    
    @staticmethod
    def get_filter_label_style():
        """Retorna el estilo para etiquetas de filtros.
        
        Diseño minimalista y compacto: texto muy pequeño, discreto.
        Sin bordes y con espaciado mínimo.
        """
        return f"""
            QLabel {{
                font-size: 9px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                background: transparent;
                border: none;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin: 0px;
                padding: 0px 0px 2px 0px;
            }}
        """
    
    @staticmethod
    def get_filter_container_style():
        """Estilo para contenedores de inputs dentro de la barra de filtros."""
        return f"""
            QWidget {{
                background-color: {DesignSystem.COLOR_BG_1};
                border: 2px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            QWidget:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """
    
    @staticmethod
    def get_tooltip_style():
        """Retorna el estilo QSS para tooltips.
        
        TODOS los tooltips de la aplicación deben usar este estilo.
        Diseño profesional: fondo oscuro, texto claro, compacto.
        
        Returns:
            str: Estilo QSS para tooltips.
        """
        return f"""
            QToolTip {{
                background-color: #2D3436;
                color: #F5F6FA;
                border: none;
                border-radius: {DesignSystem.RADIUS_SM}px;
                padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
                font-family: {DesignSystem.FONT_FAMILY_BASE};
            }}
        """
    
    @staticmethod
    def get_tab_widget_style():
        """Retorna el estilo QSS para widgets de pestañas (QTabWidget).
        
        Incluye estilos para el panel y las pestañas con estados hover/selected.
        
        Returns:
            str: Estilo QSS para QTabWidget.
        """
        return f"""
            QTabWidget::pane {{
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                background-color: {DesignSystem.COLOR_SURFACE};
                padding: {DesignSystem.SPACE_16}px;
            }}
            
            QTabBar::tab {{
                background-color: {DesignSystem.COLOR_BG_2};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_20}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-bottom: none;
                border-top-left-radius: {DesignSystem.RADIUS_BASE}px;
                border-top-right-radius: {DesignSystem.RADIUS_BASE}px;
                margin-right: {DesignSystem.SPACE_4}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-width: 100px;
                text-align: center;
            }}
            
            QTabBar::tab:selected {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_PRIMARY};
                border-color: {DesignSystem.COLOR_CARD_BORDER};
                border-bottom-color: {DesignSystem.COLOR_SURFACE}; /* Connect with pane */
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            
            QTabBar::tab:hover {{
                background-color: {DesignSystem.COLOR_BG_1};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QTabBar::tab:selected:hover {{
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
        """

    @staticmethod
    def get_context_menu_style():
        """Retorna el estilo QSS para menús contextuales (QMenu).
        
        Estilo Material Design con estados hover, disabled y separadores.
        
        Returns:
            str: Estilo QSS para QMenu.
        """
        return f"""
            QMenu {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
            
            QMenu::item {{
                background-color: transparent;
                color: {DesignSystem.COLOR_TEXT};
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_16}px;
                border-radius: {DesignSystem.RADIUS_SMALL}px;
                margin: {DesignSystem.SPACE_2}px;
            }}
            
            QMenu::item:selected {{
                background-color: {DesignSystem.COLOR_BG_2};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QMenu::item:disabled {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {DesignSystem.COLOR_BORDER};
                margin: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
            }}
            
            QMenu::icon {{
                padding-left: {DesignSystem.SPACE_8}px;
            }}
        """
    
    @staticmethod
    def get_combobox_style():
        """Retorna el estilo QSS completo para QComboBox.
        
        Estilo Material Design premium con dropdown y menú moderno.
        Incluye estados hover, focus y selected.
        
        Returns:
            str: Estilo QSS para QComboBox.
        """
        return f"""
            QComboBox {{
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                font-family: {DesignSystem.FONT_FAMILY_BASE};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
                background-color: {DesignSystem.COLOR_SURFACE};
                min-height: 40px; /* Más alto para toque premium */
                min-width: 120px;
            }}
            
            QComboBox:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                background-color: {DesignSystem.COLOR_BG_1};
            }}
            
            QComboBox:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                border-width: 2px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_10}px; /* Compensar borde */
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 30px;
                padding-right: 8px;
            }}
            

            QComboBox QAbstractItemView {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px;
                selection-background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                selection-color: {DesignSystem.COLOR_PRIMARY};
                outline: none;
                font-family: {DesignSystem.FONT_FAMILY_BASE};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
                margin-top: {DesignSystem.SPACE_4}px; /* Espacio entre combo y lista */
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: {DesignSystem.SPACE_10}px {DesignSystem.SPACE_16}px; /* Más espaciado */
                border-radius: {DesignSystem.RADIUS_SMALL}px;
                margin: {DesignSystem.SPACE_2}px;
                min-height: 36px;
            }}
            
            QComboBox QAbstractItemView::item:hover {{
                background-color: {DesignSystem.COLOR_BG_2};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QComboBox QAbstractItemView::item:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                color: {DesignSystem.COLOR_PRIMARY};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
        """

    @staticmethod
    def get_progressbar_style():
        """Retorna el estilo QSS para QProgressBar.
        
        Barra de progreso con bordes redondeados y estilo moderno.
        
        Returns:
            str: Estilo QSS para QProgressBar.
        """
        return f"""
            QProgressBar {{
                border: none;
                border-radius: {DesignSystem.RADIUS_FULL}px;
                background-color: {DesignSystem.COLOR_SECONDARY};
                text-align: center;
                height: 20px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QProgressBar::chunk {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                border-radius: {DesignSystem.RADIUS_FULL}px;
            }}
        """



    @staticmethod
    def get_checkbox_style():
        """Retorna el estilo QSS para QCheckBox.
        
        Incluye indicador personalizado con checkmark SVG y estados hover/disabled.
        
        Returns:
            str: Estilo QSS para QCheckBox.
        """
        return f"""
            QCheckBox {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
                spacing: {DesignSystem.SPACE_8}px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {DesignSystem.COLOR_BORDER};
                border-radius: 4px;
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QCheckBox::indicator:checked {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                border-color: {DesignSystem.COLOR_PRIMARY};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }}
            QCheckBox::indicator:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QCheckBox:disabled {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            QCheckBox::indicator:disabled {{
                border-color: {DesignSystem.COLOR_BORDER};
                background-color: {DesignSystem.COLOR_BG_2};
            }}
        """

    @staticmethod
    def get_lineedit_style():
        """Retorna el estilo QSS para QLineEdit.
        
        Incluye estados focus y read-only con colores diferenciados.
        
        Returns:
            str: Estilo QSS para QLineEdit.
        """
        return f"""
            QLineEdit {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
            QLineEdit:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QLineEdit:read-only {{
                background-color: {DesignSystem.COLOR_BG_1};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """

    # ==================== ESTILOS DE BOTONES ====================
    
    @staticmethod
    def get_primary_button_style():
        """Retorna el estilo para botón primario (acción principal).
        
        Uso recomendado: Acciones principales como "Organizar Archivos",
        "Proceder", "Guardar", "Aceptar".
        
        Returns:
            str: Estilo QSS con estados hover, pressed y disabled.
        """
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_24}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """ + DesignSystem._get_button_disabled_style()
    
    @staticmethod
    def get_danger_button_style():
        """Retorna el estilo para botón de acción destructiva.
        
        Uso recomendado: Acciones irreversibles como "Eliminar",
        "Borrar Archivos", "Eliminar Permanentemente".
        
        Returns:
            str: Estilo QSS con hover más oscuro para feedback visual.
        """
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_DANGER};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_24}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_DANGER_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #A02530;
            }}
        """ + DesignSystem._get_button_disabled_style()
    
    @staticmethod
    def get_secondary_button_style():
        """Retorna el estilo para botón secundario.
        
        Uso recomendado: Acciones de cancelación, cerrar diálogos,
        acciones alternativas no destructivas.
        
        Returns:
            str: Estilo QSS con hover sutil y borde visible.
        """
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_24}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                border-color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_BORDER_LIGHT};
            }}
        """ + DesignSystem._get_button_disabled_style()
    
    @staticmethod
    def get_icon_button_style():
        """Retorna el estilo para botones de icono (QToolButton).
        
        Uso recomendado: Botones con solo iconos en headers, toolbars.
        Ejemplos: Configuración, información, menús.
        
        Returns:
            str: Estilo QSS transparente con hover sutil.
        """
        return f"""
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px;
            }}
            QToolButton:hover {{
                background-color: rgba(0, 0, 0, 0.05);
            }}
            QToolButton:pressed {{
                background-color: rgba(0, 0, 0, 0.1);
            }}
        """

    @staticmethod
    def get_info_badge_style():
        """Retorna el estilo para badges de información.
        
        Badge transparente por defecto, con fondo azul claro al hover.
        Usado en cards para mostrar información adicional.
        
        Returns:
            str: Estilo QSS para QLabel tipo badge.
        """
        return f"""
            QLabel {{
                background-color: transparent;
                border: none;
                border-radius: 10px;
            }}
            QLabel:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
            }}
        """

    # ==================== CARDS Y CONTENEDORES ====================
    
    @staticmethod
    def get_card_style():
        """Retorna el estilo base para cards (QFrame).
        
        Card estándar con padding normal. Usado en summary_card,
        progress_card, folder_selection_card, etc.
        
        Returns:
            str: Estilo QSS para QFrame tipo card.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_16}px;
            }}
        """
    
    @staticmethod
    def get_card_style_compact():
        """Retorna el estilo para cards compactas.
        
        Variante con menos padding para espacios reducidos.
        
        Returns:
            str: Estilo QSS para QFrame compacto.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: 10px;
            }}
        """
    
    @staticmethod
    def get_header_card_style():
        """Retorna el estilo para la card de header.
        
        Card del encabezado principal de la aplicación con padding horizontal.
        
        Returns:
            str: Estilo QSS para header.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: 10px {DesignSystem.SPACE_20}px;
            }}
        """

    @staticmethod
    def get_status_frame_style(color: str):
        """Retorna el estilo para un frame de estado con borde lateral coloreado.
        
        Diseño profesional: fondo de superficie, borde sutil y un acento
        específico de color en el lateral izquierdo para indicar el estado.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-left: 5px solid {color};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px;
            }}
        """
    
    @staticmethod
    def get_stale_banner_style():
        """Retorna el estilo para banner de advertencia.
        
        Banner amarillo para mostrar estadísticas desactualizadas u
        otras advertencias no críticas.
        
        Returns:
            str: Estilo QSS para banner de advertencia.
        """
        return f"""
            QFrame#staleBanner {{
                background-color: {DesignSystem.COLOR_WARNING_BG};
                border: 1px solid {DesignSystem.COLOR_WARNING};
                border-radius: {DesignSystem.RADIUS_MD}px;
            }}
        """
    
    @staticmethod
    def get_warning_button_style():
        """Retorna el estilo para botones en banners de advertencia.
        
        Botón semitransparente que se integra con el fondo amarillo
        del banner de advertencia.
        
        Returns:
            str: Estilo QSS para botones en banners.
        """
        return f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.5);
                border: 1px solid {DesignSystem.COLOR_WARNING};
                border-radius: {DesignSystem.RADIUS_SM}px;
                padding: 6px 12px;
                color: {DesignSystem.COLOR_TEXT};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.8);
            }}
        """
    
    # ==================== ESTILOS DE TEXTO Y LABELS ====================
    
    @staticmethod
    def get_label_title_style():
        """Retorna el estilo para títulos principales.
        
        Usado en welcome title, header title y otros títulos destacados.
        
        Returns:
            str: Estilo CSS para texto de título.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {DesignSystem.COLOR_TEXT};
        """
    
    @staticmethod
    def get_label_subtitle_style():
        """Retorna el estilo para subtítulos.
        
        Texto secundario más pequeño para complementar títulos.
        
        Returns:
            str: Estilo QSS para QLabel de subtítulo.
        """
        return f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
            }}
        """
    
    @staticmethod
    def get_label_mono_style():
        """Retorna el estilo para texto monoespaciado.
        
        Usado para rutas de archivos, código y datos técnicos.
        
        Returns:
            str: Estilo CSS con fuente monoespaciada.
        """
        return f"""
            font-family: {DesignSystem.FONT_FAMILY_MONO};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """
    
    @staticmethod
    def get_label_secondary_style():
        """Retorna el estilo para texto secundario.
        
        Usado para hints, descripciones cortas y texto de apoyo.
        
        Returns:
            str: Estilo CSS con color secundario.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """
    
    @staticmethod
    def get_tree_widget_style():
        """Retorna el estilo Material Design para QTreeWidget.
        
        Estilo unificado para todos los TreeWidgets de grupos en diálogos.
        Incluye estilos para items, hover, selección y headers.
        
        Returns:
            str: Estilo CSS completo para QTreeWidget.
        """
        return f"""
            QTreeWidget {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                outline: none;
                background-color: {DesignSystem.COLOR_SURFACE};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px;
            }}
            QTreeWidget::item {{
                border: none;
                outline: none;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_4}px;
                border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};
            }}
            QTreeWidget::item:hover {{
                background-color: {DesignSystem.COLOR_BG_2};
            }}
            QTreeWidget::item:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT};
            }}
            QHeaderView::section {{
                background-color: {DesignSystem.COLOR_BG_1};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_8}px;
                border: none;
                border-bottom: 2px solid {DesignSystem.COLOR_BORDER};
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
        """
    
    @staticmethod
    def get_section_title_style():
        """Retorna el estilo para títulos de sección.
        
        Títulos pequeños en mayúsculas para categorizar contenido
        (ej: categorías de herramientas).
        
        Returns:
            str: Estilo CSS uppercase con letra espaciada.
        """
        return f"""
            font-size: 10px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            letter-spacing: 0.5px;
        """
    
    # ==================== OTROS COMPONENTES ====================
    
    @staticmethod
    def get_separator_style():
        """Retorna el estilo para líneas separadoras.
        
        Línea horizontal simple para dividir secciones.
        
        Returns:
            str: Estilo CSS para QFrame tipo separador.
        """
        return f"background-color: {DesignSystem.COLOR_BORDER};"
    
    # ==================== DROPZONE ====================
    
    @staticmethod
    def get_dropzone_style(dragging: bool = False):
        """Retorna el estilo para el widget de dropzone.
        
        Zona de arrastrar y soltar archivos con estados visual diferenciados.
        
        Args:
            dragging: True si el usuario está arrastrando sobre el widget.
        
        Returns:
            str: Estilo QSS con estado drag activo o inactivo.
        """
        if dragging:
            return f"""
                DropzoneWidget {{
                    background-color: rgba(37, 99, 235, 0.15);
                    border: 2px solid {DesignSystem.COLOR_PRIMARY};
                    border-radius: {DesignSystem.RADIUS_LG}px;
                }}
            """
        else:
            return f"""
                DropzoneWidget {{
                    background-color: rgba(245, 245, 245, 0.8);
                    border: 2px dashed {DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_LG}px;
                }}
                DropzoneWidget:hover {{
                    border: 2px dashed {DesignSystem.COLOR_PRIMARY};
                    background-color: rgba(37, 99, 235, 0.05);
                }}
            """
    
    # ==================== TOOL CARD ====================
    
    @staticmethod
    def get_tool_card_style():
        """Retorna el estilo para cards de herramientas.
        
        Cards interactivas en el grid de herramientas del Stage 3.
        Incluye estados hover y disabled.
        
        Returns:
            str: Estilo QSS para ToolCard.
        """
        return f"""
            ToolCard {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
            ToolCard:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                background-color: rgba(37, 99, 235, 0.02);
            }}
            ToolCard[enabled_state="disabled"] {{
                background-color: {DesignSystem.COLOR_SURFACE_DISABLED};
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """
    
    @staticmethod
    def get_tool_card_action_button_style():
        """Retorna el estilo para botones de acción en tool cards.
        
        Incluye variantes por clase:
        - 'primary': Botón azul para GESTIONAR
        - 'warning': Botón ámbar para ANALIZAR
        - disabled: Estado deshabilitado
        
        Returns:
            str: Estilo QSS con clases primary/warning.
        """
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: white;
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 10px 20px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            }}
            QPushButton:hover {{ 
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER}; 
            }}
            
            /* Clase para ANALIZAR (Ámbar) */
            QPushButton[class="warning"] {{
                background-color: {DesignSystem.COLOR_WARNING};
                color: {DesignSystem.COLOR_TEXT};
            }}
            QPushButton[class="warning"]:hover {{
                background-color: #e5ac06;
            }}
            
            /* Clase para GESTIONAR (Azul) */
            QPushButton[class="primary"] {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: white;
            }}
            
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SURFACE_DISABLED};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """
    
    @staticmethod
    def get_status_badge_style(bg_color: str):
        """Retorna el estilo para badges de estado.
        
        Pequeños badges redondeados para mostrar contadores o estados
        en tool cards.
        
        Args:
            bg_color: Color de fondo del badge (hex o rgb).
        
        Returns:
            str: Estilo QSS para QLabel con objectName 'statusBadge'.
        """
        return f"""
            QLabel#statusBadge {{
                background-color: {bg_color};
                color: white;
                border-radius: 9px;
                padding: 1px 6px;
                min-width: 14px;
                font-size: 10px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            }}
        """
    
    # ==================== SPINBOX ====================
    
    @staticmethod
    def get_spinbox_style():
        """Retorna el estilo para QSpinBox.
        
        Spinbox personalizado con botones up/down estilizados.
        
        Returns:
            str: Estilo QSS completo para QSpinBox.
        """
        return f"""
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
        """
    
    @staticmethod
    def get_small_button_style(style_type: str = "secondary"):
        """Retorna el estilo para botones pequeños.
        
        Uso recomendado: Badges, acciones menores, botones compactos.
        
        Args:
            style_type: Tipo de estilo ('secondary', 'cancel', 'link').
                - 'secondary': Fondo gris claro (default)
                - 'cancel': Transparente con borde
                - 'link': Estilo texto/link sin fondo
        
        Returns:
            str: Estilo QSS para botones pequeños.
        """
        if style_type == "cancel":
            return f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid {DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
                    color: {DesignSystem.COLOR_TEXT_SECONDARY};
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                }}
                QPushButton:hover {{
                    background: {DesignSystem.COLOR_BG_2};
                    border-color: {DesignSystem.COLOR_TEXT_SECONDARY};
                }}
            """
        elif style_type == "link":
            return f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {DesignSystem.COLOR_TEXT_SECONDARY};
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                    padding: 4px 8px;
                }}
                QPushButton:hover {{
                    color: {DesignSystem.COLOR_PRIMARY};
                    text-decoration: underline;
                }}
            """
        else:  # secondary (default)
            return f"""
                QPushButton {{
                    background-color: {DesignSystem.COLOR_BG_2};
                    color: {DesignSystem.COLOR_TEXT};
                    border: none;
                    border-radius: {DesignSystem.RADIUS_SM}px;
                    padding: 4px 10px;
                    font-size: {DesignSystem.FONT_SIZE_XS}px;
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_BORDER};
                }}
            """
    
    @staticmethod
    def get_last_folder_container_style():
        """Retorna el estilo para contenedor de última carpeta.
        
        Contenedor con fondo azul sutil para destacar la última
        carpeta analizada en Stage 1.
        
        Returns:
            str: Estilo QSS para QWidget contenedor.
        """
        return f"""
            QWidget {{
                background-color: rgba(59, 130, 246, 0.08);
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
            }}
        """
    
    @staticmethod
    def get_use_folder_button_style():
        """Retorna el estilo para botón 'Usar esta carpeta'.
        
        Botón compacto de acción rápida en Stage 1.
        
        Returns:
            str: Estilo QSS compacto con color primario.
        """
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: white;
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """
    
    # ==================== ESTILOS DE ANÁLISIS Y FASES ====================
    
    @staticmethod
    def get_phase_text_style(status: str = 'pending'):
        """Retorna el estilo para texto de fases de análisis.
        
        Args:
            status: Estado de la fase ('pending', 'running', 'completed',
                   'error', 'skipped').
        
        Returns:
            str: Estilo CSS con color según estado.
        """
        base_style = f"font-size: {DesignSystem.FONT_SIZE_LG}px; line-height: 1.0;"
        
        if status == 'completed':
            return f"""
                {base_style}
                color: {DesignSystem.COLOR_SUCCESS};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            """
        elif status == 'running':
            return f"""
                {base_style}
                color: {DesignSystem.COLOR_PRIMARY};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            """
        elif status == 'error':
            return f"""
                {base_style}
                color: {DesignSystem.COLOR_ERROR};
            """
        elif status == 'skipped':
            return f"""
                {base_style}
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-style: italic;
            """
        else:  # pending
            return f"""
                {base_style}
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            """
    
    @staticmethod
    def get_phase_counter_style(active: bool = False):
        """Retorna el estilo para contadores de progreso.
        
        Contadores numéricos que muestran progreso de archivos procesados.
        
        Args:
            active: True para fase activa (azul), False para inactiva (gris).
        
        Returns:
            str: Estilo CSS con fuente monoespaciada.
        """
        color = DesignSystem.COLOR_PRIMARY if active else DesignSystem.COLOR_TEXT_SECONDARY
        weight = DesignSystem.FONT_WEIGHT_MEDIUM if active else DesignSystem.FONT_WEIGHT_NORMAL
        return f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {color};
            font-family: {DesignSystem.FONT_FAMILY_MONO};
            line-height: 1.0;
            font-weight: {weight};
        """
    
    @staticmethod
    def get_phase_skipped_counter_style():
        """Retorna el estilo para contador de fase omitida.
        
        Texto en itálica gris para indicar que la fase fue saltada.
        
        Returns:
            str: Estilo CSS con font-style italic.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-family: {DesignSystem.FONT_FAMILY_BASE};
            line-height: 1.0;
            font-style: italic;
        """

    # ==================== ESTILOS DE TEXTO AUXILIARES ====================
    
    @staticmethod
    def get_dropzone_main_text_style():
        """Retorna el estilo para texto principal del dropzone.
        
        Returns:
            str: Estilo CSS para texto destacado.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """
    
    @staticmethod
    def get_dropzone_hint_text_style():
        """Retorna el estilo para hint del dropzone.
        
        Returns:
            str: Estilo CSS para texto secundario/hint.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """
    
    @staticmethod
    def get_analysis_phase_frame_style():
        """Retorna el estilo para frame del widget de fases.
        
        Returns:
            str: Estilo QSS transparente sin borde.
        """
        return f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
        """
    
    @staticmethod
    def get_stats_label_style():
        """Retorna el estilo para labels de estadísticas.
        
        Returns:
            str: Estilo CSS para texto de estadísticas.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """
    
    @staticmethod
    def get_visual_bar_container_style():
        """Retorna el estilo para contenedor de barra visual.
        
        Contenedor con fondo gris para barras de progreso visuales.
        
        Returns:
            str: Estilo QSS para QFrame contenedor.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BORDER_LIGHT};
                border-radius: 4px;
                border: none;
            }}
        """
    
    @staticmethod
    def get_tip_text_style(color: str = None):
        """Retorna el estilo para texto de tips/consejos.
        
        Args:
            color: Color opcional del texto (hex o rgb).
        
        Returns:
            str: Estilo QSS para QLabel de tip.
        """
        text_color = color if color else DesignSystem.COLOR_TEXT_SECONDARY
        return f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {text_color};
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
            }}
        """
    
    @staticmethod
    def get_empty_state_text_style():
        """Retorna el estilo para texto de estado vacío.
        
        Texto placeholder en itálica para secciones sin contenido.
        
        Returns:
            str: Estilo CSS con font-style italic.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-style: italic;
            padding: {DesignSystem.SPACE_16}px 0;
        """
    
    @staticmethod
    def get_info_text_style():
        """Retorna el estilo para texto informativo.
        
        Usado para mostrar información contextual como última
        carpeta analizada.
        
        Returns:
            str: Estilo CSS compacto para información.
        """
        return f"""
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """

    # ==================== ESTILOS TUTORIAL/ABOUT ====================
    
    @staticmethod
    def get_tutorial_tab_widget_style():
        """Retorna el estilo QSS para QTabWidget con pestañas laterales.
        
        Diseñado para diálogos de tutorial/about con navegación lateral compacta.
        Pestañas a la izquierda con iconos y texto corto.
        
        Returns:
            str: Estilo QSS para QTabWidget con tabs west.
        """
        return f"""
            QTabWidget::pane {{
                border: none;
                background-color: {DesignSystem.COLOR_SURFACE};
                border-radius: 0;
            }}
            
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            
            QTabBar {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
            }}
            
            QTabBar::tab {{
                background-color: transparent;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_10}px {DesignSystem.SPACE_12}px;
                border: none;
                border-left: 3px solid transparent;
                margin-bottom: 0px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-width: 100px;
                text-align: left;
            }}
            
            QTabBar::tab:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                color: {DesignSystem.COLOR_PRIMARY};
                border-left: 3px solid {DesignSystem.COLOR_PRIMARY};
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT};
            }}
        """
    
    @staticmethod
    def get_tutorial_feature_card_accent_style(accent_color: str):
        """Retorna el estilo para cards de features con acento de color.
        
        Sin borde exterior, solo el acento lateral.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
                border: none;
                border-left: 4px solid {accent_color};
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_16}px;
            }}
            QFrame:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_SUBTLE};
            }}
        """
    
    @staticmethod
    def get_tutorial_section_header_style():
        """Retorna el estilo para headers de sección en tutoriales.
        
        Returns:
            str: Estilo CSS para títulos de sección.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
            padding-bottom: {DesignSystem.SPACE_8}px;
        """
    
    @staticmethod
    def get_tutorial_highlight_box_style(bg_color: str, border_color: str):
        """Retorna el estilo para cajas destacadas en tutoriales.
        
        Usado para tips, advertencias, información importante.
        """
        return f"""
            QFrame {{
                background-color: {bg_color};
                border: none;
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_16}px;
            }}
        """
    
    @staticmethod
    def get_tutorial_scroll_area_style():
        """Retorna el estilo para scroll areas en tutoriales.
        
        Scroll area transparente con scrollbar estilizada.
        
        Returns:
            str: Estilo QSS para QScrollArea.
        """
        return f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background-color: {DesignSystem.COLOR_BACKGROUND};
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {DesignSystem.COLOR_BORDER};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """

    @staticmethod
    def get_tutorial_step_card_style():
        """Retorna el estilo para cards de pasos numerados en tutoriales.
        
        Card limpia sin bordes, usando el fondo base para contraste.
        También usado para mini cards de herramientas.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
                border: none;
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
            QFrame:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
            }}
        """
    
    @staticmethod
    def get_tutorial_tip_card_style():
        """Retorna el estilo para cards de tips en tutoriales.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                border: none;
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """
    
    # Alias para retrocompatibilidad - idéntico a get_tutorial_step_card_style
    get_tutorial_tool_card_style = get_tutorial_step_card_style
    
    @staticmethod
    def get_tutorial_note_style():
        """Retorna el estilo para notas informativas en tutoriales.
        
        Texto con estilo sutil sin fondo destacado.
        
        Returns:
            str: Estilo QSS para QLabel tipo nota.
        """
        return f"""
            QLabel {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-style: italic;
                padding: {DesignSystem.SPACE_4}px 0px;
            }}
        """

    # ==================== ESTILOS HEADER STAGE ====================
    
    @staticmethod
    def get_stage_header_style():
        """Retorna el estilo para el header moderno de stages.
        
        Header minimalista con gradiente sutil y sombra.
        
        Returns:
            str: Estilo QSS para QFrame header de stage.
        """
        return f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {DesignSystem.COLOR_SURFACE},
                    stop:1 {DesignSystem.COLOR_BACKGROUND});
                border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_20}px;
            }}
        """
    
    @staticmethod
    def get_stage_title_style():
        """Retorna el estilo para el título del header de stages.
        
        Returns:
            str: Estilo CSS para título principal.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_XL}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {DesignSystem.COLOR_TEXT};
            letter-spacing: -0.5px;
        """
    
    @staticmethod
    def get_stage_subtitle_style():
        """Retorna el estilo para el subtítulo del header de stages.
        
        Returns:
            str: Estilo CSS para subtítulo descriptivo.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """
    
    @staticmethod
    def get_stage_badge_style(variant: str = 'default'):
        """Retorna el estilo para badges indicadores de stage.
        
        Args:
            variant: 'default', 'primary', 'success', 'warning'
        
        Returns:
            str: Estilo QSS para QLabel tipo badge.
        """
        colors = {
            'default': (DesignSystem.COLOR_SECONDARY_LIGHT, DesignSystem.COLOR_TEXT_SECONDARY),
            'primary': (DesignSystem.COLOR_PRIMARY_LIGHT, DesignSystem.COLOR_PRIMARY),
            'success': (DesignSystem.COLOR_SUCCESS_BG, DesignSystem.COLOR_SUCCESS),
            'warning': (DesignSystem.COLOR_WARNING_BG, "#856404"),  # Darker warning text
        }
        bg_color, text_color = colors.get(variant, colors['default'])
        
        return f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
                border-radius: {DesignSystem.RADIUS_FULL}px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """

    # ==================== ESTILOS PROGRESS CARD STAGE 2 ====================
    
    @staticmethod
    def get_progress_card_style():
        """Retorna el estilo para la card de progreso de Stage 2.
        
        Returns:
            str: Estilo QSS para QFrame progress card.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_20}px;
            }}
        """
    
    @staticmethod
    def get_progress_header_style():
        """Retorna el estilo para el header de la card de progreso.
        
        Returns:
            str: Estilo CSS para header.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """
    
    @staticmethod
    def get_folder_path_badge_style():
        """Retorna el estilo para el badge de ruta de carpeta.
        
        Returns:
            str: Estilo QSS para QFrame con ruta.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
            }}
        """
    
    @staticmethod
    def get_progress_status_style(status: str = 'running'):
        """Retorna el estilo para el indicador de estado de progreso.
        
        Args:
            status: 'running', 'completed', 'error'
        
        Returns:
            str: Estilo QSS para QFrame status container.
        """
        colors = {
            'running': (f"rgba(13, 110, 253, 0.08)", DesignSystem.COLOR_PRIMARY),
            'completed': (DesignSystem.COLOR_SUCCESS_BG, DesignSystem.COLOR_SUCCESS),
            'error': (DesignSystem.COLOR_DANGER_BG, DesignSystem.COLOR_DANGER),
        }
        bg_color, border_color = colors.get(status, colors['running'])
        
        return f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_16}px;
            }}
        """
    
    @staticmethod
    def get_progress_status_text_style(status: str = 'running'):
        """Retorna el estilo para el texto del estado de progreso.
        
        Args:
            status: 'running', 'completed', 'error'
        
        Returns:
            str: Estilo CSS para texto.
        """
        colors = {
            'running': DesignSystem.COLOR_PRIMARY,
            'completed': DesignSystem.COLOR_SUCCESS,
            'error': DesignSystem.COLOR_DANGER,
        }
        color = colors.get(status, colors['running'])
        
        return f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {color};
        """
    
    @staticmethod
    def get_modern_progressbar_style():
        """Retorna el estilo para barra de progreso moderna.
        
        Returns:
            str: Estilo QSS para QProgressBar moderno.
        """
        return f"""
            QProgressBar {{
                border: none;
                border-radius: {DesignSystem.RADIUS_SM}px;
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                text-align: center;
                height: 6px;
            }}
            
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {DesignSystem.COLOR_PRIMARY},
                    stop:1 {DesignSystem.COLOR_PRIMARY_HOVER});
                border-radius: {DesignSystem.RADIUS_SM}px;
            }}
        """

    # ==================== ESTILOS PHASE WIDGET STAGE 2 ====================
    
    @staticmethod
    def get_phase_item_style(status: str = 'pending'):
        """Retorna el estilo para items de fase con fondo.
        
        Args:
            status: 'pending', 'running', 'completed', 'error', 'skipped'
        
        Returns:
            str: Estilo QSS para QFrame phase item.
        """
        styles = {
            'pending': f"""
                QFrame {{
                    background-color: transparent;
                    border: none;
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                }}
            """,
            'running': f"""
                QFrame {{
                    background-color: rgba(13, 110, 253, 0.06);
                    border: none;
                    border-left: 3px solid {DesignSystem.COLOR_PRIMARY};
                    border-radius: 0px {DesignSystem.RADIUS_BASE}px {DesignSystem.RADIUS_BASE}px 0px;
                    padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                }}
            """,
            'completed': f"""
                QFrame {{
                    background-color: rgba(25, 135, 84, 0.04);
                    border: none;
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                }}
            """,
            'error': f"""
                QFrame {{
                    background-color: rgba(220, 53, 69, 0.06);
                    border: none;
                    border-left: 3px solid {DesignSystem.COLOR_DANGER};
                    border-radius: 0px {DesignSystem.RADIUS_BASE}px {DesignSystem.RADIUS_BASE}px 0px;
                    padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                }}
            """,
            'skipped': f"""
                QFrame {{
                    background-color: transparent;
                    border: none;
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                    opacity: 0.6;
                }}
            """,
        }
        return styles.get(status, styles['pending'])
    
    @staticmethod
    def get_phase_number_style(status: str = 'pending'):
        """Retorna el estilo para número circular de fase.
        
        Args:
            status: 'pending', 'running', 'completed', 'error', 'skipped'
        
        Returns:
            str: Estilo QSS para QLabel número.
        """
        styles = {
            'pending': f"""
                QLabel {{
                    background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                    color: {DesignSystem.COLOR_TEXT_SECONDARY};
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                    min-width: 24px;
                    max-width: 24px;
                    min-height: 24px;
                    max-height: 24px;
                    border-radius: 12px;
                    qproperty-alignment: AlignCenter;
                }}
            """,
            'running': f"""
                QLabel {{
                    background-color: {DesignSystem.COLOR_PRIMARY};
                    color: {DesignSystem.COLOR_PRIMARY_TEXT};
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                    min-width: 24px;
                    max-width: 24px;
                    min-height: 24px;
                    max-height: 24px;
                    border-radius: 12px;
                    qproperty-alignment: AlignCenter;
                }}
            """,
            'completed': f"""
                QLabel {{
                    background-color: {DesignSystem.COLOR_SUCCESS};
                    color: white;
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                    min-width: 24px;
                    max-width: 24px;
                    min-height: 24px;
                    max-height: 24px;
                    border-radius: 12px;
                    qproperty-alignment: AlignCenter;
                }}
            """,
            'error': f"""
                QLabel {{
                    background-color: {DesignSystem.COLOR_DANGER};
                    color: white;
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                    min-width: 24px;
                    max-width: 24px;
                    min-height: 24px;
                    max-height: 24px;
                    border-radius: 12px;
                    qproperty-alignment: AlignCenter;
                }}
            """,
            'skipped': f"""
                QLabel {{
                    background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                    color: {DesignSystem.COLOR_TEXT_SECONDARY};
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                    min-width: 24px;
                    max-width: 24px;
                    min-height: 24px;
                    max-height: 24px;
                    border-radius: 12px;
                    qproperty-alignment: AlignCenter;
                }}
            """,
        }
        return styles.get(status, styles['pending'])
    
    @staticmethod
    def get_phase_title_style(status: str = 'pending'):
        """Retorna el estilo para título de fase.
        
        Args:
            status: 'pending', 'running', 'completed', 'error', 'skipped'
        
        Returns:
            str: Estilo CSS para texto de fase.
        """
        colors = {
            'pending': DesignSystem.COLOR_TEXT_SECONDARY,
            'running': DesignSystem.COLOR_TEXT,
            'completed': DesignSystem.COLOR_SUCCESS,
            'error': DesignSystem.COLOR_DANGER,
            'skipped': DesignSystem.COLOR_TEXT_SECONDARY,
        }
        weights = {
            'pending': DesignSystem.FONT_WEIGHT_NORMAL,
            'running': DesignSystem.FONT_WEIGHT_MEDIUM,
            'completed': DesignSystem.FONT_WEIGHT_MEDIUM,
            'error': DesignSystem.FONT_WEIGHT_MEDIUM,
            'skipped': DesignSystem.FONT_WEIGHT_NORMAL,
        }
        
        return f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {weights.get(status, DesignSystem.FONT_WEIGHT_NORMAL)};
            color: {colors.get(status, DesignSystem.COLOR_TEXT_SECONDARY)};
        """
    
    @staticmethod
    def get_phase_progress_text_style():
        """Retorna el estilo para texto de progreso de fase.
        
        Returns:
            str: Estilo CSS para contador de progreso.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_PRIMARY};
            font-family: {DesignSystem.FONT_FAMILY_MONO};
        """
    
    @staticmethod
    def get_cancel_button_discrete_style():
        """Retorna el estilo para botón de cancelar discreto.
        
        Returns:
            str: Estilo QSS para QPushButton.
        """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_DANGER_BG};
                color: {DesignSystem.COLOR_DANGER};
                border-color: {DesignSystem.COLOR_DANGER};
            }}
        """

    @staticmethod
    def get_tutorial_step_number_style():
        """Estilo para el círculo del número en pasos del tutorial."""
        return f"""
            QLabel {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: white;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
                border-radius: 12px;
                qproperty-alignment: AlignCenter;
            }}
        """

    @staticmethod
    def get_tutorial_card_title_style():
        """Estilo para títulos dentro de cards del tutorial."""
        return f"""
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        """

    @staticmethod
    def get_tutorial_card_desc_style():
        """Estilo para descripciones dentro de cards del tutorial."""
        return f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            line-height: 1.2;
        """

    @staticmethod
    def get_tutorial_static_info_card_style():
        """Estilo para cards informativas estáticas (sin hover)."""
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
                border: none;
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px;
            }}
        """

    @staticmethod
    def get_privacy_hero_style():
        """Estilo para el contenedor principal de privacidad (Hero)."""
        return f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(25, 135, 84, 0.05), stop:1 rgba(13, 110, 253, 0.05));
                border: 1px solid rgba(25, 135, 84, 0.1);
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_16}px;
            }}
        """

    @staticmethod
    def get_privacy_item_style():
        """Estilo para items de privacidad en la lista vertical."""
        return f"""
            QFrame {{
                background-color: transparent;
                border: none;
                padding: {DesignSystem.SPACE_8}px 0px;
            }}
        """
