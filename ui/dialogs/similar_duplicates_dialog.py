from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QGroupBox, QCheckBox, QDialogButtonBox, QPushButton,
    QHBoxLayout, QVBoxLayout as QVLayout, QScrollArea, QWidget, QGridLayout,
    QFrame, QSizePolicy, QProgressBar, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QDesktopServices, QCursor
from PyQt6.QtCore import QUrl
from config import Config
from services.duplicate_detector import DuplicateGroup
from utils.format_utils import format_size
from ui import ui_styles
from .base_dialog import BaseDialog
from .dialog_utils import show_file_details_dialog


class SimilarDuplicatesDialog(BaseDialog):
    """Diálogo para revisión de duplicados similares"""

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.current_group_index = 0
        self.selections = {}  # {group_index: [files_to_delete]}
        self.accepted_plan = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Revisar Duplicados Similares")
        self.setModal(True)
        self.resize(900, 700)
        layout = QVBoxLayout(self)

        # Advertencia con estilo sutil similar a heic_dialog
        warning_frame = QFrame()
        warning_frame.setFrameShape(QFrame.Shape.NoFrame)
        warning_frame.setStyleSheet("""
            QFrame { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #f8f9fa, stop:1 #e9ecef);
                border: none;
                border-radius: 6px; 
                padding: 10px;
            }
        """)
        warning_layout = QVLayout(warning_frame)
        warning_layout.setSpacing(2)
        warning_layout.setContentsMargins(12, 8, 12, 8)
        
        warning = QLabel(
            "ℹ️ Estos archivos son similares pero NO idénticos. "
            "Revisa cada grupo cuidadosamente antes de eliminar."
        )
        warning.setTextFormat(Qt.TextFormat.RichText)
        warning.setWordWrap(True)
        warning.setStyleSheet(ui_styles.STYLE_DIALOG_EXPLANATION_TEXT)
        warning_layout.addWidget(warning)
        
        layout.addWidget(warning_frame)

        # Navegación de grupos
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Anterior")
        self.prev_btn.clicked.connect(self._previous_group)
        nav_layout.addWidget(self.prev_btn)
        self.group_label = QLabel()
        self.group_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_label.setStyleSheet(ui_styles.STYLE_GROUP_LABEL)
        nav_layout.addWidget(self.group_label, 1)
        self.next_btn = QPushButton("Siguiente ▶")
        self.next_btn.clicked.connect(self._next_group)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)

        # Contenedor de grupo actual
        self.group_container = QGroupBox()
        self.group_layout = QVLayout(self.group_container)
        layout.addWidget(self.group_container)

        # Resumen
        summary_group = QGroupBox("📊 Resumen")
        summary_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        summary_group.setMinimumHeight(80)
        # Estilo para que el título quede dentro del cuadro
        summary_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 10pt;
                padding-top: 20px;
                margin-top: 10px;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 8px;
                left: 10px;
                top: 5px;
                color: #2c5aa0;
                font-size: 9pt;
            }
        """)
        summary_layout = QVLayout(summary_group)
        summary_layout.setContentsMargins(15, 15, 15, 15)
        summary_layout.setSpacing(5)
        self.summary_label = QLabel()
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        self.summary_label.setWordWrap(True)
        self.summary_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        summary_layout.addWidget(self.summary_label)
        layout.addWidget(summary_group)

        # Opciones de seguridad
        options_group = QGroupBox("⚙️ Opciones de Seguridad")
        options_group.setMinimumWidth(400)
        options_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        options_layout = QVLayout(options_group)
        
        # Backup checkbox (primero)
        self.add_backup_checkbox(options_layout, "💾 Crear backup antes de eliminar (Recomendado)")
        
        # Simulación checkbox (segundo)
        self.dry_run_checkbox = QCheckBox("🔍 Modo simulación (no eliminar archivos realmente)")
        # Leer configuración para establecer estado por defecto
        from utils.settings_manager import settings_manager
        dry_run_default = settings_manager.get(settings_manager.KEY_DRY_RUN_DEFAULT, False)
        # Asegurar que es un booleano
        if isinstance(dry_run_default, str):
            dry_run_default = dry_run_default.lower() in ('true', '1', 'yes')
        self.dry_run_checkbox.setChecked(bool(dry_run_default))
        options_layout.addWidget(self.dry_run_checkbox)
        layout.addWidget(options_group)

        # Botones
        buttons = self.make_ok_cancel_buttons(ok_text="🗑️ Eliminar Seleccionados", ok_enabled=False)
        self.ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        layout.addWidget(buttons)

        # Cargar primer grupo
        self._load_group(0)

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
        info_label.setStyleSheet(ui_styles.STYLE_PANEL_LABEL)
        self.group_layout.addWidget(info_label)

        # Advertencia si hay demasiadas imágenes
        max_thumbnails = 20
        if len(group.files) > max_thumbnails:
            warning_label = QLabel(
                f"⚠️ Este grupo tiene {len(group.files)} imágenes. "
                f"Para mejor rendimiento, usa el scroll para navegar."
            )
            warning_label.setStyleSheet(ui_styles.STYLE_DIALOG_WARNING_ORANGE)
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
            frame_layout = QVLayout(frame)
            frame_layout.setSpacing(0)
            frame_layout.setContentsMargins(0, 0, 0, 0)

            # === SECCIÓN 1: CHECKBOX DE ELIMINACIÓN ===
            delete_section = QWidget()
            delete_section_layout = QVLayout(delete_section)
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
            preview_section_layout = QVLayout(preview_section)
            preview_section_layout.setContentsMargins(5, 5, 5, 5)
            preview_section_layout.setSpacing(3)
            
            thumbnail_label, is_video = self._create_thumbnail(file_path)
            
            # Si es video, añadir indicador visual
            if is_video:
                video_indicator = QLabel("🎬 VIDEO - Frame de comparación")
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
                no_preview = QLabel("❌ Sin vista previa")
                no_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
                no_preview.setStyleSheet(ui_styles.STYLE_DIALOG_NO_PREVIEW)
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
            
            info_section_layout = QVLayout(info_section)
            info_section_layout.setContentsMargins(10, 8, 10, 8)
            info_section_layout.setSpacing(3)
            
            from datetime import datetime
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            # Nombre del archivo (con icono)
            name_label = QLabel(f"📄 <b>{file_path.name[:25]}{'...' if len(file_path.name) > 25 else ''}</b>")
            name_label.setTextFormat(Qt.TextFormat.RichText)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setWordWrap(True)
            name_label.setStyleSheet(ui_styles.STYLE_DIALOG_NAME_LABEL)
            info_section_layout.addWidget(name_label)
            
            # Tamaño y fecha en una línea compacta
            details_label = QLabel(
                f"💾 {format_size(file_path.stat().st_size)} • "
                f"📅 {mtime.strftime('%Y-%m-%d %H:%M')}"
            )
            details_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            details_label.setStyleSheet(ui_styles.STYLE_DIALOG_DETAILS_LABEL)
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
        layout = QVLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Título
        title_label = QLabel("🔍 Grado de Similitud")
        title_label.setStyleSheet(ui_styles.STYLE_DIALOG_TITLE_BOLD)
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
        desc_label.setStyleSheet(ui_styles.STYLE_DIALOG_DESC_MUTED)
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
            label.setStyleSheet(ui_styles.STYLE_DIALOG_LABEL_DISABLED)
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

    def _previous_group(self):
        """Navega al grupo anterior (circular: desde el primero va al último)"""
        total_groups = len(self.analysis.groups)
        if self.current_group_index == 0:
            # Estamos en el primero, ir al último
            self._load_group(total_groups - 1)
        else:
            self._load_group(self.current_group_index - 1)

    def _next_group(self):
        """Navega al grupo siguiente (circular: desde el último va al primero)"""
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
        details_action = menu.addAction("ℹ️ Ver detalles del archivo")
        details_action.triggered.connect(lambda: self._show_file_details(file_path))
        
        menu.addSeparator()
        
        # Opción para abrir el archivo
        open_action = menu.addAction("🔍 Abrir archivo")
        open_action.triggered.connect(lambda: self._open_file(file_path))
        
        # Opción para abrir la carpeta
        from .dialog_utils import open_folder
        open_folder_action = menu.addAction("📁 Abrir carpeta")
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
