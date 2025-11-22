"""
Design System para Pixaro Lab
Tokens CSS centralizados para garantizar coherencia visual
"""


class DesignSystem:
    """Design system centralizado con todos los tokens de diseño"""    
  
    # ==================== COLORES MODERNOS ====================
    
    # Colores base
    COLOR_BACKGROUND = "#F8F9FA"  # Gris muy claro, más moderno que #f5f5f5
    COLOR_SURFACE = "#FFFFFF"
    COLOR_TEXT = "#212529"
    COLOR_TEXT_SECONDARY = "#6C757D"
    COLOR_TEXT_TERTIARY = "#ADB5BD"
    
    # Colores primarios (Azul vibrante pero profesional)
    COLOR_PRIMARY = "#0D6EFD"
    COLOR_PRIMARY_HOVER = "#0B5ED7"
    COLOR_PRIMARY_ACTIVE = "#0A58CA"
    COLOR_PRIMARY_LIGHT = "#E7F1FF"  # Para fondos sutiles
    COLOR_PRIMARY_TEXT = "#FFFFFF"
    
    # Colores secundarios (Gris neutro)
    COLOR_SECONDARY = "#6C757D"
    COLOR_SECONDARY_HOVER = "#5C636A"
    COLOR_SECONDARY_LIGHT = "#E9ECEF"
    
    # Estados semánticos
    COLOR_SUCCESS = "#198754"
    COLOR_SUCCESS_BG = "#D1E7DD"
    COLOR_WARNING = "#FFC107"
    COLOR_WARNING_BG = "#FFF3CD"
    COLOR_DANGER = "#DC3545"
    COLOR_DANGER_HOVER = "#BB2D3B"
    COLOR_DANGER_BG = "#F8D7DA"
    COLOR_INFO = "#0DCAF0"
    COLOR_INFO_BG = "#CFF4FC"
    
    # Bordes
    COLOR_BORDER = "#DEE2E6"
    COLOR_BORDER_LIGHT = "#E9ECEF"
    COLOR_CARD_BORDER = "#DEE2E6"  # Alias for backward compatibility
    
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
    RADIUS_FULL = 9999    # ==================== SOMBRAS ====================
    
    SHADOW_SM = "0 1px 2px rgba(0,0,0,0.05)"
    SHADOW_MD = "0 4px 6px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1)"
    SHADOW_LG = "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05)"
    
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
    
    # ==================== LEGACY / COMPATIBILITY ====================
    # Aliases maintained for backward compatibility with existing dialogs
    
    COLOR_ACCENT = COLOR_PRIMARY
    COLOR_BG_1 = COLOR_BACKGROUND
    COLOR_BG_2 = COLOR_SECONDARY_LIGHT
    COLOR_BG_4 = COLOR_WARNING_BG
    COLOR_SURFACE_DISABLED = COLOR_SECONDARY_LIGHT
    COLOR_ERROR = COLOR_DANGER
    
    LINE_HEIGHT_NORMAL = 1.5
    LINE_HEIGHT_RELAXED = 1.75
    
    RADIUS_SMALL = RADIUS_SM
    
    # ==================== ICONOS ====================
    
    ICON_SIZE_SM = 16
    ICON_SIZE_MD = 20
    ICON_SIZE_LG = 24
    ICON_SIZE_XL = 32
    
    # ==================== MÉTODOS DE AYUDA ====================
    
    @staticmethod
    def get_stylesheet():
        """
        Retorna el stylesheet QSS global de la aplicación
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
    def get_tooltip_style():
        """
        Retorna el estilo QSS para tooltips de manera centralizada
        TODOS los tooltips de la aplicación deben usar este estilo
        """
        return f"""
            QToolTip {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
            }}
        """
    
    @staticmethod
    def get_tab_widget_style():
        """
        Retorna el estilo QSS para widgets de pestañas (QTabWidget)
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
        """
        Retorna el estilo QSS para menús contextuales (QMenu) Material Design
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
        """
        Retorna el estilo QSS completo para ComboBox Material Design
        Incluye el dropdown y los items del menú
        """
        return f"""
            QComboBox {{
                padding: {DesignSystem.SPACE_8}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                background-color: {DesignSystem.COLOR_SURFACE};
                min-height: 28px;
            }}
            
            QComboBox:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            
            QComboBox:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 30px;
                padding-right: {DesignSystem.SPACE_8}px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px;
                selection-background-color: {DesignSystem.COLOR_BG_2};
                selection-color: {DesignSystem.COLOR_TEXT};
                outline: none;
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                border-radius: {DesignSystem.RADIUS_SMALL}px;
                margin: {DesignSystem.SPACE_2}px;
                min-height: 24px;
            }}
            
            QComboBox QAbstractItemView::item:hover {{
                background-color: {DesignSystem.COLOR_BG_2};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QComboBox QAbstractItemView::item:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
            }}
        """

    @staticmethod
    def get_progressbar_style():
        """
        Retorna el estilo QSS para barras de progreso
        """
        return f"""
            QProgressBar {{
                border: none;
                border-radius: {DesignSystem.RADIUS_FULL}px;
                background-color: {DesignSystem.COLOR_SECONDARY};
                text-align: center;
                height: 8px;
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
        """
        Retorna el estilo consistente para checkboxes
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
    def get_spinbox_style():
        """
        Retorna el estilo consistente para spinboxes
        """
        return f"""
            QSpinBox {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                min-height: 32px;
                min-width: 80px;
            }}
            QSpinBox:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QSpinBox:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background-color: transparent;
                border: none;
                width: 20px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                border-radius: {DesignSystem.RADIUS_SM}px;
            }}
            QSpinBox::up-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 4px solid {DesignSystem.COLOR_TEXT};
            }}
            QSpinBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {DesignSystem.COLOR_TEXT};
            }}
        """

    @staticmethod
    def get_lineedit_style():
        """
        Retorna el estilo consistente para QLineEdit
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

    # ==================== BOTONES DE ACCIÓN (MATERIAL DESIGN) ====================
    
    @staticmethod
    def get_primary_button_style():
        """
        Estilo para botón primario (acción principal).
        Ejemplo: "Organizar Archivos", "Proceder", "Eliminar Ahora"
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
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """
    
    @staticmethod
    def get_danger_button_style():
        """
        Estilo para botón de acción destructiva.
        Ejemplo: "Eliminar", "Borrar Archivos"
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
                background-color: {DesignSystem.COLOR_ERROR};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_DANGER};
            }}
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """
    
    @staticmethod
    def get_secondary_button_style():
        """
        Estilo para botón secundario (cancelar, cerrar).
        Ejemplo: "Cancelar"
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
                background-color: {DesignSystem.COLOR_SECONDARY};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
            }}
            QPushButton:disabled {{
            background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            border: 1px solid {DesignSystem.COLOR_BORDER};
        }}
        """
