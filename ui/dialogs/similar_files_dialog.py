"""
Diálogo de gestión de archivos similares con slider interactivo.

Permite ajustar la sensibilidad de detección en tiempo real y gestionar
los grupos de archivos similares detectados sin necesidad de reanalizar.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSlider, QPushButton,
    QDialogButtonBox, QCheckBox, QGroupBox, QScrollArea, QWidget,
    QGridLayout, QSizePolicy, QProgressBar, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QDesktopServices, QCursor, QImage
from PyQt6.QtCore import QUrl
from config import Config
from services.similar_files_detector import SimilarFilesAnalysis, DuplicateGroup
from utils.format_utils import format_size
from ui.styles.design_system import DesignSystem  # Keep for backwards compatibility with existing code
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from .base_dialog import BaseDialog
from .dialog_utils import show_file_details_dialog


class SimilarFilesDialog(BaseDialog):
    """
    Diálogo para gestionar archivos similares con slider de sensibilidad.
    
    Permite ajustar la sensibilidad en tiempo real y ver cómo afecta
    a los grupos detectados, sin necesidad de reanalizar.
    """

    def __init__(self, analysis: SimilarFilesAnalysis, parent=None):
        """
        Inicializa el diálogo.
        
        Args:
            analysis: Objeto SimilarFilesAnalysis con hashes calculados
            parent: Widget padre
        """
        super().__init__(parent)
        
        self.analysis = analysis
        self.current_sensitivity = 85  # Valor inicial predeterminado
        self.current_result = None
        self.current_group_index = 0
        self.selections = {}  # {group_index: [files_to_delete]}
        self.accepted_plan = None
        
        self._setup_ui()
        self._load_initial_results()
    
    def _setup_ui(self):
        """Configura la interfaz del diálogo."""
        # Configuración de la ventana
        self.setWindowTitle("Gestionar archivos similares")
        self.setModal(True)
        self.resize(900, 700)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, DesignSystem.SPACE_20)
        
        # --- HEADER: Título compacto con métricas iniciales (se actualizarán) ---
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='content-duplicate',
            title='Archivos similares detectados',
            description='Imágenes visualmente parecidas (perceptual hash). Ajusta la sensibilidad para refinar.',
            metrics=[
                {'value': '0', 'label': 'Grupos', 'color': DesignSystem.COLOR_PRIMARY},
                {'value': '0', 'label': 'Duplicados', 'color': DesignSystem.COLOR_WARNING},
                {'value': '0 B', 'label': 'Espacio', 'color': DesignSystem.COLOR_SUCCESS}
            ]
        )
        main_layout.addWidget(self.header_frame)
        
        # Contenedor con márgenes para el resto del contenido
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(DesignSystem.SPACE_20)
        content_layout.setContentsMargins(
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_24,
            0
        )
        main_layout.addWidget(content_container)
        
        # --- SECCIÓN 1: Card de sensibilidad ---
        sensitivity_card = self._create_sensitivity_card()
        content_layout.addWidget(sensitivity_card)
        
        # --- SECCIÓN 2: Barra de advertencia ---
        warning_frame = self._create_warning_section()
        content_layout.addWidget(warning_frame)
        
        # --- SECCIÓN 3: Navegación de grupos ---
        nav_layout = self._create_navigation_section()
        content_layout.addLayout(nav_layout)
        
        # --- SECCIÓN 4: Contenedor de grupo actual ---
        self.group_container = QGroupBox()
        self.group_layout = QVBoxLayout(self.group_container)
        content_layout.addWidget(self.group_container)
        
        # --- SECCIÓN 5: Resumen ---
        summary_group = self._create_summary_section()
        content_layout.addWidget(summary_group)
        
        # --- SECCIÓN 6: Opciones de seguridad ---
        options_group = self._create_options_section()
        content_layout.addWidget(options_group)
        
        # --- SECCIÓN 7: Botones de acción ---
        buttons = self._create_action_buttons()
        content_layout.addWidget(buttons)
        
        # Aplicar estilos
        self.setStyleSheet(self._get_dialog_styles())
    
    def _create_sensitivity_card(self) -> QFrame:
        """
        Crea la card con slider de sensibilidad interactivo.
        
        Returns:
            QFrame con slider y controles
        """
        card = QFrame()
        card.setObjectName("sensitivity_card")
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setContentsMargins(
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_16
        )
        
        # Título de la card con icono
        title_layout = QHBoxLayout()
        title_icon = icon_manager.get_icon('options', size=20)
        title_icon_label = QLabel()
        title_icon_label.setPixmap(title_icon.pixmap(20, 20))
        title_layout.addWidget(title_icon_label)
        
        title = QLabel("Ajustar sensibilidad de detección")
        title.setObjectName("card_title")
        title_layout.addWidget(title)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # Layout del slider
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(DesignSystem.SPACE_12)
        
        # Label izquierda
        left_label = QLabel("Menos estricto\n30%")
        left_label.setObjectName("slider_label")
        left_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Slider horizontal
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setObjectName("sensitivity_slider")
        self.sensitivity_slider.setRange(30, 100)
        self.sensitivity_slider.setValue(self.current_sensitivity)
        self.sensitivity_slider.setSingleStep(5)
        self.sensitivity_slider.setPageStep(10)
        self.sensitivity_slider.setTickInterval(10)
        self.sensitivity_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        
        # Label derecha
        right_label = QLabel("Más estricto\n100%")
        right_label.setObjectName("slider_label")
        right_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        slider_layout.addWidget(left_label)
        slider_layout.addWidget(self.sensitivity_slider)
        slider_layout.addWidget(right_label)
        
        layout.addLayout(slider_layout)
        
        # Display de estadísticas en tiempo real
        self.stats_label = QLabel()
        self.stats_label.setObjectName("stats_label")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stats_label)
        
        # Mensaje de ayuda con icono
        help_icon = icon_manager.get_icon('info', size=16)
        help_layout = QHBoxLayout()
        help_icon_label = QLabel()
        help_icon_label.setPixmap(help_icon.pixmap(16, 16))
        help_layout.addWidget(help_icon_label)
        
        help_label = QLabel(
            "Mueve el slider para ajustar qué tan similares "
            "deben ser las imágenes para agruparse"
        )
        help_label.setObjectName("help_label")
        help_label.setWordWrap(True)
        help_layout.addWidget(help_label)
        help_layout.addStretch()
        layout.addLayout(help_layout)
        
        # Conectar señales
        self.sensitivity_slider.valueChanged.connect(
            self._on_slider_value_changed
        )
        self.sensitivity_slider.sliderReleased.connect(
            self._on_slider_released
        )
        
        return card
    
    def _create_warning_section(self) -> QFrame:
        """Crea la sección de advertencia."""
        warning_frame = QFrame()
        warning_frame.setObjectName("warning_frame")
        
        warning_layout = QVBoxLayout(warning_frame)
        warning_layout.setSpacing(DesignSystem.SPACE_8)
        warning_layout.setContentsMargins(
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_8,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_8
        )
        
        warning_icon = icon_manager.get_icon('warning', size=16)
        warning_text_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(warning_icon.pixmap(16, 16))
        warning_text_layout.addWidget(icon_label)
        
        warning = QLabel(
            "Estos archivos son similares pero NO idénticos. "
            "Revisa cada grupo cuidadosamente antes de eliminar."
        )
        warning.setWordWrap(True)
        warning.setObjectName("warning_text")
        warning_text_layout.addWidget(warning)
        warning_layout.addLayout(warning_text_layout)
        
        return warning_frame
    
    def _create_navigation_section(self) -> QHBoxLayout:
        """Crea la sección de navegación de grupos."""
        nav_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton()
        prev_icon = icon_manager.get_icon('chevron-left', size=18)
        self.prev_btn.setIcon(prev_icon)
        self.prev_btn.setText("Anterior")
        self.prev_btn.clicked.connect(self._previous_group)
        
        self.group_label = QLabel()
        self.group_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_label.setObjectName("group_label")
        
        self.next_btn = QPushButton()
        next_icon = icon_manager.get_icon('chevron-right', size=18)
        self.next_btn.setIcon(next_icon)
        self.next_btn.setText("Siguiente")
        self.next_btn.clicked.connect(self._next_group)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.group_label, 1)
        nav_layout.addWidget(self.next_btn)
        
        return nav_layout
    
    def _create_summary_section(self) -> QGroupBox:
        """Crea la sección de resumen."""
        summary_group = QGroupBox("Resumen")
        summary_group.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        summary_group.setMinimumHeight(80)
        
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.setContentsMargins(
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_16,
            DesignSystem.SPACE_16
        )
        
        self.summary_label = QLabel()
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        self.summary_label.setWordWrap(True)
        self.summary_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.summary_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        summary_layout.addWidget(self.summary_label)
        
        return summary_group
    
    def _create_options_section(self) -> QGroupBox:
        """Crea la sección de opciones de seguridad."""
        options_group = QGroupBox("Opciones de Seguridad")
        options_group.setMinimumWidth(400)
        
        options_layout = QVBoxLayout(options_group)
        
        # Backup checkbox
        self.add_backup_checkbox(
            options_layout,
            "Crear backup antes de eliminar (Recomendado)"
        )
        
        # Simulación checkbox
        self.dry_run_checkbox = QCheckBox(
            "Modo simulación (no eliminar archivos realmente)"
        )
        
        # Leer configuración para establecer estado por defecto
        from utils.settings_manager import settings_manager
        dry_run_default = settings_manager.get(
            settings_manager.KEY_DRY_RUN_DEFAULT,
            False
        )
        # Asegurar que es un booleano
        if isinstance(dry_run_default, str):
            dry_run_default = dry_run_default.lower() in (
                'true', '1', 'yes'
            )
        self.dry_run_checkbox.setChecked(bool(dry_run_default))
        options_layout.addWidget(self.dry_run_checkbox)
        
        return options_group
    
    def _create_action_buttons(self) -> QDialogButtonBox:
        """Crea los botones de acción del diálogo."""
        buttons = self.make_ok_cancel_buttons(
            ok_text="Eliminar Seleccionados",
            ok_enabled=False
        )
        self.ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        icon_manager.set_button_icon(self.ok_btn, 'delete', size=16)
        
        return buttons

    def _load_group(self, index):
        """Carga y muestra un grupo específico con miniaturas"""
        if not 0 <= index < len(self.analysis.groups):
            return
        self.current_group_index = index
        group = self.analysis.groups[index]

        # Actualizar navegación
        total_groups = len(self.analysis.groups)
        self.group_label.setText(f"Grupo {index + 1} de {total_groups}")
        # Con navegación circular, los botones siempre están habilitados
        self.prev_btn.setEnabled(True)
        self.next_btn.setEnabled(True)

        # Limpiar layout anterior
        for i in reversed(range(self.group_layout.count())):
            widget = self.group_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Métrica de similitud visual
        similarity_widget = self._create_similarity_widget(group)
        self.group_layout.addWidget(similarity_widget)

        # Info del grupo
        info_label = QLabel(
            f"<b>Archivos:</b> {group.file_count} | "
            f"<b>Tamaño total:</b> {format_size(group.total_size)}"
        )
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setStyleSheet(DesignSystem.STYLE_PANEL_LABEL)
        self.group_layout.addWidget(info_label)

        # Advertencia si hay demasiadas imágenes
        max_thumbnails = 20
        if len(group.files) > max_thumbnails:
            warning_label = QLabel(
                f"Este grupo tiene {len(group.files)} imágenes. "
                f"Para mejor rendimiento, usa el scroll para navegar."
            )
            warning_label.setStyleSheet(DesignSystem.STYLE_DIALOG_WARNING_ORANGE)
            warning_label.setWordWrap(True)
            self.group_layout.addWidget(warning_label)

        # Crear área con scroll para las miniaturas
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Widget contenedor de miniaturas
        thumbnails_widget = QWidget()
        thumbnails_layout = QGridLayout(thumbnails_widget)
        thumbnails_layout.setSpacing(10)

        previous_selection = self.selections.get(index, [])

        # Configurar grid (máximo 5 columnas)
        max_columns = 5
        for row_idx, file_path in enumerate(group.files):
            row = row_idx // max_columns
            col = row_idx % max_columns

            # Frame contenedor para cada imagen
            frame = QFrame()
            frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            frame.setLineWidth(1)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setSpacing(0)
            frame_layout.setContentsMargins(0, 0, 0, 0)

            # === SECCIÓN 1: CHECKBOX DE ELIMINACIÓN ===
            delete_section = QWidget()
            delete_section_layout = QVBoxLayout(delete_section)
            delete_section_layout.setContentsMargins(10, 10, 10, 10)
            delete_section_layout.setSpacing(0)
            
            checkbox = QCheckBox("Eliminar este archivo")
            checkbox.setChecked(file_path in previous_selection)
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-weight: 600;
                    font-size: 11px;
                    padding: 5px;
                    color: #DC3545;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border: 2px solid #DC3545;
                    border-radius: 4px;
                    background-color: white;
                }
                QCheckBox::indicator:checked {
                    background-color: #DC3545;
                    border-color: #DC3545;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTMuNSA0TDYgMTEuNSAyLjUgOCIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
                }
                QCheckBox::indicator:hover {
                    border-color: #BB2D3B;
                }
            """)
            checkbox.stateChanged.connect(lambda state, f=file_path: self._on_selection_changed(f, state))
            delete_section_layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
            
            # Diseño más limpio: borde rojo sutil en lugar de fondo amarillo
            delete_section.setStyleSheet("""
                QWidget {
                    background-color: #FFFFFF;
                    padding: 10px;
                    border-bottom: 2px solid #F8D7DA;
                }
            """)
            frame_layout.addWidget(delete_section)

            # === SECCIÓN 2: MINIATURA (PREVIEW) ===
            preview_section = QWidget()
            preview_section_layout = QVBoxLayout(preview_section)
            preview_section_layout.setContentsMargins(5, 5, 5, 5)
            preview_section_layout.setSpacing(3)
            
            thumbnail_label, is_video = self._create_thumbnail(file_path)
            
            # Si es video, añadir indicador visual
            if is_video:
                video_indicator = QLabel("VIDEO - Frame de comparación")
                video_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
                video_indicator.setStyleSheet("""
                    background-color: #6F42C1;
                    color: white;
                    font-size: 9px;
                    font-weight: bold;
                    padding: 3px;
                    border-radius: 3px;
                    margin-bottom: 3px;
                """)
                preview_section_layout.addWidget(video_indicator)
            
            if thumbnail_label:
                thumbnail_label.mousePressEvent = lambda event, f=file_path: self._open_file(f)
                thumbnail_label.setCursor(Qt.CursorShape.PointingHandCursor)
                thumbnail_label.setToolTip(f"Clic para abrir: {file_path.name}")
                preview_section_layout.addWidget(thumbnail_label, alignment=Qt.AlignmentFlag.AlignCenter)
            else:
                # Si no se puede cargar la imagen, mostrar placeholder
                no_preview = QLabel("Sin vista previa")
                no_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_preview.setStyleSheet(DesignSystem.STYLE_DIALOG_NO_PREVIEW)
                preview_section_layout.addWidget(no_preview)
            
            preview_section.setStyleSheet("""
                QWidget {
                    background-color: #E9ECEF;
                    padding: 10px;
                }
            """)
            frame_layout.addWidget(preview_section)

            # === SECCIÓN 3: INFORMACIÓN COMPACTA DEL ARCHIVO (con menú contextual) ===
            info_section = QWidget()
            info_section.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            info_section.customContextMenuRequested.connect(
                lambda pos, f=file_path: self._show_file_context_menu(pos, f, info_section)
            )
            info_section.setCursor(Qt.CursorShape.PointingHandCursor)
            info_section.setToolTip("Clic derecho para más opciones")
            
            info_section_layout = QVBoxLayout(info_section)
            info_section_layout.setContentsMargins(10, 8, 10, 8)
            info_section_layout.setSpacing(3)
            
            from datetime import datetime
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            # Nombre del archivo (con icono)
            name_label = QLabel(f"<b>{file_path.name[:25]}{'...' if len(file_path.name) > 25 else ''}</b>")
            name_label.setTextFormat(Qt.TextFormat.RichText)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setWordWrap(True)
            name_label.setStyleSheet(DesignSystem.STYLE_DIALOG_NAME_LABEL)
            info_section_layout.addWidget(name_label)
            
            # Tamaño y fecha en una línea compacta
            details_label = QLabel(
                f"{format_size(file_path.stat().st_size)} • "
                f"{mtime.strftime('%Y-%m-%d %H:%M')}"
            )
            details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            details_label.setStyleSheet(DesignSystem.STYLE_DIALOG_DETAILS_LABEL)
            info_section_layout.addWidget(details_label)
            
            # Estilo con hover para indicar que es clickeable
            info_section.setStyleSheet("""
                QWidget {
                    background-color: #F8F9FA;
                    padding: 8px;
                    border-radius: 4px;
                }
                QWidget:hover {
                    background-color: #E9ECEF;
                }
            """)
            frame_layout.addWidget(info_section)

            # Destacar el frame si está seleccionado
            if file_path in previous_selection:
                frame.setStyleSheet("""
                    QFrame {
                        border: 2px solid #DC3545;
                        background-color: #FFFFFF;
                        border-radius: 6px;
                    }
                """)
            else:
                frame.setStyleSheet("""
                    QFrame {
                        border: 1px solid #CED4DA;
                        background-color: #FFFFFF;
                        border-radius: 6px;
                    }
                """)

            # Conectar cambios de selección para actualizar el estilo del frame
            checkbox.stateChanged.connect(
                lambda state, fr=frame, f=file_path: self._update_frame_style(fr, f, state)
            )

            thumbnails_layout.addWidget(frame, row, col)

        scroll_area.setWidget(thumbnails_widget)
        scroll_area.setMinimumHeight(400)
        self.group_layout.addWidget(scroll_area)

        self._update_summary()

    def _create_similarity_widget(self, group) -> QWidget:
        """Crea un widget visual para mostrar el grado de similitud"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Título
        title_label = QLabel("Grado de Similitud")
        title_label.setStyleSheet(DesignSystem.STYLE_DIALOG_TITLE_BOLD)
        layout.addWidget(title_label)

        # Barra de progreso visual
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(int(group.similarity_score))
        progress_bar.setTextVisible(True)
        progress_bar.setFormat(f"{group.similarity_score:.1f}%")
        progress_bar.setMinimumHeight(30)

        # Estilo de la barra según el nivel de similitud
        similarity_color, similarity_text, similarity_icon = self._get_similarity_level(group.similarity_score)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #BDC3C7;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                font-size: 13px;
                background-color: #ECF0F1;
            }}
            QProgressBar::chunk {{
                background-color: {similarity_color};
                border-radius: 6px;
            }}
        """)
        layout.addWidget(progress_bar)

        # Interpretación del nivel
        interpretation_label = QLabel(
            f"{similarity_icon} <b>Nivel:</b> {similarity_text}"
        )
        interpretation_label.setTextFormat(Qt.TextFormat.RichText)
        interpretation_label.setStyleSheet(f"""
            color: {similarity_color};
            font-size: 13px;
            padding: 5px;
            background-color: {similarity_color}20;
            border-radius: 5px;
            border: 1px solid {similarity_color};
        """)
        layout.addWidget(interpretation_label)

        # Descripción explicativa
        description = self._get_similarity_description(group.similarity_score)
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(DesignSystem.STYLE_DIALOG_DESC_MUTED)
        layout.addWidget(desc_label)

        container.setStyleSheet("""
            QWidget {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
            }
        """)

        return container

    def _get_similarity_level(self, score: float) -> tuple:
        """Retorna (color, texto, icono) según el nivel de similitud"""
        if score >= 95:
            return ("#27AE60", "Casi Idénticas", "🟢")
        elif score >= 85:
            return ("#3498DB", "Muy Similares", "🔵")
        elif score >= 75:
            return ("#F39C12", "Similares", "🟡")
        elif score >= 65:
            return ("#E67E22", "Moderadamente Similares", "🟠")
        else:
            return ("#E74C3C", "Poco Similares", "🔴")

    def _get_similarity_description(self, score: float) -> str:
        """Retorna una descripción explicativa del nivel de similitud"""
        if score >= 95:
            return "Las imágenes son prácticamente idénticas. Diferencias mínimas o imperceptibles."
        elif score >= 85:
            return "Las imágenes son muy parecidas. Pueden tener pequeñas diferencias en calidad, resolución o edición."
        elif score >= 75:
            return "Las imágenes comparten características significativas pero tienen diferencias notables."
        elif score >= 65:
            return "Las imágenes tienen similitudes pero también diferencias considerables. Revisa cuidadosamente."
        else:
            return "Las imágenes tienen pocas similitudes. Verifica que realmente sean duplicados antes de eliminar."

    def _create_thumbnail(self, file_path: Path) -> tuple:
        """Crea una miniatura para un archivo de imagen o video.
        
        Returns:
            tuple: (QLabel con la miniatura, bool indicando si es video)
        """
        try:
            # Extensiones soportadas
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.heic', '.heif'}
            video_extensions = {'.mov', '.mp4', '.avi', '.mkv', '.m4v', '.webm'}
            
            file_ext = file_path.suffix.lower()
            is_video = file_ext in video_extensions
            
            # Si no es imagen ni video, retornar None
            if file_ext not in image_extensions and file_ext not in video_extensions:
                return None, False
            
            pixmap = None
            
            # Para videos, extraer un frame fijo (frame 1 segundo)
            if is_video:
                try:
                    import cv2
                    import numpy as np
                    from PyQt6.QtGui import QImage
                    
                    # Abrir video
                    cap = cv2.VideoCapture(str(file_path))
                    
                    # Ir al frame del segundo 1 (frame 30 aprox si es 30fps)
                    # Usamos frame fijo para que sea consistente entre comparaciones
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
                    
                    # Leer frame
                    ret, frame = cap.read()
                    cap.release()
                    
                    if ret:
                        # Convertir de BGR (OpenCV) a RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # Convertir a QImage
                        h, w, ch = frame_rgb.shape
                        bytes_per_line = ch * w
                        qimage = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                        
                        # Convertir a QPixmap
                        pixmap = QPixmap.fromImage(qimage)
                    
                except ImportError:
                    # OpenCV no disponible, intentar con otro método
                    pass
                except Exception:
                    pass
            else:
                # Para imágenes, intentar cargar con QPixmap
                pixmap = QPixmap(str(file_path))
                
                # Si QPixmap falla (puede pasar con HEIC), intentar con pillow
                if pixmap.isNull():
                    try:
                        from PIL import Image
                        from PyQt6.QtGui import QImage
                        import io
                        
                        # Cargar con Pillow y convertir a QPixmap
                        img = Image.open(str(file_path))
                        img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                        
                        # Convertir PIL Image a QPixmap
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='PNG')
                        img_byte_arr.seek(0)
                        
                        qimage = QImage()
                        qimage.loadFromData(img_byte_arr.read())
                        pixmap = QPixmap.fromImage(qimage)
                    except ImportError:
                        pass
                    except Exception:
                        pass

            if pixmap is None or pixmap.isNull():
                return None, is_video

            # Redimensionar manteniendo aspecto (150x150 máximo)
            scaled_pixmap = pixmap.scaled(
                Config.THUMBNAIL_SIZE, Config.THUMBNAIL_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            label = QLabel()
            label.setPixmap(scaled_pixmap)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedSize(Config.THUMBNAIL_SIZE, Config.THUMBNAIL_SIZE)
            label.setStyleSheet(DesignSystem.STYLE_DIALOG_LABEL_DISABLED)
            return label, is_video
        except Exception:
            return None, False

    def _update_frame_style(self, frame: QFrame, file_path: Path, state):
        """Actualiza el estilo visual del frame según el estado de selección"""
        if state == Qt.CheckState.Checked:
            frame.setStyleSheet("""
                QFrame {
                    border: 2px solid #DC3545;
                    background-color: #FFFFFF;
                    border-radius: 6px;
                }
            """)
        else:
            frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #CED4DA;
                    background-color: #FFFFFF;
                    border-radius: 6px;
                }
            """)

    def _on_selection_changed(self, file_path, state):
        """Maneja cambios en la selección"""
        if self.current_group_index not in self.selections:
            self.selections[self.current_group_index] = []
        # Qt6 emite state como int: 0 (Unchecked), 2 (Checked)
        if state == Qt.CheckState.Checked.value or state == Qt.CheckState.Checked:
            if file_path not in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].append(file_path)
        else:
            if file_path in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].remove(file_path)
        self._update_summary()
    
    def _load_initial_results(self):
        """Carga resultados iniciales con sensibilidad predeterminada."""
        self._update_results(self.current_sensitivity)
    
    def _on_slider_value_changed(self, value: int):
        """
        Se llama mientras el usuario mueve el slider.
        
        Solo actualiza el display numérico, no recalcula todavía
        para dar feedback inmediato sin lag.
        
        Args:
            value: Nuevo valor del slider (30-100)
        """
        self.current_sensitivity = value
        # Actualizar solo el texto de estadísticas actuales
        self.stats_label.setText(
            f"Sensibilidad: {value}% | "
            f"Grupos: {self.current_result.total_groups if self.current_result else 0} | "
            f"Espacio recuperable: "
            f"{format_size(self.current_result.space_potential if self.current_result else 0)}"
        )
    
    def _on_slider_released(self):
        """Se llama cuando el usuario suelta el slider."""
        # Recalcular grupos con nueva sensibilidad
        self._update_results(self.current_sensitivity)
    
    def _update_results(self, sensitivity: int):
        """
        Actualiza la UI con resultados de nueva sensibilidad.
        
        MUY RÁPIDO (< 1 segundo) porque usa hashes pre-calculados.
        
        Args:
            sensitivity: Sensibilidad de detección (30-100)
        """
        # Obtener grupos con nueva sensibilidad (RÁPIDO)
        self.current_result = self.analysis.get_groups(sensitivity)
        
        # Actualizar estadísticas en la card de sensibilidad
        self.stats_label.setText(
            f"Sensibilidad: {sensitivity}% | "
            f"Grupos: {self.current_result.total_groups} | "
            f"Espacio recuperable: "
            f"{format_size(self.current_result.space_potential)}"
        )
        
        # Actualizar métricas del header compacto
        self._update_header_metrics(
            groups=self.current_result.total_groups,
            duplicates=self.current_result.total_duplicates,
            space=self.current_result.space_potential
        )
        
        # Actualizar la estructura analysis.groups para compatibilidad
        # con el código existente de visualización
        self.analysis.groups = self.current_result.groups
        
        # Limpiar selecciones previas (los grupos han cambiado)
        self.selections.clear()
        
        # Resetear al primer grupo
        self.current_group_index = 0
        
        # Recargar visualización del primer grupo
        if self.current_result.groups:
            self._load_group(0)
        else:
            # No hay grupos con esta sensibilidad
            self._show_no_groups_message()
    
    def _show_no_groups_message(self):
        """Muestra mensaje cuando no hay grupos con la sensibilidad actual."""
        # Limpiar layout del contenedor de grupos
        for i in reversed(range(self.group_layout.count())):
            widget = self.group_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Mostrar mensaje informativo
        no_groups_label = QLabel(
            "No se encontraron grupos con esta sensibilidad.\n\n"
            "Prueba reducir la sensibilidad (mover slider a la izquierda) "
            "para detectar archivos menos similares."
        )
        no_groups_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        no_groups_label.setWordWrap(True)
        no_groups_label.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_40}px;
            }}
        """)
        self.group_layout.addWidget(no_groups_label)
        
        # Actualizar etiqueta de navegación
        self.group_label.setText("Sin grupos")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        
        # Actualizar resumen
        self.summary_label.setText(
            "<b>No hay archivos seleccionados.</b>"
        )
        self.ok_btn.setEnabled(False)
    
    def _get_dialog_styles(self) -> str:
        """Retorna los estilos CSS para el diálogo."""
        return f"""
            QDialog {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
            }}
            
            QFrame#sensitivity_card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
            
            QLabel#card_title {{
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QLabel#slider_label {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QSlider#sensitivity_slider {{
                height: 24px;
            }}
            
            QSlider#sensitivity_slider::groove:horizontal {{
                background: {DesignSystem.COLOR_SECONDARY};
                height: 4px;
                border-radius: 2px;
            }}
            
            QSlider#sensitivity_slider::handle:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;
                border: 2px solid {DesignSystem.COLOR_SURFACE};
            }}
            
            QSlider#sensitivity_slider::handle:horizontal:hover {{
                background: {DesignSystem.COLOR_PRIMARY_HOVER};
                width: 24px;
                height: 24px;
                margin: -10px 0;
                border-radius: 12px;
            }}
            
            QSlider#sensitivity_slider::sub-page:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border-radius: 2px;
            }}
            
            QLabel#stats_label {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                color: {DesignSystem.COLOR_PRIMARY};
            }}
            
            QLabel#help_label {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            
            QFrame#warning_frame {{
                background-color: {DesignSystem.COLOR_BG_4};
                border: 1px solid {DesignSystem.COLOR_WARNING};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            
            QLabel#warning_text {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT};
            }}
            
            QLabel#group_label {{
                font-size: {DesignSystem.FONT_SIZE_LG}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                color: {DesignSystem.COLOR_TEXT};
            }}
        """

    def _previous_group(self):
        """Navega al grupo anterior (circular: desde el primero va al último)"""
        # Solo navegar si hay grupos
        if not self.analysis.groups:
            return
        
        total_groups = len(self.analysis.groups)
        if self.current_group_index == 0:
            # Estamos en el primero, ir al último
            self._load_group(total_groups - 1)
        else:
            self._load_group(self.current_group_index - 1)

    def _next_group(self):
        """Navega al grupo siguiente (circular: desde el último va al primero)"""
        # Solo navegar si hay grupos
        if not self.analysis.groups:
            return
        
        total_groups = len(self.analysis.groups)
        if self.current_group_index >= total_groups - 1:
            # Estamos en el último, ir al primero
            self._load_group(0)
        else:
            self._load_group(self.current_group_index + 1)

    def _update_summary(self):
        """Actualiza el resumen de archivos seleccionados"""
        total_selected = sum(len(files) for files in self.selections.values())
        total_size = 0
        for files in self.selections.values():
            total_size += sum(f.stat().st_size for f in files)
        self.summary_label.setText(
            f"<b>Archivos seleccionados:</b> {total_selected} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Espacio a liberar:</b> {format_size(total_size)}"
        )
        self.ok_btn.setEnabled(total_selected > 0)
    
    def _update_header_metrics(self, groups: int, duplicates: int, space: int):
        """Actualiza las métricas del header compacto.
        
        Args:
            groups: Número de grupos detectados
            duplicates: Número total de duplicados
            space: Espacio recuperable en bytes
        """
        # Recrear el header con los nuevos valores
        old_header = self.header_frame
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='content-duplicate',
            title='Archivos similares detectados',
            description='Imágenes visualmente parecidas (perceptual hash). Ajusta la sensibilidad para refinar.',
            metrics=[
                {'value': str(groups), 'label': 'Grupos', 'color': DesignSystem.COLOR_PRIMARY},
                {'value': str(duplicates), 'label': 'Duplicados', 'color': DesignSystem.COLOR_WARNING},
                {'value': format_size(space), 'label': 'Espacio', 'color': DesignSystem.COLOR_SUCCESS}
            ]
        )
        
        # Reemplazar el widget en el layout
        layout = self.layout()
        layout.replaceWidget(old_header, self.header_frame)
        old_header.deleteLater()


    def accept(self):
        # Crear grupos filtrados solo con archivos a eliminar
        groups_to_process = []
        for group_idx, files_to_delete in self.selections.items():
            if files_to_delete:
                original_group = self.analysis.groups[group_idx]
                groups_to_process.append(DuplicateGroup(
                    hash_value=original_group.hash_value,
                    files=files_to_delete,
                    total_size=sum(f.stat().st_size for f in files_to_delete),
                    similarity_score=original_group.similarity_score
                ))
        self.accepted_plan = {
            'groups': groups_to_process,
            'keep_strategy': 'manual',
            'create_backup': self.backup_checkbox.isChecked(),
            'dry_run': self.dry_run_checkbox.isChecked()
        }
        super().accept()

    def _open_file(self, file_path: Path):
        """Abre un archivo con la aplicación predeterminada del sistema operativo"""
        if file_path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Archivo no encontrado", f"No se encontró el archivo:\n{file_path}")
    
    def _show_file_context_menu(self, position, file_path: Path, widget: QWidget):
        """Muestra menú contextual para un archivo con opciones de ver detalles"""
        menu = QMenu(self)
        
        # Opción para ver detalles del archivo
        details_action = menu.addAction("Ver detalles del archivo")
        details_action.triggered.connect(lambda: self._show_file_details(file_path))
        
        menu.addSeparator()
        
        # Opción para abrir el archivo
        open_action = menu.addAction("Abrir archivo")
        open_action.triggered.connect(lambda: self._open_file(file_path))
        
        # Opción para abrir la carpeta
        from .dialog_utils import open_folder
        open_folder_action = menu.addAction("Abrir carpeta")
        open_folder_action.triggered.connect(lambda: open_folder(file_path.parent, self))
        
        # Mostrar el menú en la posición exacta del cursor
        menu.exec(QCursor.pos())
    
    def _show_file_details(self, file_path: Path):
        """Muestra diálogo con detalles del archivo"""
        # Obtener el grupo actual para incluir contexto
        current_group = self.analysis.groups[self.current_group_index]
        
        # Preparar información adicional
        additional_info = {
            'file_type': Config.get_file_type(file_path),
            'metadata': {
                'Grupo': f'{self.current_group_index + 1} de {len(self.analysis.groups)}',
                'Similitud del grupo': f'{current_group.similarity_score:.1f}%',
                'Archivos en grupo': str(current_group.file_count),
                'Tamaño total del grupo': format_size(current_group.total_size),
            }
        }
        
        # Mostrar diálogo de detalles usando la utilidad
        show_file_details_dialog(file_path, self, additional_info)
