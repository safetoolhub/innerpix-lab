"""
Design System para Pixaro Lab
Tokens CSS centralizados para garantizar coherencia visual
"""


class DesignSystem:
    """Design system centralizado con todos los tokens de diseño"""
    
    # ==================== COLORES ====================
    
    # Colores base
    COLOR_BACKGROUND = "#f5f5f5"
    COLOR_BACKGROUND_PRIMARY = "#f5f5f5"
    COLOR_BACKGROUND_SECONDARY = "#ffffff"
    COLOR_SURFACE = "#ffffff"
    COLOR_TEXT = "#1a1a1a"
    COLOR_TEXT_SECONDARY = "#666666"
    COLOR_TEXT_PRIMARY = "#1a1a1a"
    
    # Colores primarios
    COLOR_PRIMARY = "#2563eb"
    COLOR_PRIMARY_HOVER = "#1d4ed8"
    COLOR_PRIMARY_TEXT = "#ffffff"
    
    # Color de acento para avisos resaltados
    COLOR_ACCENT = "#3b82f6"
    
    # Colores secundarios
    COLOR_SECONDARY = "#e5e7eb"
    COLOR_SECONDARY_HOVER = "#d1d5db"
    
    # Bordes
    COLOR_BORDER = "#e5e7eb"
    COLOR_CARD_BORDER = "#d1d5db"
    
    # Estados
    COLOR_SUCCESS = "#10b981"
    COLOR_WARNING = "#f59e0b"
    COLOR_WARNING_HOVER = "#d97706"
    COLOR_DANGER = "#dc4a26"
    COLOR_ERROR = "#ef4444"
    COLOR_INFO = "#3b82f6"
    
    # Backgrounds adicionales
    COLOR_BG_1 = "#fafafa"
    COLOR_BG_2 = "#f0f0f0"
    COLOR_BG_4 = "#fef3c7"  # Warning background    
    COLOR_SURFACE_DISABLED = "#f9fafb"  # Fondo más oscuro para estados deshabilitados
    
    # ==================== TIPOGRAFÍA ====================
    
    FONT_FAMILY_BASE = "Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif"
    FONT_FAMILY_MONO = "Consolas, Monaco, 'Courier New', monospace"
    
    FONT_SIZE_XS = 10
    FONT_SIZE_SMALL = 10
    FONT_SIZE_SM = 12
    FONT_SIZE_BASE = 14
    FONT_SIZE_BODY = 14
    FONT_SIZE_MD = 14
    FONT_SIZE_LG = 16
    FONT_SIZE_H3 = 18
    FONT_SIZE_XL = 18
    FONT_SIZE_2XL = 20
    FONT_SIZE_3XL = 24
    
    FONT_WEIGHT_NORMAL = 400
    FONT_WEIGHT_MEDIUM = 500
    FONT_WEIGHT_SEMIBOLD = 550
    FONT_WEIGHT_BOLD = 600
    
    LINE_HEIGHT_NORMAL = 1.5
    LINE_HEIGHT_RELAXED = 1.75
    
    # ==================== ESPACIADO ====================

    SPACE_2 = 2
    SPACE_4 = 4
    SPACE_6 = 6
    SPACE_8 = 8
    SPACE_10 = 10
    SPACE_12 = 12
    SPACE_16 = 16
    SPACE_XS = 2
    SPACE_SM = 12    
    SPACE_MD = 16
    SPACE_20 = 20
    SPACE_24 = 24
    SPACE_32 = 32
    SPACE_40 = 40
    SPACE_48 = 48
    SPACE_LG = 56
    SPACE_XL = 64
    
# ==================== BORDER RADIUS ====================

    RADIUS_BASE = 8
    RADIUS_SMALL = 4
    RADIUS_LG = 12
    RADIUS_MEDIUM = 14
    RADIUS_LARGE = 16
    RADIUS_FULL = 9999    # ==================== SOMBRAS ====================
    
    SHADOW_SM = "0 1px 2px rgba(0, 0, 0, 0.05)"
    SHADOW_MD = "0 4px 6px rgba(0, 0, 0, 0.07)"
    SHADOW_LG = "0 10px 15px rgba(0, 0, 0, 0.1)"
    
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
    
    # ==================== ICONOS ====================
    
    ICON_SIZE_SM = 16
    ICON_SIZE_MD = 18
    ICON_SIZE_LG = 22
    ICON_SIZE_XL = 24
    
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
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT};
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_20}px;
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px {DesignSystem.RADIUS_BASE}px 0 0;
                margin-right: {DesignSystem.SPACE_4}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-width: 80px;
                text-align: center;
            }}
            
            QTabBar::tab:selected {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                border-bottom: 2px solid {DesignSystem.COLOR_PRIMARY};
            }}
            
            QTabBar::tab:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
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
    def get_combobox_style():
        """
        Estilo para QComboBox con Material Design.
        Elimina bordes negros problemáticos en el popup desplegable.
        """
        return f"""
            QComboBox {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                min-height: 20px;
            }}
            
            QComboBox:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            
            QComboBox:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            
            /* Estilo del popup desplegable - elimina bordes negros */
            QComboBox QAbstractItemView {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                selection-background-color: {DesignSystem.COLOR_PRIMARY};
                selection-color: {DesignSystem.COLOR_PRIMARY_TEXT};
                outline: none;
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                border: none;
                min-height: 20px;
            }}
            
            QComboBox QAbstractItemView::item:hover {{
                background-color: {DesignSystem.COLOR_BG_2};
            }}
            
            QComboBox QAbstractItemView::item:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
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
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
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
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
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
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border-color: {DesignSystem.COLOR_SECONDARY};
            }}
        """

    # ==================== LEGACY CONSTANTS (TO BE REVIEWED) ====================
    # These constants are migrated from ui_styles.py and need to be reviewed/updated
    # TODO: Review and modernize these legacy styles to use DesignSystem tokens
    
    # Legacy button styles (DEPRECATED - usar get_danger_button_style())
    STYLE_DANGER_BUTTON = """
    QPushButton {
        background-color: #dc3545;
        color: white;
        padding: 8px 20px;
        border-radius: 4px;
        border: none;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: #c82333;
    }
    QPushButton:pressed {
        background-color: #bd2130;
    }
    QPushButton:disabled {
        background-color: #6c757d;
        color: #ffffff;
    }
    """
    
    # Legacy dialog styles
    STYLE_DIALOG_SEPARATOR = "color: #dee2e6;"
    STYLE_DIALOG_COUNTER_BOLD = "font-weight: bold; color: #2c5aa0; margin-left: 10px;"
    STYLE_DIALOG_PAGINATION_FRAME = "QFrame { background-color: #f0f0f0; border-radius: 3px; }"
    STYLE_DIALOG_PAGE_LABEL = "font-weight: bold; padding: 0 20px;"
    STYLE_DIALOG_PROBLEM_INFO = "color: #fd7e14; font-size: 10px;"
    STYLE_DIALOG_PROBLEM_TEXT = "font-size: 10px; color: #6c757d;"
    STYLE_DIALOG_OPTIONS_GROUP = "QGroupBox { font-weight: bold; }"
    
    # Legacy panel and label styles
    STYLE_PANEL_LABEL = "padding: 8px; background-color: #f8f9fa; border-radius: 4px;"
    STYLE_DIALOG_WARNING_ORANGE = "color: #fd7e14; padding: 5px; font-weight: bold;"
    STYLE_DIALOG_NO_PREVIEW = "color: #6c757d; font-size: 10px; font-style: italic;"
    STYLE_DIALOG_NAME_LABEL = "font-size: 11px; color: #212529; background: transparent;"
    STYLE_DIALOG_DETAILS_LABEL = "font-size: 9px; color: #6c757d; background: transparent;"
    STYLE_DIALOG_TITLE_BOLD = "font-weight: bold; font-size: 14px; color: #212529;"
    STYLE_DIALOG_DESC_MUTED = "color: #6c757d; font-size: 11px; padding: 5px;"
    STYLE_DIALOG_LABEL_DISABLED = "border: 1px solid #adb5bd; background-color: #e9ecef;"
    
    # Legacy colors (RGB values for QColor usage)
    COLOR_CONFLICT_BG = "#ffc107"  # RGB: 255, 193, 7
    COLOR_SUCCESS_BG = "#4caf50"   # RGB: 76, 175, 80
