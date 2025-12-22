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
from utils.date_utils import get_date_from_file, get_all_file_dates, select_chosen_date, extract_date_from_filename
from utils.platform_utils import open_file_with_default_app, open_folder_in_explorer
from utils.logger import get_logger

# Logger del módulo siguiendo el patrón estándar del proyecto
logger = get_logger('UI.Dialogs.Utils')


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
    Muestra un diálogo con detalles completos del archivo usando toda la información
    disponible en FileMetadata desde el FileInfoRepositoryCache.
    
    ÚNICA FUENTE DE VERDAD: FileInfoRepositoryCache.get_file_metadata()
    Esta función obtiene directamente los metadatos del repositorio de caché.
    """
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                QPushButton, QFrame, QGroupBox, QWidget, QScrollArea)
    from PyQt6.QtCore import Qt
    from ui.styles.design_system import DesignSystem
    from ui.styles.icons import icon_manager
    from services.file_metadata_repository_cache import FileInfoRepositoryCache
    
    logger.debug(f"Mostrando detalles del archivo: {file_path.name}")
    
    # === 1. RECOPILACIÓN DE DATOS ===
    
    # Obtener TODA la información de metadatos desde el repositorio de caché
    # Esta función es la ÚNICA fuente de verdad para metadatos de archivos
    repo = FileInfoRepositoryCache.get_instance()
    metadata = repo.get_file_metadata(file_path)
    
    if metadata is None:
        logger.warning(f"No se encontraron metadatos en caché para {file_path}")
        # Fallback: intentar obtener con get_all_file_dates si no está en caché
        from utils.date_utils import get_all_file_dates
        metadata = get_all_file_dates(file_path)
    
    logger.debug(f"Metadatos obtenidos - Size: {metadata.fs_size}, Hash: {metadata.has_hash}, EXIF: {metadata.has_exif}, Best Date: {metadata.has_best_date}")
    
    # === 2. CONSTRUCCIÓN DE LA IU ===
    
    dialog = QDialog(parent_widget)
    dialog.setWindowTitle("Detalles del Archivo")
    dialog.setModal(True)
    dialog.setMinimumWidth(900)
    dialog.setMaximumWidth(950)
    dialog.setMinimumHeight(700)
    
    main_layout = QVBoxLayout(dialog)
    main_layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_20, DesignSystem.SPACE_24, DesignSystem.SPACE_20)
    main_layout.setSpacing(DesignSystem.SPACE_16)
    
    # Header
    header_layout = QHBoxLayout()
    header_layout.setSpacing(DesignSystem.SPACE_12)
    
    file_icon_name = 'image' if metadata.is_image else ('video' if metadata.is_video else 'file')
    header_icon = QLabel()
    icon_manager.set_label_icon(header_icon, file_icon_name, size=DesignSystem.ICON_SIZE_LG, color=DesignSystem.COLOR_PRIMARY)
    header_layout.addWidget(header_icon)
    
    title_label = QLabel(file_path.name)
    title_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_2XL}px; font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; color: {DesignSystem.COLOR_TEXT};")
    header_layout.addWidget(title_label)
    header_layout.addStretch()
    main_layout.addLayout(header_layout)
    
    # Área de scroll
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setStyleSheet(f"QScrollArea {{ border: 1px solid {DesignSystem.COLOR_CARD_BORDER}; border-radius: {DesignSystem.RADIUS_LG}px; background-color: {DesignSystem.COLOR_SURFACE}; }}")
    
    scroll_widget = QWidget()
    scroll_layout = QVBoxLayout(scroll_widget)
    scroll_layout.setContentsMargins(DesignSystem.SPACE_20, DesignSystem.SPACE_16, DesignSystem.SPACE_20, DesignSystem.SPACE_16)
    scroll_layout.setSpacing(DesignSystem.SPACE_20)
    
    # SECCIÓN: INFORMACIÓN GENERAL
    general_items = [
        ("Ubicación", str(file_path.parent), "Directorio donde se encuentra el archivo", 'folder', DesignSystem.COLOR_INFO),
        ("Nombre de archivo", file_path.name, "Nombre completo con extensión", 'file-document-outline', DesignSystem.COLOR_INFO),
        ("Tamaño en disco", format_size(metadata.fs_size), "Espacio que ocupa en el sistema de archivos", 'harddisk', DesignSystem.COLOR_INFO),
        ("Tipo de archivo", _get_file_type_display(file_path), "Categoría detectada por extensión", 'file-check', DesignSystem.COLOR_INFO),
    ]
    if metadata.sha256:
        general_items.append(("Hash SHA256", metadata.sha256, "Huella digital única del contenido del archivo", 'fingerprint', DesignSystem.COLOR_INFO))
    
    scroll_layout.addWidget(_create_enhanced_section("Información General", general_items))
    
    # SECCIÓN: FECHAS DEL SISTEMA (RAW FileMetadata)
    fs_dates = [
        ("Creación (ctime)", datetime.fromtimestamp(metadata.fs_ctime).strftime('%Y-%m-%d %H:%M:%S'), "Fecha de creación del archivo en el sistema de archivos", 'file-plus', DesignSystem.COLOR_WARNING),
        ("Modificación (mtime)", datetime.fromtimestamp(metadata.fs_mtime).strftime('%Y-%m-%d %H:%M:%S'), "Última modificación del contenido del archivo", 'file-edit', DesignSystem.COLOR_WARNING),
        ("Último acceso (atime)", datetime.fromtimestamp(metadata.fs_atime).strftime('%Y-%m-%d %H:%M:%S'), "Última vez que se abrió o leyó el archivo", 'eye', DesignSystem.COLOR_WARNING),
    ]
    scroll_layout.addWidget(_create_enhanced_section("Fechas del Sistema de Archivos", fs_dates))
    
    # SECCIÓN: DATOS EXIF (De FileMetadata structure)
    if metadata.has_exif:
        exif_items = []
        
        # Dimensiones
        if metadata.exif_ImageWidth:
            exif_items.append(("Ancho", f"{metadata.exif_ImageWidth} píxeles", "Ancho de la imagen original", 'ruler', DesignSystem.COLOR_ACCENT))
        if metadata.exif_ImageLength:
            exif_items.append(("Alto", f"{metadata.exif_ImageLength} píxeles", "Alto de la imagen original", 'ruler', DesignSystem.COLOR_ACCENT))
        
        # Versión EXIF
        if metadata.exif_ExifVersion:
            exif_items.append(("Versión EXIF", str(metadata.exif_ExifVersion), "Versión del estándar EXIF usado", 'information', DesignSystem.COLOR_ACCENT))
        
        # Software (solo si existe y es relevante - no duplicado)
        if metadata.exif_Software:
            exif_items.append(("Software", metadata.exif_Software, "Aplicación que creó o modificó el archivo", 'application-cog', DesignSystem.COLOR_ACCENT))
        
        # Subsegundos
        if metadata.exif_SubSecTimeOriginal:
            exif_items.append(("Subsegundos", metadata.exif_SubSecTimeOriginal, "Fracción de segundo en la captura original", 'timer-sand', DesignSystem.COLOR_ACCENT))
        
        # Zona horaria
        if metadata.exif_OffsetTimeOriginal:
            exif_items.append(("Zona horaria", metadata.exif_OffsetTimeOriginal, "Desplazamiento UTC en el momento de captura", 'clock-time-four', DesignSystem.COLOR_ACCENT))
        
        if exif_items:
            scroll_layout.addWidget(_create_enhanced_section("Metadatos Técnicos (EXIF)", exif_items))

    # SECCIÓN: INFORMACIÓN ADICIONAL (Fechas y metadatos adicionales)
    scroll_layout.addWidget(_create_dates_section(metadata))
    
    # SECCIÓN: CONTEXTO DE LA OPERACIÓN (Si hay información adicional del diálogo)
    if additional_info:
        add_items = []
        for key, val in additional_info.items():
            if key in ['metadata', 'target_path']: continue # Manejados aparte o ignorados
            icon = 'tag'
            if 'name' in key: icon = 'file-rename'
            if 'conflict' in key: icon = 'alert-decagram'
            add_items.append((key.replace('_', ' ').title(), str(val), icon))
        
        if add_items:
            scroll_layout.addWidget(_create_material_section("Contexto de la Operación", add_items))

    # SECCIÓN: MEJOR FECHA DISPONIBLE (Última sección - solo si existe)
    if metadata.best_date:
        scroll_layout.addWidget(_create_best_date_section(metadata))

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


def _create_enhanced_section(title: str, items: list):
    """Crea una sección mejorada con formato unificado (título + valor + descripción)
    
    Args:
        title: Título de la sección
        items: Lista de tuplas (título, valor, descripción, icono, color)
    """
    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QWidget
    from ui.styles.design_system import DesignSystem
    
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
    
    for i, (label_text, value_text, description, icon_name, accent_color) in enumerate(items):
        row = _create_info_row(label_text, value_text, description, icon_name, accent_color)
        layout.addWidget(row)
        
        # Agregar separador entre items (excepto el último)
        if i < len(items) - 1:
            separator = QWidget()
            separator.setFixedHeight(1)
            separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_CARD_BORDER}; margin: {DesignSystem.SPACE_4}px 0;")
            layout.addWidget(separator)
    
    group.setLayout(layout)
    return group


def _create_material_section(title: str, items: list, use_code_style: bool = False):
    """Crea una sección Material Design con título e items
    DEPRECATED: Usar _create_enhanced_section en su lugar
    """
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


def _create_dates_section(metadata: 'FileMetadata'):
    """Crea la sección especial de fechas con información detallada usando FileMetadata directamente"""
    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QHBoxLayout, QWidget
    from ui.styles.design_system import DesignSystem
    from ui.styles.icons import icon_manager
    from datetime import datetime
    from utils.date_utils import extract_date_from_filename
    
    # Helper para parsear fechas EXIF string a datetime
    def _parse_exif_date(date_str):
        if not date_str:
            return None
        try:
            if ':' in date_str[:10]:
                return datetime.strptime(date_str[:19], '%Y:%m:%d %H:%M:%S')
            elif 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return None
        except (ValueError, TypeError):
            return None
    
    group = QGroupBox("Fechas EXIF")
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
    
    # === FECHAS EXIF ===
    exif_dates_added = False
    
    # DateTimeOriginal (fecha de captura principal)
    exif_date_time_original = _parse_exif_date(metadata.exif_DateTimeOriginal)
    if exif_date_time_original:
        tz_info = ""
        if metadata.exif_OffsetTimeOriginal:
            tz_info = f" (Zona horaria: {metadata.exif_OffsetTimeOriginal})"
        exif_row = _create_date_row(
            "EXIF DateTimeOriginal", 
            exif_date_time_original.strftime("%Y-%m-%d %H:%M:%S"),
            f"Fecha de captura original{tz_info}",
            'camera',
            DesignSystem.COLOR_ACCENT
        )
        layout.addWidget(exif_row)
        exif_dates_added = True
    
    # CreateDate (DateTime en FileMetadata)
    exif_create_date = _parse_exif_date(metadata.exif_DateTime)
    if exif_create_date:
        exif_row = _create_date_row(
            "EXIF CreateDate", 
            exif_create_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha de creación del archivo según EXIF",
            'camera',
            DesignSystem.COLOR_ACCENT
        )
        layout.addWidget(exif_row)
        exif_dates_added = True
    
    # DateTimeDigitized
    exif_date_digitized = _parse_exif_date(metadata.exif_DateTimeDigitized)
    if exif_date_digitized:
        exif_row = _create_date_row(
            "EXIF DateTimeDigitized", 
            exif_date_digitized.strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha de digitalización",
            'camera',
            DesignSystem.COLOR_ACCENT
        )
        layout.addWidget(exif_row)
        exif_dates_added = True
    
    # GPS DateStamp
    exif_gps_date = _parse_exif_date(metadata.exif_GPSDateStamp)
    if exif_gps_date:
        exif_row = _create_date_row(
            "EXIF GPS DateStamp", 
            exif_gps_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha GPS del archivo",
            'map-marker',
            DesignSystem.COLOR_ACCENT
        )
        layout.addWidget(exif_row)
        exif_dates_added = True
    
    # Separador después de EXIF si se agregó algo
    if exif_dates_added:
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_CARD_BORDER}; margin: {DesignSystem.SPACE_8}px 0;")
        layout.addWidget(separator)
    
    # === FECHA DEL NOMBRE DE ARCHIVO ===
    filename_date = extract_date_from_filename(metadata.path.name)
    if filename_date:
        filename_row = _create_date_row(
            "Fecha del nombre", 
            filename_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Extraída del nombre del archivo (WhatsApp, etc.)",
            'file-document-outline',
            DesignSystem.COLOR_INFO
        )
        layout.addWidget(filename_row)
    
    # === METADATA DE VIDEO ===
    # Para videos, exif_DateTime contiene la fecha de creación del video
    if metadata.is_video and exif_create_date:
        video_row = _create_date_row(
            "Metadata de video", 
            exif_create_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha de creación del video (ffprobe)",
            'video',
            DesignSystem.COLOR_INFO
        )
        layout.addWidget(video_row)
    
    # Separador antes de fechas del sistema
    if filename_date or (metadata.is_video and exif_create_date):
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_CARD_BORDER};")
        layout.addWidget(separator)
    
    # === FECHAS DEL SISTEMA DE ARCHIVOS ===
    # NOTA: Las fechas del filesystem (ctime, mtime, atime) ya se muestran en la sección "Filesystem (RAW)"
    # por lo que no se repiten aquí para evitar duplicación
    
    group.setLayout(layout)
    return group


def _create_best_date_section(metadata: 'FileMetadata'):
    """Crea la sección especial para mostrar la mejor fecha disponible"""
    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
    from ui.styles.design_system import DesignSystem
    
    group = QGroupBox("Mejor Fecha Disponible")
    group.setStyleSheet(f"""
        QGroupBox {{
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
            border: 2px solid {DesignSystem.COLOR_SUCCESS};
            border-radius: {DesignSystem.RADIUS_LG}px;
            padding: {DesignSystem.SPACE_16}px;
            margin: 0;
            background-color: {DesignSystem.COLOR_SURFACE};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: {DesignSystem.SPACE_12}px;
            padding: 0 {DesignSystem.SPACE_8}px;
            color: {DesignSystem.COLOR_SUCCESS};
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        }}
    """)
    
    layout = QVBoxLayout()
    layout.setContentsMargins(
        DesignSystem.SPACE_16, DesignSystem.SPACE_24, 
        DesignSystem.SPACE_16, DesignSystem.SPACE_16
    )
    layout.setSpacing(DesignSystem.SPACE_12)
    
    best_date_row = _create_date_row(
        "Fecha seleccionada", 
        metadata.best_date.strftime("%Y-%m-%d %H:%M:%S"),
        f"Fecha más representativa seleccionada automáticamente (Origen: {metadata.best_date_source})",
        'calendar-check',
        DesignSystem.COLOR_SUCCESS
    )
    layout.addWidget(best_date_row)
    
    group.setLayout(layout)
    return group


def _create_info_row(title: str, value_text: str, description: str, icon_name: str, accent_color: str = None):
    """Crea una fila especializada para mostrar información con icono, título, valor y descripción
    
    Args:
        title: Título del campo
        value_text: Valor a mostrar
        description: Descripción explicativa
        icon_name: Nombre del icono MDI
        accent_color: Color del icono (opcional, por defecto COLOR_ACCENT)
    """
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
    from ui.styles.design_system import DesignSystem
    from ui.styles.icons import icon_manager
    
    if accent_color is None:
        accent_color = DesignSystem.COLOR_ACCENT
    
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
    title_label.setWordWrap(True)
    content_layout.addWidget(title_label)
    
    # Descripción
    desc_label = QLabel(description)
    desc_label.setStyleSheet(f"""
        color: {DesignSystem.COLOR_TEXT_SECONDARY};
        font-size: {DesignSystem.FONT_SIZE_SM}px;
    """)
    desc_label.setWordWrap(True)
    content_layout.addWidget(desc_label)
    
    main_layout.addLayout(content_layout, 1)
    
    return widget


def _create_date_row(title: str, date_str: str, description: str, icon_name: str, accent_color: str):
    """Crea una fila especializada para mostrar información de fecha
    
    Alias de _create_info_row para mantener compatibilidad con código existente.
    """
    return _create_info_row(title, date_str, description, icon_name, accent_color)


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



