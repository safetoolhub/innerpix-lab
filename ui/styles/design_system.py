"""
Design System para Pixaro Lab
Tokens CSS centralizados para garantizar coherencia visual
"""


class DesignSystem:
    """Design system centralizado con todos los tokens de diseño"""
    
    # ==================== COLORES ====================
    
    # Colores base
    COLOR_BACKGROUND = "#f5f5f5"
    COLOR_SURFACE = "#ffffff"
    COLOR_TEXT = "#1a1a1a"
    COLOR_TEXT_SECONDARY = "#666666"
    
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
    COLOR_ERROR = "#ef4444"
    
    # Backgrounds adicionales
    COLOR_BG_1 = "#fafafa"
    COLOR_BG_2 = "#f0f0f0"
    COLOR_BG_4 = "#fef3c7"  # Warning background
    
    # ==================== TIPOGRAFÍA ====================
    
    FONT_FAMILY_BASE = "Segoe UI, -apple-system, BlinkMacSystemFont, Roboto, sans-serif"
    FONT_FAMILY_MONO = "Consolas, Monaco, 'Courier New', monospace"
    
    FONT_SIZE_SM = 12
    FONT_SIZE_BASE = 14
    FONT_SIZE_MD = 14
    FONT_SIZE_LG = 16
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
    SPACE_12 = 12
    SPACE_16 = 16
    SPACE_20 = 20
    SPACE_24 = 24
    SPACE_32 = 32
    SPACE_40 = 40
    SPACE_48 = 48
    
    # ==================== BORDER RADIUS ====================
    
    RADIUS_BASE = 8
    RADIUS_LG = 12
    RADIUS_FULL = 9999
    
    # ==================== SOMBRAS ====================
    
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
    def apply_card_shadow(widget, hover=False):
        """
        Aplica efecto de sombra a un widget tipo card
        """
        shadow = f"0 4px 6px rgba(0, 0, 0, {'0.07' if not hover else '0.12'})"
        widget.setGraphicsEffect(None)  # PyQt no soporta CSS shadows directamente
    
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
    def get_tooltip_style():
        """
        Retorna el estilo QSS para tooltips
        """
        return f"""
            QToolTip {{
                background-color: {DesignSystem.COLOR_TEXT};
                color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
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
