"""
UI Styles para PhotoKit Manager
Contiene todas las definiciones de estilos CSS para la interfaz
"""

# ============================================================================
# ESTILOS DE BOTONES PRINCIPALES
# ============================================================================

STYLE_CONFIG_BUTTON = """
    QPushButton {
        background-color: transparent;
        color: #6c757d;
        border: 1px solid #dee2e6;
        border-radius: 20px;
        padding: 5px;
        font-size: 18px;
    }
    QPushButton:hover {
        background-color: #f8f9fa;
        border-color: #adb5bd;
        color: #495057;
    }
    QPushButton:pressed {
        background-color: #e9ecef;
    }
"""

STYLE_BROWSE_BUTTON = """
    QPushButton {
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #0056b3;
    }
    QPushButton:pressed {
        background-color: #004085;
    }
"""

STYLE_ANALYZE_BUTTON = """
    QPushButton {
        background-color: #2196F3;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 20px 40px;
        font-size: 18px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    QPushButton:hover {
        background-color: #1976D2;
        padding: 20px 40px;
    }
    QPushButton:pressed {
        background-color: #0D47A1;
        padding: 20px 40px;
    }
    QPushButton:focus {
        outline: none;
        border: 3px solid #64B5F6;
        padding: 17px 37px;
    }
    QPushButton:disabled {
        background-color: #BDBDBD;
        color: #EEEEEE;
        padding: 20px 40px;
    }
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

STYLE_DIR_LABEL = "font-weight: bold; font-size: 13px; color: #495057;"

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

STYLE_STATS_DIRECTORY = """
font-weight: bold;
color: #007bff;
text-decoration: underline;
"""

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

STYLE_DIRECTORY_EDIT_ALT = """
    QLineEdit {
        padding: 6px;
        border: 1px solid #ced4da;
        border-radius: 4px;
        background-color: #e9ecef;
    }
"""

STYLE_LOGS_EDIT = """
    QLineEdit {
        padding: 5px 8px;
        border: 1px solid #ced4da;
        border-radius: 4px;
        background-color: #e9ecef;
        font-size: 12px;
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

# ============================================================================
# ESTILOS DE PANELS Y FRAMES
# ============================================================================

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
        color: Color en formato hex (con o sin #)

    Returns:
        String con el estilo CSS completo
    """
    # Mapeo de colores base a colores hover y pressed
    color_variants = {
        "#17a2b8": {  # Cyan/Info - Para Preview
            'base': "#17a2b8",
            'hover': "#138496",
            'pressed': "#0f6674"
        },
        "#28a745": {  # Verde - Para Ejecutar
            'base': "#28a745",
            'hover': "#218838",
            'pressed': "#1e7e34"
        },
        "#007bff": {  # Azul - Alternativo
            'base': "#007bff",
            'hover': "#0056b3",
            'pressed': "#004085"
        },
        "#ffc107": {  # Amarillo/Warning - Alternativo
            'base': "#ffc107",
            'hover': "#e0a800",
            'pressed': "#d39e00"
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
            background-color: #BDBDBD;
            color: #757575;
        }}
    """
