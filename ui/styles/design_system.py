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

    
    # Colores primarios (Azul vibrante pero profesional)
    COLOR_PRIMARY = "#0D6EFD"
    COLOR_PRIMARY_HOVER = "#0B5ED7"
    COLOR_PRIMARY_ACTIVE = "#0A58CA"
    COLOR_PRIMARY_LIGHT = "#E7F1FF"  # Para fondos sutiles
    COLOR_PRIMARY_SUBTLE = "rgba(37, 99, 235, 0.02)"  # Para fondos muy sutiles (hover cards)
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
    
    # ==================== LEGACY / COMPATIBILITY ====================
    # Aliases maintained for backward compatibility with existing dialogs
    
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
        Estilo Material Design: fondo oscuro, texto claro, sombra elegante
        """
        return f"""
            QToolTip {{
                background-color: rgba(97, 97, 97, 0.95);
                color: #FFFFFF;
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                font-family: {DesignSystem.FONT_FAMILY_BASE};
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
        Retorna el estilo QSS completo para ComboBox Material Design Premium
        Incluye el dropdown y los items del menú con un look moderno y espacioso
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
        """
        Retorna el estilo QSS para barras de progreso
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
        Material Design: hover más oscuro para mejor feedback visual
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
        Material Design: hover sutil con fondo claro
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
            QPushButton:disabled {{
            background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            border: 1px solid {DesignSystem.COLOR_BORDER};
        }}
        """
    
    @staticmethod
    def get_icon_button_style():
        """
        Estilo para botones de icono (QToolButton) en header.
        Material Design: hover sutil con fondo claro, no opaco.
        Ejemplo: Botones de configuración y about en el header.
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
        """
        Estilo para el badge de información en las cards.
        Fondo transparente por defecto, azul claro al hover para mantener contraste con el icono azul.
        """
        return f"""
            QLabel {{
                background-color: transparent;
                border-radius: 10px;
            }}
            QLabel:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
            }}
        """

    # ==================== CARDS Y CONTENEDORES ====================
    
    @staticmethod
    def get_card_style():
        """
        Estilo base para cards (QFrame).
        Usado en: summary_card, progress_card, folder_selection_card, header_card, etc.
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
        """
        Estilo para cards más compactas con menos padding.
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
        """
        Estilo para la card de header de la aplicación.
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
    def get_stale_banner_style():
        """
        Estilo para banner de advertencia (estadísticas desactualizadas).
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
        """
        Estilo para botón de acción en banners de advertencia.
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
    
    # ==================== LABELS Y TEXTO ====================
    
    @staticmethod
    def get_label_title_style():
        """
        Estilo para títulos principales (welcome title, header title).
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {DesignSystem.COLOR_TEXT};
        """
    
    @staticmethod
    def get_label_subtitle_style():
        """
        Estilo para subtítulos.
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
        """
        Estilo para texto monoespaciado (rutas, código).
        """
        return f"""
            font-family: {DesignSystem.FONT_FAMILY_MONO};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """
    
    @staticmethod
    def get_label_secondary_style():
        """
        Estilo para texto secundario (hints, descripciones cortas).
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """
    
    @staticmethod
    def get_section_title_style():
        """
        Estilo para títulos de sección (categorías de herramientas).
        """
        return f"""
            font-size: 10px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            letter-spacing: 0.5px;
        """
    
    # ==================== SEPARADORES ====================
    
    @staticmethod
    def get_separator_style():
        """
        Estilo para líneas separadoras horizontales.
        """
        return f"background-color: {DesignSystem.COLOR_BORDER};"
    
    # ==================== DROPZONE ====================
    
    @staticmethod
    def get_dropzone_style(dragging: bool = False):
        """
        Estilo para el widget de dropzone.
        
        Args:
            dragging: Si el usuario está arrastrando algo sobre el widget
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
        """
        Estilo para las cards de herramientas en el grid.
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
        """
        Estilo para el botón de acción dentro de las tool cards.
        Incluye clases para estados: primary (azul), warning (ámbar).
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
        """
        Estilo para badges de estado en tool cards.
        
        Args:
            bg_color: Color de fondo del badge
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
        """
        Estilo para QSpinBox personalizado.
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
    
    # ==================== BOTONES SECUNDARIOS PEQUEÑOS ====================
    
    @staticmethod
    def get_secondary_small_button_style():
        """
        Estilo para botones secundarios pequeños (badges, acciones menores).
        """
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
    def get_cancel_button_style():
        """
        Estilo para botones de cancelar (discretos).
        """
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
    
    @staticmethod
    def get_link_button_style():
        """
        Estilo para botones que parecen links (Reanalizar, etc).
        """
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
    
    @staticmethod
    def get_last_folder_container_style():
        """
        Estilo para el contenedor de última carpeta analizada.
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
        """
        Estilo para botón "Usar esta carpeta".
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
    
    # ==================== PHASE WIDGET ====================
    
    @staticmethod
    def get_phase_text_style(status: str = 'pending'):
        """
        Estilo para texto de fases de análisis.
        
        Args:
            status: 'pending', 'running', 'completed', 'error', 'skipped'
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
        """
        Estilo para contadores de progreso de fases.
        
        Args:
            active: Si la fase está activa (azul) o no (gris)
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
        """
        Estilo para contador de fase omitida.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-family: {DesignSystem.FONT_FAMILY_BASE};
            line-height: 1.0;
            font-style: italic;
        """

    # ==================== ESTILOS DE TEXTO GENÉRICOS ====================
    
    @staticmethod
    def get_dropzone_main_text_style():
        """
        Estilo para texto principal del dropzone.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """
    
    @staticmethod
    def get_dropzone_hint_text_style():
        """
        Estilo para texto secundario (hint) del dropzone.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """
    
    @staticmethod
    def get_analysis_phase_frame_style():
        """
        Estilo para el frame del widget de fases de análisis.
        """
        return f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
        """
    
    @staticmethod
    def get_analysis_phase_header_style():
        """
        Estilo para el header del widget de fases de análisis.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """
    
    @staticmethod
    def get_stats_label_style():
        """
        Estilo para labels de estadísticas.
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """
    
    @staticmethod
    def get_visual_bar_container_style():
        """
        Estilo para el contenedor de la barra visual de estadísticas.
        """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BORDER_LIGHT};
                border-radius: 4px;
                border: none;
            }}
        """
    
    @staticmethod
    def get_status_label_style(state: str = 'normal'):
        """
        Estilo para labels de estado (ej: "Analizando...", "Completado").
        
        Args:
            state: 'normal', 'success'
        """
        if state == 'success':
            return f"""
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_SUCCESS};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            """
        else:
            return f"""
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
            """
    
    @staticmethod
    def get_tip_text_style(color: str = None):
        """
        Estilo para texto de tips/consejos.
        
        Args:
            color: Color opcional del texto
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
        """
        Estilo para texto de estado vacío (placeholder).
        """
        return f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-style: italic;
            padding: {DesignSystem.SPACE_16}px 0;
        """
    
    @staticmethod
    def get_info_text_style():
        """
        Estilo para texto informativo (ej: última carpeta analizada).
        """
        return f"""
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """
