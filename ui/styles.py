"""
UI Styles para Pixaro Lab
Contiene todas las definiciones de estilos CSS para la interfaz
"""

# ============================================================================
# PALETA DE COLORES CENTRALIZADA
# ============================================================================

COLORS = {
    # Colores primarios
    'primary': '#2196F3',
    'primary_hover': '#1976D2',
    'primary_pressed': '#0D47A1',
    'primary_light': '#64B5F6',
    
    # Colores de estado
    'success': '#28a745',
    'success_hover': '#218838',
    'success_pressed': '#1e7e34',
    'success_light': '#d4edda',
    
    'danger': '#dc3545',
    'danger_hover': '#c82333',
    'danger_light': '#f8d7da',
    'danger_border': '#f5c6cb',
    
    'warning': '#ffc107',
    'warning_hover': '#e0a800',
    'warning_pressed': '#d39e00',
    'warning_light': '#fff3cd',
    'warning_dark': '#856404',
    'warning_border': '#ffeeba',
    
    'info': '#17a2b8',
    'info_hover': '#138496',
    'info_pressed': '#0f6674',
    'info_light': '#e7f3ff',
    'info_border': '#b3d9ff',
    
    # Colores de UI
    'blue': '#007bff',
    'blue_hover': '#0056b3',
    'blue_pressed': '#004085',
    'blue_light': '#0066cc',
    
    'cyan': '#17a2b8',
    'orange': '#FFA500',
    'green': '#28a745',
    
    # Grises y neutrales
    'text_primary': '#212529',
    'text_secondary': '#495057',
    'text_muted': '#6c757d',
    'text_light': '#7F8C8D',
    'text_dark': '#2c3e50',
    'text_darker': '#2C3E50',
    'text_danger': '#721c24',
    
    # Bordes
    'border_light': '#dee2e6',
    'border_medium': '#ced4da',
    'border_dark': '#adb5bd',
    'border_info': '#d1e3f5',
    'border_success': '#c3e6cb',
    'border_danger': '#f5c6cb',
    
    # Fondos
    'bg_white': '#ffffff',
    'bg_light': '#f8f9fa',
    'bg_lighter': '#f8fafc',
    'bg_medium': '#e9ecef',
    'bg_dark': '#e9eef4',
    'bg_info': '#e7f3ff',
    'bg_info_alt': '#f5f8fc',
    'bg_success': '#f4fcf7',
    'bg_warning': '#fff3cd',
    'bg_danger': '#f8d7da',
    'bg_disabled': '#BDBDBD',
    'bg_gray': '#F5F5F5',
    'bg_card': '#F8F9FA',
    
    # Colores específicos
    'gray': 'gray',
    'gray_light': '#CCC',
    'gray_medium': '#DDD',
    'red_light': '#FF6B6B',
    'red_bg': '#FFE5E5',
    'disabled_text': '#EEEEEE',
    'disabled_bg': '#757575',
}

# ============================================================================
# ESTILOS DE BOTONES PRINCIPALES
# ============================================================================

STYLE_CONFIG_BUTTON = f"""
    QPushButton {{
        background-color: transparent;
        color: {COLORS['text_muted']};
        border: 1px solid {COLORS['border_light']};
        border-radius: 20px;
        padding: 5px;
        font-size: 18px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['bg_light']};
        border-color: {COLORS['border_dark']};
        color: {COLORS['text_secondary']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['bg_medium']};
    }}
"""

STYLE_BROWSE_BUTTON = f"""
    QPushButton {{
        background-color: {COLORS['blue']};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton:hover {{
        background-color: {COLORS['blue_hover']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['blue_pressed']};
    }}
"""

STYLE_ANALYZE_BUTTON = f"""
    QPushButton {{
        background-color: {COLORS['primary']};
        color: white;
        border: none;
        border-radius: 12px;
        padding: 20px 40px;
        font-size: 18px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['primary_hover']};
        padding: 20px 40px;
    }}
    QPushButton:pressed {{
        background-color: {COLORS['primary_pressed']};
        padding: 20px 40px;
    }}
    QPushButton:focus {{
        outline: none;
        border: 3px solid {COLORS['primary_light']};
        padding: 17px 37px;
    }}
    QPushButton:disabled {{
        background-color: {COLORS['bg_disabled']};
        color: {COLORS['disabled_text']};
        padding: 20px 40px;
    }}
"""

STYLE_COLLAPSE_BUTTON = """
    QPushButton {
        background-color: transparent;
        border: 1px solid #ced4da;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
        color: #495057;
    }
    QPushButton:hover {
        background-color: #e9ecef;
        border-color: #adb5bd;
    }
"""

STYLE_MENU_BUTTON = """
    QPushButton {
        background-color: transparent;
        color: #6c757d;
        border: 2px solid #dee2e6;
        border-radius: 8px;
        padding: 0px;
        font-size: 22px;
        font-weight: bold;
        text-align: center;
        qproperty-iconSize: 0px 0px;
    }
    QPushButton:hover {
        background-color: #f8f9fa;
        border-color: #adb5bd;
    }
    QPushButton:pressed {
        background-color: #e9ecef;
    }
    QPushButton::menu-indicator {
        image: none;
        width: 0px;
    }
"""

# Estilo para menús contextuales / QMenu del header
STYLE_MENU = """
    QMenu {
        background-color: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 4px;
    }
    QMenu::item {
        padding: 8px 24px 8px 12px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #f8f9fa;
    }
"""

# Contenedor del selector de directorio en la barra de búsqueda
STYLE_SEARCH_CONTAINER = """
    QFrame {
        background-color: white;
        border: 2px solid #dee2e6;
        border-radius: 12px;
        padding: 4px;
    }
"""

# Icono de carpeta del search bar (decorativo, no clickeable)
STYLE_FOLDER_ICON = """
    font-size: 18px; 
    padding-top: 2px; 
    color: #adb5bd;
    opacity: 0.7;
"""

# Estilo específico para el QLineEdit readonly usado en la barra de búsqueda
STYLE_DIRECTORY_EDIT_READONLY = """
    QLineEdit {
        border: none;
        background: transparent;
        font-size: 14px;
        color: #495057;
        padding: 8px 4px;
    }
    QLineEdit[readOnly="true"] {
        color: #6c757d;
    }
"""

# Botón principal de seleccionar y analizar (estilo específico usado en header)
STYLE_ANALYZE_BUTTON_PRIMARY = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #2196F3, stop:1 #1976D2);
        color: white;
        border: none;
        border-radius: 21px;
        padding: 10px 32px;
        font-size: 14px;
        font-weight: 600;
        letter-spacing: 0.3px;
        min-width: 200px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #1E88E5, stop:1 #0D47A1);
        padding: 10px 32px;
    }
    QPushButton:pressed {
        background-color: #0D47A1;
        padding: 10px 30px;
    }
    QPushButton:disabled {
        background-color: #BDBDBD;
        color: #EEEEEE;
    }
"""

# Contenedor transparente para acciones (sin fondo ni borde)
STYLE_ACTIONS_CONTAINER = "background: transparent; border: none;"

STYLE_BROWSE_LOGS_BUTTON = """
    QPushButton {
        background-color: transparent;
        color: #007bff;
        border: 1px solid #007bff;
        border-radius: 4px;
        padding: 5px 10px;
        text-align: left;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #007bff;
        color: white;
    }
"""

STYLE_OPEN_LOGS_BUTTON = """
    QPushButton {
        background-color: transparent;
        color: #007bff;
        border: 1px solid #007bff;
        border-radius: 4px;
        padding: 4px 8px;
        text-align: left;
    }
    QPushButton:hover {
        background-color: #007bff;
        color: white;
    }
"""

STYLE_ABOUT_BUTTON = """
    QPushButton {
        background-color: transparent;
        border: 1px solid #007bff;
        border-radius: 4px;
        padding: 4px 12px;
        color: #007bff;
    }
    QPushButton:hover {
        background-color: #007bff;
        color: white;
    }
"""

# ============================================================================
# ESTILOS DE LABELS
# ============================================================================

STYLE_TITLE_LABEL = "font-size: 20px; font-weight: bold; color: #2c3e50; padding: 10px;"

STYLE_TAB_TITLE = f"font-size: 20px; font-weight: 600; color: {COLORS['text_primary']}; margin-bottom: 8px;"

STYLE_DIR_LABEL = f"font-weight: bold; font-size: 13px; color: {COLORS['text_secondary']};"

STYLE_RESULTS_LABEL = "font-weight: bold; color: #2c3e50; padding-top: 10px;"

STYLE_CONFIG_TITLE = """
    font-weight: bold;
    font-size: 14px;
    color: #2c3e50;
    padding: 5px;
"""

STYLE_INFO_LABEL = "color: #6c757d; padding: 10px; font-style: italic;"

STYLE_SUMMARY_TITLE = "font-size: 16px; font-weight: bold; color: #2c3e50; padding: 5px;"

STYLE_STATS_LABEL_BOLD = "font-weight: bold; color: #495057;"

STYLE_STATS_LABEL = "color: #6c757d; padding: 2px;"

STYLE_CATEGORY_LABEL = "color: #6c757d; padding: 3px;"

STYLE_PROGRESS_LABEL = "font-weight: bold; color: #2c3e50;"

STYLE_INFO_ICON = "font-size: 20px;"

STYLE_SEPARATOR = "background-color: #dee2e6;"

#STYLE_STATS_DIRECTORY = """
#font-weight: bold;
#color: #007bff;
#text-decoration: underline;
#"""

# ============================================================================
# ESTILOS DE INPUT FIELDS
# ============================================================================

STYLE_DIRECTORY_EDIT = """
    QLineEdit {
        padding: 6px 10px;
        border: 1px solid #ced4da;
        border-radius: 4px;
        background-color: #f8f9fa;
        font-size: 13px;
        color: #495057;
    }
"""

# ============================================================================
# ESTILOS DE COMBOBOX
# ============================================================================

STYLE_LOG_LEVEL_COMBO = """
    QComboBox {
        padding: 4px 8px;
        border: 1px solid #ced4da;
        border-radius: 4px;
        font-size: 12px;
    }
"""

# ============================================================================
# ESTILOS DE CHECKBOXES
# ============================================================================

STYLE_CHECKBOX = "font-size: 12px;"

STYLE_RADIO_BUTTON = "QRadioButton { font-size: 13px; color: #495057; }"

STYLE_RADIO_BUTTON_BOLD = "font-weight: 500; font-size: 14px;"

# ============================================================================
# ESTILOS DE PANELS Y FRAMES
# ============================================================================

STYLE_GROUPBOX_STANDARD = f"""
    QGroupBox {{
        font-weight: 600;
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border_light']};
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 20px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
        background: white;
    }}
"""

STYLE_GROUPBOX_WARNING = f"""
    QGroupBox {{
        font-weight: 600;
        color: {COLORS['danger']};
        border: 2px solid {COLORS['danger_border']};
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 24px;
        background: {COLORS['danger_light']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
        background: {COLORS['danger_light']};
    }}
"""

# Estilo de advertencia suave (información importante pero no alarmante)
STYLE_GROUPBOX_INFO = f"""
    QGroupBox {{
        font-weight: 600;
        color: {COLORS['info']};
        border: 2px solid {COLORS['info_border']};
        border-radius: 8px;
        margin-top: 0px;
        padding-top: 0px;
        background: {COLORS['info_light']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
        background: {COLORS['info_light']};
    }}
"""

# Estilo para QGroupBox en diálogos de configuración (títulos más anchos para emojis)
STYLE_GROUPBOX_SETTINGS = f"""
    QGroupBox {{
        font-weight: 600;
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border_light']};
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 20px;
        padding-left: 10px;
        padding-right: 10px;
        padding-bottom: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 12px 0 8px;
        background: white;
        min-width: 150px;
    }}
"""

STYLE_CONFIG_PANEL = """
    QFrame {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 6px;
        padding: 15px;
    }
"""

STYLE_SAFETY_SECTION = """
    QFrame {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 6px;
        padding: 10px;
    }
"""

STYLE_CONFIG_CONTAINER = """
    QFrame {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 6px;
        padding: 8px;
    }
"""

STYLE_DIR_SECTION = """
    QFrame {
        background-color: white;
        border: 1px solid #dee2e6;
        border-radius: 6px;
        padding: 12px;
    }
"""

STYLE_INFO_SECTION = """
    QFrame {
        background-color: #e7f3ff;
        border: 1px solid #b3d9ff;
        border-radius: 6px;
        padding: 8px;
    }
"""

STYLE_SUMMARY_PANEL = """
    QFrame {
        background-color: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 8px;
        padding: 10px;
    }
"""

# Estilos adicionales para el panel de resumen moderno
STYLE_STAT_CHIP = """
    QLabel {
        background-color: white;
        border: 1px solid #e6ecf1;
        border-radius: 12px;
        padding: 4px 8px;
        color: #495057;
        font-size: 12px;
    }
"""

STYLE_FRAME_EXACT_MODE = f"""
    QFrame {{
        background: {COLORS['bg_info_alt']};
        border-radius: 8px;
        border: 1px solid {COLORS['border_info']};
    }}
"""

STYLE_FRAME_SIMILAR_MODE = f"""
    QFrame {{
        background: {COLORS['bg_success']};
        border-radius: 8px;
        border: 1px solid {COLORS['border_success']};
    }}
"""

STYLE_SLIDER_SENSITIVITY = f"""
    QSlider::groove:horizontal {{
        height: 6px;
        background: {COLORS['success_light']};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {COLORS['success']};
        border-radius: 7px;
        width: 14px;
        height: 14px;
        margin: -4px 0;
    }}
"""

STYLE_LABEL_MUTED_SMALL = f"color: {COLORS['text_muted']}; font-size: 12px;"

STYLE_LABEL_SUCCESS_BOLD = f"color: {COLORS['success']}; font-size: 13px; font-weight: 500;"

STYLE_LABEL_INFO_MARGIN = f"margin-left: 24px; color: {COLORS['text_secondary']}; font-size: 13px;"

STYLE_LABEL_INFO_STANDARD = f"color: {COLORS['text_secondary']}; font-size: 13px; line-height: 1.6;"

# ============================================================================
# ESTILOS ESPECÍFICOS DE DIÁLOGOS
# ============================================================================

STYLE_DIALOG_FOLDER_LABEL = f"color: {COLORS['blue_light']}; font-weight: 600; margin: 8px 0;"

STYLE_DIALOG_WARNING_ORANGE = f"color: {COLORS['orange']}; padding: 5px; font-weight: bold;"

STYLE_DIALOG_SMALL_GRAY = f"color: {COLORS['gray']}; font-size: 10px;"

STYLE_DIALOG_TINY_TEXT = "font-size: 10px; padding: 2px;"

STYLE_DIALOG_TINY_BUTTON = "font-size: 9px; padding: 2px;"

STYLE_DIALOG_FRAME_SELECTED = f"QFrame {{ border: 2px solid {COLORS['red_light']}; background-color: {COLORS['red_bg']}; }}"

STYLE_DIALOG_FRAME_UNSELECTED = f"QFrame {{ border: 1px solid {COLORS['gray_light']}; background-color: white; }}"

STYLE_DIALOG_TITLE_BOLD = f"font-weight: bold; font-size: 14px; color: {COLORS['text_darker']};"

STYLE_DIALOG_DESC_MUTED = f"color: {COLORS['text_light']}; font-size: 11px; padding: 5px;"

STYLE_DIALOG_LABEL_DISABLED = f"border: 1px solid {COLORS['gray_medium']}; background-color: {COLORS['bg_gray']};"

STYLE_FRAME_TRANSPARENT = "background: transparent;"

STYLE_LABEL_TITLE_DARK = f"font-weight: bold; color: {COLORS['text_dark']};"

# ---------------------------------------------------------------------------
# Additional styles extracted from dialogs.py
# ---------------------------------------------------------------------------

STYLE_ITALIC_GRAY = "font-style: italic; color: gray;"

STYLE_INFO_HIGHLIGHT = (
    "color: #495057; padding: 10px; background-color: #e7f3ff; "
    "border-radius: 5px; margin-bottom: 10px;"
)

STYLE_DESC_SMALL_INDENT = "color: #6c757d; font-size: 11px; margin-left: 20px;"

# Alias para mantener compatibilidad
STYLE_SMALL_INFO_LABEL_INDENT = STYLE_DESC_SMALL_INDENT  

STYLE_WARNING_LIGHT = "color: #495057; padding: 10px; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 4px;"

STYLE_TABS = """
QTabWidget::pane {
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 10px;
    background-color: white;
}
QTabBar::tab {
    padding: 8px 16px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #007bff;
    color: white;
}
"""

STYLE_FOOTER = "background-color: #f8f9fa; border-top: 1px solid #dee2e6;"

STYLE_RESTORE_BUTTON = """
QPushButton {
    background-color: transparent;
    color: #6c757d;
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #e9ecef;
}
"""

STYLE_SAVE_BUTTON = """
QPushButton {
    background-color: #28a745;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 20px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #218838;
}
"""

STYLE_CANCEL_BUTTON = """
QPushButton {
    background-color: transparent;
    color: #6c757d;
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 8px 20px;
}
QPushButton:hover {
    background-color: #e9ecef;
}
"""

STYLE_SMALL_INFO_LABEL = "color: #6c757d; font-size: 11px;"

STYLE_WARNING_LABEL = "color: #856404; background-color: #fff3cd; padding: 8px; border-radius: 4px;"

STYLE_GROUPS_LABEL = "font-weight: bold; margin-top: 10px;"

STYLE_DANGER_BUTTON = """
QPushButton {
    background-color: #dc3545;
    color: white;
    padding: 8px 20px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #c82333;
}
"""

STYLE_GROUP_LABEL = "font-weight: bold; font-size: 14px;"

STYLE_PANEL_LABEL = "padding: 8px; background-color: #f8f9fa; border-radius: 4px;"

STYLE_MORE_ITALIC = "color: #6c757d; font-style: italic;"

STYLE_SUMMARY_ACTION_BUTTON = """
    QPushButton {
        background-color: #ffffff;
        color: #495057;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 13px;
    }
    QPushButton:hover {
        background-color: #f1f5f9;
        border-color: #cfd8e3;
    }
    QPushButton:pressed {
        background-color: #e9eef4;
    }
"""

STYLE_SUMMARY_ACTION_BUTTON_FULL = """
    QPushButton {
        background-color: #ffffff;
        color: #495057;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        text-align: left;
    }
    QPushButton:hover {
        background-color: #f8fafc;
        border-color: #dfe7ef;
    }
    QPushButton:pressed {
        background-color: #eef4f9;
    }
"""

# ============================================================================
# ESTILOS DE PROGRESS BAR
# ============================================================================

STYLE_PROGRESS_BAR = """
    QProgressBar {
        border: 2px solid #bdc3c7;
        border-radius: 5px;
        text-align: center;
        background-color: #ecf0f1;
    }
    QProgressBar::chunk {
        background-color: #3498db;
        border-radius: 3px;
    }
"""

# ============================================================================
# FUNCIONES HELPER PARA ESTILOS DINÁMICOS
# ============================================================================

def get_button_style(color):
    """
    Genera estilo para botones con color personalizado

    Args:
        color: Color en formato hex (con o sin #) o nombre de color de la paleta

    Returns:
        String con el estilo CSS completo
    """
    # Mapeo de colores base a colores hover y pressed usando la paleta COLORS
    color_variants = {
        COLORS['info']: {
            'base': COLORS['info'],
            'hover': COLORS['info_hover'],
            'pressed': COLORS['info_pressed']
        },
        COLORS['success']: {
            'base': COLORS['success'],
            'hover': COLORS['success_hover'],
            'pressed': COLORS['success_pressed']
        },
        COLORS['blue']: {
            'base': COLORS['blue'],
            'hover': COLORS['blue_hover'],
            'pressed': COLORS['blue_pressed']
        },
        COLORS['warning']: {
            'base': COLORS['warning'],
            'hover': COLORS['warning_hover'],
            'pressed': COLORS['warning_pressed']
        },
        # Mantener retrocompatibilidad con códigos hex directos
        "#17a2b8": {
            'base': COLORS['info'],
            'hover': COLORS['info_hover'],
            'pressed': COLORS['info_pressed']
        },
        "#28a745": {
            'base': COLORS['success'],
            'hover': COLORS['success_hover'],
            'pressed': COLORS['success_pressed']
        },
        "#007bff": {
            'base': COLORS['blue'],
            'hover': COLORS['blue_hover'],
            'pressed': COLORS['blue_pressed']
        },
        "#ffc107": {
            'base': COLORS['warning'],
            'hover': COLORS['warning_hover'],
            'pressed': COLORS['warning_pressed']
        }
    }

    # Obtener variantes o usar por defecto
    if color in color_variants:
        variants = color_variants[color]
    else:
        # Colores por defecto si no está mapeado
        variants = {
            'base': color,
            'hover': f"{color}dd",
            'pressed': f"{color}aa"
        }

    return f"""
        QPushButton {{
            background-color: {variants['base']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: bold;
            min-width: 180px;
            min-height: 40px;
        }}
        QPushButton:hover {{
            background-color: {variants['hover']};
        }}
        QPushButton:pressed {{
            background-color: {variants['pressed']};
        }}
        QPushButton:focus {{
            outline: none;
            border: 2px solid white;
        }}
        QPushButton:disabled {{
            background-color: {COLORS['bg_disabled']};
            color: {COLORS['disabled_bg']};
        }}
    """

# ============================================================================
# ESTILOS DE PESTAÑAS (NUEVO DISEÑO MODERNO)
# ============================================================================

STYLE_TAB_WIDGET = """
QTabWidget::pane {
    border: 2px solid #e9ecef;
    border-radius: 12px;
    background-color: white;
    top: -2px;
}

QTabBar::tab {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f8f9fa, stop:1 #e9ecef);
    border: 2px solid #dee2e6;
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 12px 24px;
    margin-right: 4px;
    margin-top: 4px;
    font-size: 13px;
    font-weight: 500;
    color: #6c757d;
    min-width: 120px;
}

QTabBar::tab:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #ffffff, stop:1 #f8f9fa);
    color: #495057;
    border-color: #adb5bd;
}

QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2196F3, stop:1 #1976D2);
    color: white;
    border-color: #2196F3;
    font-weight: 600;
    padding-bottom: 14px;
}

QTabBar::tab:!selected {
    margin-top: 6px;
}
"""

# ============================================================================
# ESTILOS DE DIALOGS - RENAMING
# ============================================================================

STYLE_DIALOG_INFO_SMALL = f"color: {COLORS['text_muted']}; font-size: 11px; padding: 5px;"

# Unificar con STYLE_SMALL_INFO_LABEL (muy similar)
# STYLE_SMALL_INFO_LABEL = "color: #6c757d; font-size: 11px;" (sin padding)
# Se mantienen separados por el padding

STYLE_DIALOG_COUNTER_BOLD = f"font-weight: bold; color: #2c5aa0; margin-left: 10px;"

STYLE_DIALOG_PAGINATION_FRAME = "QFrame { background-color: #f0f0f0; border-radius: 3px; }"

STYLE_DIALOG_PAGE_LABEL = "font-weight: bold; padding: 0 20px;"

STYLE_DIALOG_PROBLEM_INFO = f"color: {COLORS['orange']}; font-size: 10px;"

STYLE_DIALOG_PROBLEM_TEXT = f"font-size: 10px; color: {COLORS['text_muted']};"

# Unificar con estilos similares de labels tipo info
STYLE_ORG_TYPES_LABEL = STYLE_DIALOG_PROBLEM_TEXT + " padding: 5px;"

STYLE_DIALOG_OPTIONS_GROUP = "QGroupBox { font-weight: bold; }"

STYLE_DIALOG_METRIC_FRAME = lambda color: f"""
    QFrame {{
        background-color: {COLORS['bg_light']};
        border-left: 3px solid {color};
        padding: 5px;
        margin: 2px;
    }}
"""

STYLE_DIALOG_VALUE_LABEL = lambda color: f"color: {color}; background: transparent; border: none;"

STYLE_DIALOG_DESC_SMALL = f"font-size: 10px; color: {COLORS['text_muted']}; background: transparent; border: none;"

# Background colors for table items (renaming conflicts)
COLOR_WARNING_BG = COLORS['warning_light']  # RGB: 255, 243, 205
COLOR_CONFLICT_BG = COLORS['warning']  # RGB: 255, 193, 7
COLOR_SUCCESS_BG = COLORS['success']  # RGB: 76, 175, 80

# ============================================================================
# ESTILOS DE DIALOGS - HEIC
# ============================================================================

# Frame de header info unificado para dialogs
STYLE_DIALOG_HEADER_INFO_FRAME = f"""
    QFrame {{
        background: {COLORS['bg_info']};
        border: 1px solid {COLORS['border_info']};
        border-radius: 8px;
        padding: 12px;
    }}
"""

# Alias para mantener compatibilidad
STYLE_HEIC_HEADER_FRAME = STYLE_DIALOG_HEADER_INFO_FRAME

# STYLE_HEIC_EXPLANATION ya definido como alias de STYLE_DIALOG_EXPLANATION_TEXT arriba
# STYLE_HEIC_SAVINGS ya definido como alias de STYLE_DIALOG_SAVINGS_GREEN arriba

STYLE_HEIC_FORMAT_INFO = f"color: {COLORS['text_muted']}; font-size: 10px; margin-left: 20px;"

# TreeWidget estándar para dialogs (base unificada)
STYLE_DIALOG_TREE_STANDARD = f"""
    QTreeWidget {{
        border: 1px solid {COLORS['border_light']};
        border-radius: 4px;
        background-color: white;
        alternate-background-color: {COLORS['bg_light']};
    }}
    QTreeWidget::item {{
        padding: 4px;
        min-height: 22px;
    }}
    QTreeWidget::item:hover {{
        background-color: {COLORS['bg_medium']};
    }}
    QTreeWidget::item:selected {{
        background-color: {COLORS['primary_light']};
        color: white;
    }}
"""

# Alias para HEIC tree
STYLE_HEIC_TREE = STYLE_DIALOG_TREE_STANDARD

# HEIC tree colors
COLOR_HEIC_PURPLE = "#9c27b0"
COLOR_HEIC_ORANGE = "#ff9800"

# ============================================================================
# ESTILOS DE DIALOGS - ORGANIZATION
# ============================================================================

# Frame de header (usa el estilo unificado)
STYLE_ORG_HEADER_FRAME = STYLE_DIALOG_HEADER_INFO_FRAME

# STYLE_ORG_TYPES_LABEL ya definido como alias arriba

STYLE_ORG_CONFLICTS_LABEL = f"font-weight: bold; color: #e74c3c; font-size: 11px; padding: 5px;"

STYLE_ORG_LEGEND_FRAME = f"""
    QFrame {{
        background: white;
        border: 1px solid {COLORS['border_light']};
        border-radius: 4px;
        padding: 6px;
    }}
"""

STYLE_ORG_LEGEND_LABEL = f"font-size: 10px; color: #1976d2; background: transparent;"

# Tree organization (con altura de item ligeramente diferente)
STYLE_ORG_TREE = f"""
    QTreeWidget {{
        border: 1px solid {COLORS['border_light']};
        border-radius: 4px;
        background-color: white;
        alternate-background-color: {COLORS['bg_light']};
    }}
    QTreeWidget::item {{
        padding: 4px;
        min-height: 24px;
    }}
    QTreeWidget::item:hover {{
        background-color: {COLORS['bg_medium']};
    }}
    QTreeWidget::item:selected {{
        background-color: {COLORS['primary_light']};
        color: white;
    }}
"""

# Organization tree colors
COLOR_ORG_ERROR = "#e74c3c"
COLOR_ORG_FOLDER = "#2c5aa0"
COLOR_ORG_SUBFOLDER = "#666"
COLOR_ORG_SUCCESS = "#27ae60"
COLOR_ORG_WHATSAPP = "#25d366"

# ============================================================================
# ESTILOS DE TABS - DUPLICATES
# ============================================================================

STYLE_DUPLICATES_TITLE = f"font-size: 18px; font-weight: 600; color: {COLORS['text_primary']};"

STYLE_DUPLICATES_DESC = f"font-size: 12px; color: {COLORS['text_muted']}; margin-bottom: 4px;"

STYLE_DUPLICATES_EXACT_CARD = f"""
    QGroupBox {{
        font-weight: 700;
        font-size: 13px;
        color: #ffffff;
        border: 2px solid #2c5aa0;
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 18px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                   stop:0 #e3f2fd, stop:1 #ffffff);
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 15px;
        padding: 3px 12px;
        background-color: #2c5aa0;
        border-radius: 4px;
        color: white;
        font-size: 13px;
    }}
"""

STYLE_DUPLICATES_HELP_LABEL = """
    font-size: 11px; 
    color: #495057; 
    background-color: #e7f3ff;
    padding: 4px 8px;
    border-radius: 3px;
    border-left: 3px solid #2c5aa0;
"""

STYLE_DUPLICATES_STATUS_LABEL = """
    font-size: 12px; 
    font-weight: 600; 
    color: #2c5aa0;
    padding: 4px;
"""

STYLE_DUPLICATES_REVIEW_BUTTON = """
    QPushButton {
        background-color: #28a745;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: 600;
    }
    QPushButton:hover {
        background-color: #218838;
    }
    QPushButton:pressed {
        background-color: #1e7e34;
    }
"""

STYLE_DUPLICATES_DETAILS_TEXT = f"""
    QTextEdit {{
        background-color: {COLORS['bg_light']};
        border: 1px solid {COLORS['border_light']};
        border-radius: 4px;
        padding: 8px;
        font-size: 11px;
        color: {COLORS['text_secondary']};
    }}
"""

STYLE_DUPLICATES_SIMILAR_CARD = f"""
    QGroupBox {{
        font-weight: 700;
        font-size: 13px;
        color: #ffffff;
        border: 2px solid {COLORS['success']};
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 18px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                   stop:0 {COLORS['success_light']}, stop:1 #ffffff);
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 15px;
        padding: 3px 12px;
        background-color: {COLORS['success']};
        border-radius: 4px;
        color: white;
        font-size: 13px;
    }}
"""

STYLE_DUPLICATES_SIMILAR_HELP = f"""
    font-size: 11px; 
    color: {COLORS['text_secondary']}; 
    background-color: {COLORS['success_light']};
    padding: 4px 8px;
    border-radius: 3px;
    border-left: 3px solid {COLORS['success']};
"""

STYLE_DUPLICATES_SENS_LABEL = f"font-size: 12px; color: {COLORS['text_secondary']}; font-weight: 600;"

STYLE_DUPLICATES_SENS_VALUE = f"font-size: 11px; color: {COLORS['text_muted']};"

STYLE_DUPLICATES_ANALYZE_BUTTON = f"""
    QPushButton {{
        background-color: {COLORS['success']};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {COLORS['success_hover']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['success_pressed']};
    }}
"""

STYLE_DUPLICATES_CANCEL_BUTTON = f"""
    QPushButton {{
        background-color: {COLORS['danger']};
        color: white;
        border: none;
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {COLORS['danger_hover']};
    }}
"""

# ============================================================================
# ESTILOS GENERALES DE TABS
# ============================================================================

STYLE_TAB_TITLE_LARGE = f"font-size: 20px; font-weight: 600; color: {COLORS['text_primary']}; margin-bottom: 4px;"

STYLE_TAB_DESC = f"font-size: 13px; color: {COLORS['text_muted']}; margin-bottom: 8px;"

# ============================================================================
# ESTILOS ADICIONALES PARA DIALOGS
# ============================================================================

STYLE_DIALOG_EXPLANATION_TEXT = f"font-size: 9pt; color: {COLORS['text_secondary']}; background: transparent;"

# Alias unificado para explicaciones (HEIC y otros)
STYLE_HEIC_EXPLANATION = STYLE_DIALOG_EXPLANATION_TEXT

STYLE_DIALOG_NO_PREVIEW = f"color: {COLORS['text_muted']}; font-size: 10px; font-style: italic;"

STYLE_DIALOG_NAME_LABEL = f"font-size: 11px; color: {COLORS['text_primary']}; background: transparent;"

STYLE_DIALOG_DETAILS_LABEL = f"font-size: 9px; color: {COLORS['text_muted']}; background: transparent;"

# Unificar descripciones pequeñas/tiny
STYLE_DIALOG_DESC_TINY = f"font-size: 9px; color: {COLORS['text_muted']}; background: transparent; border: none;"
STYLE_DIALOG_DESC_SMALL = f"font-size: 10px; color: {COLORS['text_muted']}; background: transparent; border: none;"

STYLE_DIALOG_SEPARATOR = f"color: {COLORS['border_light']};"

STYLE_DIALOG_SAVINGS_GREEN = f"font-weight: bold; color: #27ae60; font-size: 11px; padding: 3px;"

# Alias para mantener compatibilidad
STYLE_HEIC_SAVINGS = STYLE_DIALOG_SAVINGS_GREEN

# ============================================================================
# ESTILOS PARA ABOUT DIALOG
# ============================================================================

STYLE_ABOUT_CONTENT_BG = f"background-color: {COLORS['bg_white']};"

STYLE_ABOUT_DESCRIPTION = f"font-size: 13px; color: #555;"

STYLE_ABOUT_LINE = f"color: #e0e0e0;"

STYLE_ABOUT_TOOLS_TITLE = f"font-size: 13px; color: #333;"

STYLE_ABOUT_TOOL_WIDGET = f"font-size: 12px; color: #555;"

STYLE_ABOUT_TECH_INFO = f"font-size: 11px; color: #777;"

STYLE_ABOUT_CREDITS = f"font-size: 11px; color: #999; font-style: italic;"

STYLE_ABOUT_FOOTER = f"background-color: #f8f8f8;"

# ============================================================================
# ESTILOS PARA SETTINGS DIALOG
# ============================================================================

STYLE_SETTINGS_DEBUG_INFO = f"color: #ff5252; font-size: 11px;"

# ============================================================================
# ESTILO GLOBAL PARA TOOLTIPS
# ============================================================================

STYLE_GLOBAL_TOOLTIP = """
QToolTip {
    background-color: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e0 !important;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}
"""

# Estilo oscuro compartido para tooltips (usado en diálogos como HEIC)
STYLE_TOOLTIP_DARK = """
QToolTip {
    background-color: #2c3e50;
    color: #ecf0f1;
    border: 1px solid #34495e;
    padding: 8px;
    font-size: 11px;
    border-radius: 4px;
}
"""

# ============================================================================
# ESTILOS PARA ICONOS MATERIAL DESIGN
# ============================================================================

# Colores recomendados para iconos según contexto
ICON_COLORS = {
    # Colores primarios
    'primary': '#2563eb',        # Azul principal para acciones importantes
    'secondary': '#64748b',      # Gris para iconos secundarios
    'muted': '#94a3b8',          # Gris claro para iconos deshabilitados
    
    # Estados
    'success': '#155724',        # Verde para éxito/completado
    'warning': '#856404',        # Amarillo oscuro para advertencias
    'danger': '#dc2626',         # Rojo para peligro/error
    'info': '#1e40af',           # Azul para información
    
    # Contextos específicos
    'text': '#334155',           # Gris oscuro para iconos en texto
    'hover': '#475569',          # Gris medio para hover
    'disabled': '#cbd5e0',       # Gris muy claro para deshabilitado
}

# Tamaños estándar de iconos
ICON_SIZES = {
    'small': 14,       # Iconos pequeños en labels compactos
    'normal': 16,      # Tamaño estándar para la mayoría de iconos
    'medium': 20,      # Iconos en botones principales
    'large': 24,       # Iconos grandes en headers
    'xlarge': 32,      # Iconos muy grandes (poco común)
}

# Documentación de uso de iconos
"""
Uso de iconos en la aplicación:
-------------------------------

1. Importar el gestor de iconos:
   from utils.icons import icon_manager

2. Aplicar icono a un botón:
   icon_manager.set_button_icon(button, 'settings', color=ICON_COLORS['primary'], size=ICON_SIZES['medium'])

3. Aplicar icono a un label:
   icon_manager.set_label_icon(label, 'folder', color=ICON_COLORS['text'], size=ICON_SIZES['normal'])

4. Crear label con icono:
   label = icon_manager.create_icon_label('info', color=ICON_COLORS['info'], size=ICON_SIZES['normal'])

Recomendaciones:
- Usar colores del diccionario ICON_COLORS para consistencia
- Usar tamaños del diccionario ICON_SIZES
- Evitar mezclar emojis y Material Design icons
- Los iconos NO afectan la fuente del texto de la aplicación
"""
