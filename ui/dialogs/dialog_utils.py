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
from utils.date_utils import get_date_from_file, select_chosen_date, get_all_file_dates
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
    Muestra un diálogo con detalles completos del archivo usando Material Design
    
    Args:
        file_path: Ruta del archivo
        parent_widget: Widget padre para el diálogo
        additional_info: Dict con información adicional a mostrar (opcional)
            Puede incluir: original_name, new_name, file_type, etc.
    """
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QFrame, QGroupBox, QWidget, QScrollArea)
    from PyQt6.QtCore import Qt
    from ui.styles.design_system import DesignSystem
    from ui.styles.icons import icon_manager
    
    # Obtener toda la información de fechas disponible
    dates_info = get_all_file_dates(file_path)
    
    # Seleccionar la fecha más representativa
    selected_date, selected_source = select_chosen_date(dates_info)
    dates_info['selected_date'] = selected_date
    dates_info['selected_source'] = selected_source
    
    # Mapear la fecha EXIF principal para compatibilidad con la UI
    dates_info['exif_date'] = (dates_info.get('exif_date_time_original') or 
                              dates_info.get('exif_create_date') or 
                              dates_info.get('exif_date_digitized'))
    
    # Obtener información básica del archivo
    try:
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
    except Exception as e:
        file_size = 0
    
    # Crear diálogo
    dialog = QDialog(parent_widget)
    dialog.setWindowTitle("Detalles del Archivo")
    dialog.setModal(True)
    dialog.setMinimumWidth(900)
    dialog.setMaximumWidth(950)
    dialog.setMinimumHeight(600)
    
    # Layout principal
    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(
        DesignSystem.SPACE_24, DesignSystem.SPACE_20, 
        DesignSystem.SPACE_24, DesignSystem.SPACE_20
    )
    main_layout.setSpacing(DesignSystem.SPACE_16)
    
    # Header con título e icono
    header_layout = QHBoxLayout()
    header_layout.setSpacing(DesignSystem.SPACE_12)
    
    # Icono del archivo
    file_icon = icon_manager.get_icon('file', size=DesignSystem.ICON_SIZE_LG, 
                                     color=DesignSystem.COLOR_PRIMARY)
    header_icon = QLabel()
    header_icon.setPixmap(file_icon.pixmap(DesignSystem.ICON_SIZE_LG, DesignSystem.ICON_SIZE_LG))
    header_layout.addWidget(header_icon)
    
    # Título
    title_label = QLabel("Detalles del Archivo")
    title_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_2XL}px;
        font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        color: {DesignSystem.COLOR_TEXT};
    """)
    header_layout.addWidget(title_label)
    header_layout.addStretch()
    
    main_layout.addLayout(header_layout)
    
    # Área de scroll para el contenido
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll_area.setStyleSheet(f"""
        QScrollArea {{
            border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
            border-radius: {DesignSystem.RADIUS_LG}px;
            background-color: {DesignSystem.COLOR_SURFACE};
        }}
        QScrollArea QWidget {{
            background-color: transparent;
        }}
    """)
    
    # Widget contenedor del scroll
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)
    scroll_layout.setContentsMargins(
        DesignSystem.SPACE_20, DesignSystem.SPACE_16, 
        DesignSystem.SPACE_20, DesignSystem.SPACE_16
    )
    scroll_layout.setSpacing(DesignSystem.SPACE_20)
    
    # === SECCIÓN 1: INFORMACIÓN GENERAL ===
    general_section = _create_material_section("Información General", [
        ("Nombre del archivo", file_path.name, 'file'),
        ("Tamaño", format_size(file_size), 'ruler'),
        ("Tipo", _get_file_type_display(file_path), 'image'),
    ])
    scroll_layout.addWidget(general_section)
    
    # Información adicional si se proporcionó
    if additional_info:
        additional_items = []
        
        if 'original_name' in additional_info and 'new_name' in additional_info:
            additional_items.extend([
                ("Nombre original", additional_info['original_name'], 'file'),
                ("Nombre nuevo", additional_info['new_name'], 'file'),
            ])
        
        if 'file_type' in additional_info:
            additional_items.append(("Tipo de archivo", additional_info['file_type'], 'image'))
        
        if 'conflict' in additional_info:
            status_text = "Conflicto de nombre" if additional_info['conflict'] else "Sin conflictos"
            status_icon = 'alert-circle' if additional_info['conflict'] else 'check-circle'
            status_color = DesignSystem.COLOR_DANGER if additional_info['conflict'] else DesignSystem.COLOR_SUCCESS
            additional_items.append(("Estado", status_text, status_icon))
        
        if 'sequence' in additional_info and additional_info['sequence']:
            additional_items.append(("Secuencia", str(additional_info['sequence']), 'update'))
        
        if additional_items:
            additional_section = _create_material_section("Información Adicional", additional_items)
            scroll_layout.addWidget(additional_section)
    
    # === SECCIÓN 2: UBICACIÓN ===
    location_items = [
        ("Ruta actual", str(file_path.parent), 'folder'),
    ]
    
    if additional_info and 'target_path' in additional_info:
        location_items.append(("Ruta destino", str(additional_info['target_path']), 'folder-open'))
    
    location_section = _create_material_section("Ubicación", location_items, use_code_style=True)
    scroll_layout.addWidget(location_section)
    
    # === SECCIÓN 3: FECHAS DETALLADAS ===
    dates_section = _create_dates_section(dates_info)
    scroll_layout.addWidget(dates_section)
    
    # === SECCIÓN 4: METADATOS ADICIONALES ===
    if additional_info and 'metadata' in additional_info and additional_info['metadata']:
        metadata_items = [(key, str(value), 'information') for key, value in additional_info['metadata'].items()]
        metadata_section = _create_material_section("Metadatos", metadata_items)
        scroll_layout.addWidget(metadata_section)
    
    scroll_layout.addStretch()
    scroll_area.setWidget(scroll_widget)
    main_layout.addWidget(scroll_area)
    
    # Separador
    separator = QFrame()
    separator.setFrameShape(QFrame.Shape.HLine)
    separator.setFrameShadow(QFrame.Shadow.Sunken)
    separator.setStyleSheet(f"color: {DesignSystem.COLOR_CARD_BORDER};")
    main_layout.addWidget(separator)
    
    # Botones
    buttons_layout = QHBoxLayout()
    buttons_layout.setSpacing(DesignSystem.SPACE_12)
    
    # Botón de abrir archivo
    open_file_btn = QPushButton("Abrir Archivo")
    open_file_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
    open_file_btn.clicked.connect(lambda: _open_file_and_close(file_path, dialog))
    buttons_layout.addWidget(open_file_btn)
    
    # Botón de abrir carpeta
    open_folder_btn = QPushButton("Abrir Carpeta")
    open_folder_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
    open_folder_btn.clicked.connect(lambda: _open_folder_and_close(file_path, dialog))
    buttons_layout.addWidget(open_folder_btn)
    
    buttons_layout.addStretch()
    
    # Botón cerrar
    close_btn = QPushButton("Cerrar")
    close_btn.setStyleSheet(DesignSystem.get_primary_button_style())
    close_btn.clicked.connect(dialog.accept)
    buttons_layout.addWidget(close_btn)
    
    main_layout.addLayout(buttons_layout)
    
    dialog.exec()


def _create_material_section(title: str, items: list, use_code_style: bool = False):
    """Crea una sección Material Design con título e items"""
    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
    from ui.styles.design_system import DesignSystem
    from ui.styles.icons import icon_manager
    
    group = QGroupBox(title)
    group.setStyleSheet(f"""
        QGroupBox {{
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
            border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
            border-radius: {DesignSystem.RADIUS_LG}px;
            padding: {DesignSystem.SPACE_16}px;
            margin: 0;
            background-color: {DesignSystem.COLOR_SURFACE};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: {DesignSystem.SPACE_12}px;
            padding: 0 {DesignSystem.SPACE_8}px;
            color: {DesignSystem.COLOR_PRIMARY};
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        }}
    """)
    
    layout = QVBoxLayout()
    layout.setContentsMargins(
        DesignSystem.SPACE_16, DesignSystem.SPACE_24, 
        DesignSystem.SPACE_16, DesignSystem.SPACE_16
    )
    layout.setSpacing(DesignSystem.SPACE_12)
    
    for label_text, value_text, icon_name in items:
        row = _create_material_info_row(label_text, value_text, icon_name, use_code_style)
        layout.addWidget(row)
    
    group.setLayout(layout)
    return group


def _create_material_info_row(label_text: str, value_text: str, icon_name: str, use_code_style: bool = False):
    """Crea una fila de información con icono usando Material Design"""
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
    from ui.styles.design_system import DesignSystem
    from ui.styles.icons import icon_manager
    
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(DesignSystem.SPACE_12)
    
    # Icono
    icon = icon_manager.get_icon(icon_name, size=DesignSystem.ICON_SIZE_MD, 
                                color=DesignSystem.COLOR_TEXT_SECONDARY)
    icon_label = QLabel()
    icon_label.setPixmap(icon.pixmap(DesignSystem.ICON_SIZE_MD, DesignSystem.ICON_SIZE_MD))
    icon_label.setFixedSize(DesignSystem.ICON_SIZE_MD + 4, DesignSystem.ICON_SIZE_MD + 4)
    layout.addWidget(icon_label)
    
    # Label
    label = QLabel(f"{label_text}:")
    label.setStyleSheet(f"""
        color: {DesignSystem.COLOR_TEXT_SECONDARY};
        font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        font-size: {DesignSystem.FONT_SIZE_BASE}px;
    """)
    label.setMinimumWidth(140)
    layout.addWidget(label)
    
    # Valor
    value = QLabel(value_text)
    if use_code_style:
        value.setStyleSheet(f"""
            background-color: {DesignSystem.COLOR_BG_2};
            color: {DesignSystem.COLOR_TEXT};
            font-family: {DesignSystem.FONT_FAMILY_MONO};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_10}px;
            border-radius: {DesignSystem.RADIUS_BASE}px;
            border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
        """)
        value.setWordWrap(True)
    else:
        value.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
        """)
        value.setWordWrap(True)
    
    layout.addWidget(value, 1)
    
    return widget


def _create_dates_section(dates_info: dict):
    """Crea la sección especial de fechas con información detallada"""
    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QWidget
    from ui.styles.design_system import DesignSystem
    from ui.styles.icons import icon_manager
    
    group = QGroupBox("Información de Fechas")
    group.setStyleSheet(f"""
        QGroupBox {{
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
            border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
            border-radius: {DesignSystem.RADIUS_LG}px;
            padding: {DesignSystem.SPACE_16}px;
            margin: 0;
            background-color: {DesignSystem.COLOR_SURFACE};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: {DesignSystem.SPACE_12}px;
            padding: 0 {DesignSystem.SPACE_8}px;
            color: {DesignSystem.COLOR_PRIMARY};
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        }}
    """)
    
    layout = QVBoxLayout()
    layout.setContentsMargins(
        DesignSystem.SPACE_16, DesignSystem.SPACE_24, 
        DesignSystem.SPACE_16, DesignSystem.SPACE_16
    )
    layout.setSpacing(DesignSystem.SPACE_12)
    
    # === FECHA SELECCIONADA (la que usa la aplicación) ===
    if dates_info.get('selected_date'):
        selected_row = _create_date_row(
            "Fecha utilizada por la aplicación", 
            dates_info['selected_date'].strftime("%Y-%m-%d %H:%M:%S"),
            f"Fuente: {dates_info.get('selected_source', 'Desconocida')}",
            'check-circle',
            DesignSystem.COLOR_SUCCESS
        )
        layout.addWidget(selected_row)
        
        # Separador sutil
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_CARD_BORDER};")
        layout.addWidget(separator)
    
    # === FECHAS EXIF ===
    exif_dates_added = False
    
    # DateTimeOriginal (fecha de captura principal)
    if dates_info.get('exif_date_time_original'):
        tz_info = ""
        if dates_info.get('exif_offset_time'):
            tz_info = f" (Zona horaria: {dates_info['exif_offset_time']})"
        exif_row = _create_date_row(
            "EXIF DateTimeOriginal", 
            dates_info['exif_date_time_original'].strftime("%Y-%m-%d %H:%M:%S"),
            f"Fecha de captura original{tz_info}",
            'camera',
            DesignSystem.COLOR_ACCENT
        )
        layout.addWidget(exif_row)
        exif_dates_added = True
    
    # CreateDate
    if dates_info.get('exif_create_date'):
        exif_row = _create_date_row(
            "EXIF CreateDate", 
            dates_info['exif_create_date'].strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha de creación del archivo según EXIF",
            'camera',
            DesignSystem.COLOR_ACCENT
        )
        layout.addWidget(exif_row)
        exif_dates_added = True
    
    # DateTimeDigitized
    if dates_info.get('exif_date_digitized'):
        exif_row = _create_date_row(
            "EXIF DateTimeDigitized", 
            dates_info['exif_date_digitized'].strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha de digitalización",
            'camera',
            DesignSystem.COLOR_ACCENT
        )
        layout.addWidget(exif_row)
        exif_dates_added = True
    
    # GPS DateStamp
    if dates_info.get('exif_gps_date'):
        exif_row = _create_date_row(
            "EXIF GPS DateStamp", 
            dates_info['exif_gps_date'].strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha GPS del archivo",
            'map-marker',
            DesignSystem.COLOR_ACCENT
        )
        layout.addWidget(exif_row)
        exif_dates_added = True
    
    # Software EXIF
    if dates_info.get('exif_software'):
        software_row = _create_info_row(
            "Software EXIF", 
            dates_info['exif_software'],
            "Aplicación que creó/modificó el archivo",
            'cog'
        )
        layout.addWidget(software_row)
        exif_dates_added = True
    
    # Separador después de EXIF si se agregó algo
    if exif_dates_added:
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_CARD_BORDER};")
        layout.addWidget(separator)
    
    # === FECHA DEL NOMBRE DE ARCHIVO ===
    if dates_info.get('filename_date'):
        filename_row = _create_date_row(
            "Fecha del nombre", 
            dates_info['filename_date'].strftime("%Y-%m-%d %H:%M:%S"),
            "Extraída del nombre del archivo (WhatsApp, etc.)",
            'file-document-outline',
            DesignSystem.COLOR_INFO
        )
        layout.addWidget(filename_row)
    
    # === METADATA DE VIDEO ===
    if dates_info.get('video_metadata_date'):
        video_row = _create_date_row(
            "Metadata de video", 
            dates_info['video_metadata_date'].strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha de creación del video (ffprobe)",
            'video',
            DesignSystem.COLOR_INFO
        )
        layout.addWidget(video_row)
    
    # Separador antes de fechas del sistema
    if dates_info.get('filename_date') or dates_info.get('video_metadata_date'):
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_CARD_BORDER};")
        layout.addWidget(separator)
    
    # === FECHAS DEL SISTEMA DE ARCHIVOS ===
    
    # Fecha de creación
    if dates_info.get('creation_date'):
        source_desc = "Fecha de creación del archivo" if dates_info.get('creation_source') == 'birth' else "Fecha de creación (ctime)"
        creation_row = _create_date_row(
            "Fecha de creación", 
            dates_info['creation_date'].strftime("%Y-%m-%d %H:%M:%S"),
            source_desc,
            'update',
            DesignSystem.COLOR_TEXT_SECONDARY
        )
        layout.addWidget(creation_row)
    
    # Fecha de modificación
    if dates_info.get('modification_date'):
        mod_row = _create_date_row(
            "Fecha de modificación", 
            dates_info['modification_date'].strftime("%Y-%m-%d %H:%M:%S"),
            "Última modificación del archivo",
            'clock-outline',
            DesignSystem.COLOR_TEXT_SECONDARY
        )
        layout.addWidget(mod_row)
    
    # Fecha de último acceso
    if dates_info.get('access_date'):
        access_row = _create_date_row(
            "Último acceso", 
            dates_info['access_date'].strftime("%Y-%m-%d %H:%M:%S"),
            "Última vez que se accedió al archivo",
            'clock-outline',
            DesignSystem.COLOR_TEXT_SECONDARY
        )
        layout.addWidget(access_row)
    
    group.setLayout(layout)
    return group


def _create_info_row(title: str, value_text: str, description: str, icon_name: str):
    """Crea una fila especializada para mostrar información no-fechas"""
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
    from ui.styles.design_system import DesignSystem
    from ui.styles.icons import icon_manager
    
    widget = QWidget()
    main_layout = QHBoxLayout(widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(DesignSystem.SPACE_12)
    
    # Icono
    icon = icon_manager.get_icon(icon_name, size=DesignSystem.ICON_SIZE_MD, color=DesignSystem.COLOR_ACCENT)
    icon_label = QLabel()
    icon_label.setPixmap(icon.pixmap(DesignSystem.ICON_SIZE_MD, DesignSystem.ICON_SIZE_MD))
    icon_label.setFixedSize(DesignSystem.ICON_SIZE_MD + 4, DesignSystem.ICON_SIZE_MD + 4)
    main_layout.addWidget(icon_label)
    
    # Contenido de información
    content_layout = QVBoxLayout()
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(DesignSystem.SPACE_2)
    
    # Título y valor
    title_label = QLabel(f"{title}: {value_text}")
    title_label.setStyleSheet(f"""
        color: {DesignSystem.COLOR_TEXT};
        font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        font-size: {DesignSystem.FONT_SIZE_BASE}px;
    """)
    content_layout.addWidget(title_label)
    
    # Descripción
    desc_label = QLabel(description)
    desc_label.setStyleSheet(f"""
        color: {DesignSystem.COLOR_TEXT_SECONDARY};
        font-size: {DesignSystem.FONT_SIZE_SM}px;
    """)
    content_layout.addWidget(desc_label)
    
    main_layout.addLayout(content_layout, 1)
    
    return widget


def _create_date_row(title: str, date_str: str, description: str, icon_name: str, accent_color: str):
    """Crea una fila especializada para mostrar información de fecha"""
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
    from ui.styles.design_system import DesignSystem
    from ui.styles.icons import icon_manager
    
    widget = QWidget()
    main_layout = QHBoxLayout(widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(DesignSystem.SPACE_12)
    
    # Icono
    icon = icon_manager.get_icon(icon_name, size=DesignSystem.ICON_SIZE_MD, color=accent_color)
    icon_label = QLabel()
    icon_label.setPixmap(icon.pixmap(DesignSystem.ICON_SIZE_MD, DesignSystem.ICON_SIZE_MD))
    icon_label.setFixedSize(DesignSystem.ICON_SIZE_MD + 4, DesignSystem.ICON_SIZE_MD + 4)
    main_layout.addWidget(icon_label)
    
    # Contenido de fecha
    content_layout = QVBoxLayout()
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(DesignSystem.SPACE_2)
    
    # Título y fecha
    title_label = QLabel(f"{title}: {date_str}")
    title_label.setStyleSheet(f"""
        color: {DesignSystem.COLOR_TEXT};
        font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        font-size: {DesignSystem.FONT_SIZE_BASE}px;
    """)
    content_layout.addWidget(title_label)
    
    # Descripción
    desc_label = QLabel(description)
    desc_label.setStyleSheet(f"""
        color: {DesignSystem.COLOR_TEXT_SECONDARY};
        font-size: {DesignSystem.FONT_SIZE_SM}px;
    """)
    content_layout.addWidget(desc_label)
    
    main_layout.addLayout(content_layout, 1)
    
    return widget


def _get_file_type_display(file_path: Path) -> str:
    """Obtiene una descripción amigable del tipo de archivo"""
    from config import Config
    
    from utils.file_utils import get_file_type
    file_type = get_file_type(file_path)
    if file_type == 'image':
        return "Imagen"
    elif file_type == 'video':
        return "Video"
    else:
        return f"Archivo {file_path.suffix.upper()}"


def _open_file_and_close(file_path: Path, dialog):
    """Abre el archivo y cierra el diálogo"""
    open_file(file_path)
    dialog.accept()


def _open_folder_and_close(file_path: Path, dialog):
    """Abre la carpeta del archivo y cierra el diálogo"""
    open_folder(file_path.parent)
    dialog.accept()



