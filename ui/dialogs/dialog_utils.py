"""
Utilidades compartidas para diálogos
Funciones comunes para abrir archivos, carpetas y mostrar detalles
"""
import os
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt
from utils.format_utils import format_size
from utils.date_utils import get_file_date
from utils.platform_utils import open_file_with_default_app, open_folder_in_explorer


def open_file(file_path: Path, parent_widget=None):
    """
    Abre un archivo con la aplicación predeterminada del sistema operativo.
    Wrapper de UI para utils.platform_utils.open_file_with_default_app()
    
    Args:
        file_path: Ruta del archivo a abrir
        parent_widget: Widget padre para mostrar mensajes de error
        
    Returns:
        True si el archivo se abrió correctamente, False si hubo error
    """
    def show_error(error_msg: str):
        """Callback para mostrar errores en QMessageBox"""
        if parent_widget:
            QMessageBox.warning(
                parent_widget,
                "Error al abrir archivo",
                error_msg
            )
    
    return open_file_with_default_app(file_path, error_callback=show_error)


def open_folder(folder_path: Path, parent_widget=None, select_file: Path = None):
    """
    Abre una carpeta en el explorador de archivos del sistema operativo.
    Wrapper de UI para utils.platform_utils.open_folder_in_explorer()
    
    Args:
        folder_path: Ruta de la carpeta a abrir
        parent_widget: Widget padre para mostrar mensajes de error
        select_file: Archivo opcional dentro de la carpeta a seleccionar
        
    Returns:
        True si la carpeta se abrió correctamente, False si hubo error
    """
    def show_error(error_msg: str):
        """Callback para mostrar errores en QMessageBox"""
        if parent_widget:
            QMessageBox.warning(
                parent_widget,
                "Error al abrir carpeta",
                error_msg
            )
    
    return open_folder_in_explorer(folder_path, 
                                   select_file=select_file,
                                   error_callback=show_error)


def show_file_details_dialog(file_path: Path, parent_widget=None, additional_info=None):
    """
    Muestra un diálogo con detalles completos del archivo
    
    Args:
        file_path: Ruta del archivo
        parent_widget: Widget padre para el diálogo
        additional_info: Dict con información adicional a mostrar (opcional)
            Puede incluir: original_name, new_name, file_type, etc.
    """
    # Obtener información del archivo
    try:
        file_stat = os.stat(file_path)
        created_time = datetime.fromtimestamp(file_stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        modified_time = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        file_size = file_stat.st_size
        
        # Intentar obtener fecha del archivo usando la utilidad del proyecto
        file_date = get_file_date(file_path)
        if file_date:
            date_from_name = file_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_from_name = "No disponible"
    except Exception as e:
        created_time = f"Error: {str(e)}"
        modified_time = f"Error: {str(e)}"
        file_size = 0
        date_from_name = "Error"
    
    # Construir HTML con detalles - diseño mejorado
    details = """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        h3 { color: #2c5aa0; margin-top: 0; margin-bottom: 16px; border-bottom: 2px solid #2c5aa0; padding-bottom: 8px; }
        h4 { color: #495057; margin-top: 20px; margin-bottom: 10px; font-size: 11pt; }
        .info-row { margin: 6px 0; }
        .label { color: #6c757d; font-weight: 600; display: inline-block; min-width: 160px; }
        .value { color: #212529; }
        .code { background: #f4f4f4; padding: 4px 8px; border-radius: 3px; font-family: monospace; font-size: 9pt; color: #495057; display: inline-block; margin: 2px 0; }
        .status-ok { color: #28a745; font-weight: bold; }
        .status-conflict { color: #e74c3c; font-weight: bold; }
        .section { margin: 12px 0; padding: 12px; background: #f8f9fa; border-radius: 4px; }
    </style>
    """
    
    details += "<h3>Detalles del Archivo</h3>"
    
    # Información básica
    details += "<div class='section'>"
    details += f"<div class='info-row'><span class='label'>Nombre:</span> <span class='value'>{file_path.name}</span></div>"
    details += f"<div class='info-row'><span class='label'>Tamaño:</span> <span class='value'>{format_size(file_size)}</span></div>"
    
    # Información adicional si se proporcionó
    if additional_info:
        if 'original_name' in additional_info and 'new_name' in additional_info:
            details += f"<div class='info-row'><span class='label'>Nombre original:</span> <span class='value'>{additional_info['original_name']}</span></div>"
            details += f"<div class='info-row'><span class='label'>Nombre nuevo:</span> <span class='value'>{additional_info['new_name']}</span></div>"
        
        if 'file_type' in additional_info:
            details += f"<div class='info-row'><span class='label'>Tipo:</span> <span class='value'>{additional_info['file_type']}</span></div>"
        
        if 'conflict' in additional_info:
            status_class = "status-conflict" if additional_info['conflict'] else "status-ok"
            status_text = "Conflicto de nombre" if additional_info['conflict'] else "Sin conflictos"
            details += f"<div class='info-row'><span class='label'>Estado:</span> <span class='{status_class}'>{status_text}</span></div>"
        
        if 'sequence' in additional_info and additional_info['sequence']:
            details += f"<div class='info-row'><span class='label'>Secuencia:</span> <span class='value'>{additional_info['sequence']}</span></div>"
    
    details += "</div>"
    
    # Ubicación
    details += "<h4>Ubicación</h4>"
    details += "<div class='section'>"
    details += f"<div class='info-row'><span class='label'>Ruta actual:</span><br><span class='code'>{file_path.parent}</span></div>"
    
    if additional_info and 'target_path' in additional_info:
        details += f"<div class='info-row' style='margin-top: 10px;'><span class='label'>Ruta destino:</span><br><span class='code'>{additional_info['target_path']}</span></div>"
    
    details += "</div>"
    
    # Fechas
    details += "<h4>Información de Fechas</h4>"
    details += "<div class='section'>"
    details += f"<div class='info-row'><span class='label'>Fecha detectada:</span> <span class='value'>{date_from_name}</span></div>"
    details += f"<div class='info-row'><span class='label'>Fecha de creación:</span> <span class='value'>{created_time}</span></div>"
    details += f"<div class='info-row'><span class='label'>Fecha de modificación:</span> <span class='value'>{modified_time}</span></div>"
    details += "</div>"
    
    # Información adicional de metadatos si se proporcionó
    if additional_info and 'metadata' in additional_info:
        details += "<h4>Metadatos Adicionales</h4>"
        details += "<div class='section'>"
        for key, value in additional_info['metadata'].items():
            details += f"<div class='info-row'><span class='label'>{key}:</span> <span class='value'>{value}</span></div>"
        details += "</div>"
    
    # Crear diálogo personalizado sin icono ni scroll
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QFrame
    
    dialog = QDialog(parent_widget)
    dialog.setWindowTitle("Detalles del Archivo")
    dialog.setModal(True)
    dialog.setMinimumWidth(850)
    dialog.setMaximumWidth(900)
    
    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(20, 15, 20, 15)
    main_layout.setSpacing(12)
    
    # Título principal
    title_label = QLabel("Detalles del Archivo")
    title_label.setStyleSheet("""
        font-size: 14pt;
        font-weight: bold;
        color: #2c5aa0;
        border-bottom: 2px solid #2c5aa0;
        padding-bottom: 6px;
        margin-bottom: 8px;
    """)
    main_layout.addWidget(title_label)
    
    # Contenedor principal con 2 columnas
    content_layout = QHBoxLayout()
    content_layout.setSpacing(20)
    
    # === COLUMNA IZQUIERDA ===
    left_column = QVBoxLayout()
    left_column.setSpacing(12)
    
    # Información básica
    basic_info = _create_info_section("Información General", [
        ("Nombre", file_path.name),
        ("Tamaño", format_size(file_size)),
    ])
    
    if additional_info:
        if 'original_name' in additional_info and 'new_name' in additional_info:
            basic_info.layout().addWidget(_create_info_row("Original", additional_info['original_name']))
            basic_info.layout().addWidget(_create_info_row("Nuevo", additional_info['new_name']))
        
        if 'file_type' in additional_info:
            basic_info.layout().addWidget(_create_info_row("Tipo", additional_info['file_type']))
        
        if 'conflict' in additional_info:
            status_color = "#e74c3c" if additional_info['conflict'] else "#28a745"
            status_text = "Conflicto" if additional_info['conflict'] else "Sin conflictos"
            status_label = _create_info_row("Estado", status_text, status_color)
            basic_info.layout().addWidget(status_label)
        
        if 'sequence' in additional_info and additional_info['sequence']:
            basic_info.layout().addWidget(_create_info_row("Secuencia", str(additional_info['sequence'])))
    
    left_column.addWidget(basic_info)
    
    # Ubicación
    location_items = [("Ruta actual", str(file_path.parent))]
    if additional_info and 'target_path' in additional_info:
        location_items.append(("Ruta destino", str(additional_info['target_path'])))
    
    location_info = _create_info_section("Ubicación", location_items, use_code=True)
    left_column.addWidget(location_info)
    
    left_column.addStretch()
    content_layout.addLayout(left_column, 1)
    
    # === COLUMNA DERECHA ===
    right_column = QVBoxLayout()
    right_column.setSpacing(12)
    
    # Fechas
    dates_info = _create_info_section("Fechas", [
        ("Detectada", date_from_name),
        ("Creación", created_time),
        ("Modificación", modified_time),
    ])
    right_column.addWidget(dates_info)
    
    # Metadatos adicionales
    if additional_info and 'metadata' in additional_info:
        metadata_items = [(key, str(value)) for key, value in additional_info['metadata'].items()]
        metadata_info = _create_info_section("Metadatos", metadata_items)
        right_column.addWidget(metadata_info)
    
    right_column.addStretch()
    content_layout.addLayout(right_column, 1)
    
    main_layout.addLayout(content_layout)
    
    # Separador
    separator = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setFrameShadow(QFrame.Shadow.Sunken)
    from ui.styles.design_system import DesignSystem
    separator.setStyleSheet(DesignSystem.STYLE_DIALOG_SEPARATOR)
    main_layout.addWidget(separator)
    
    # Botón OK centrado con estilo Material Design
    ok_button = QPushButton("Cerrar")
    ok_button.setMinimumWidth(120)
    ok_button.setMinimumHeight(32)
    ok_button.clicked.connect(dialog.accept)
    ok_button.setStyleSheet(DesignSystem.get_primary_button_style())
    
    button_layout = QHBoxLayout()
    button_layout.addStretch()
    button_layout.addWidget(ok_button)
    button_layout.addStretch()
    main_layout.addLayout(button_layout)
    
    dialog.exec()


def _create_info_section(title, items, use_code=False):
    """Crea una sección de información con título y items"""
    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
    
    group = QGroupBox(title)
    group.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            font-size: 10pt;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
            background-color: #f8f9fa;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #495057;
        }
    """)
    
    layout = QVBoxLayout()
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(6)
    
    for label, value in items:
        row = _create_info_row(label, value, use_code=use_code)
        layout.addWidget(row)
    
    group.setLayout(layout)
    return group


def _create_info_row(label_text, value_text, value_color=None, use_code=False):
    """Crea una fila de información con label y valor"""
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
    
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    
    # Label
    label = QLabel(f"{label_text}:")
    label.setStyleSheet("""
        color: #6c757d;
        font-weight: 600;
        font-size: 9pt;
    """)
    label.setMinimumWidth(80)
    label.setMaximumWidth(80)
    layout.addWidget(label)
    
    # Valor
    value = QLabel(value_text)
    
    if use_code:
        value.setStyleSheet("""
            background: #ffffff;
            padding: 4px 6px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 8pt;
            color: #495057;
            border: 1px solid #dee2e6;
        """)
        value.setWordWrap(True)
    else:
        style = f"""
            color: {value_color if value_color else '#212529'};
            font-size: 9pt;
        """
        if value_color:
            style += "font-weight: bold;"
        value.setStyleSheet(style)
        value.setWordWrap(True)
    
    layout.addWidget(value, 1)
    
    return widget
