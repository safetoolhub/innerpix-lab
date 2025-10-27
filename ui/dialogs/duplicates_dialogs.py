from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QGroupBox, QButtonGroup, QRadioButton,
    QTableWidget, QTableWidgetItem, QCheckBox, QDialogButtonBox, QPushButton,
    QHBoxLayout, QVBoxLayout as QVLayout, QScrollArea, QWidget, QGridLayout,
    QFrame, QSizePolicy, QProgressBar
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QDesktopServices
from PyQt5.QtCore import QUrl
from services.duplicate_detector import DuplicateGroup
from utils.format_utils import format_size
from ui import styles as ui_styles
from .base_dialog import BaseDialog


class ExactDuplicatesDialog(BaseDialog):
    """Diálogo para eliminación de duplicados exactos"""
    
    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.keep_strategy = 'oldest'
        self.accepted_plan = None
        self.init_ui()
    def init_ui(self):
        self.setWindowTitle("Eliminar Duplicados Exactos")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Información
        info = QLabel(
            f"📊 Se encontraron **{self.analysis['total_duplicates']} archivos duplicados** "
            f"en **{self.analysis['total_groups']} grupos**\n\n"
            f"💾 Espacio a liberar: **{format_size(self.analysis['space_wasted'])}**"
        )
        info.setTextFormat(Qt.RichText)
        info.setWordWrap(True)
        info.setStyleSheet(ui_styles.STYLE_INFO_SECTION)
        layout.addWidget(info)
        
        # Estrategia
        strategy_group = QGroupBox("🎯 Estrategia de Eliminación")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_buttons = QButtonGroup()
        
        r1 = QRadioButton("🕐 Mantener el más antiguo (Recomendado)")
        r1.setChecked(True)
        self.strategy_buttons.addButton(r1, 0)
        strategy_layout.addWidget(r1)
        
        r2 = QRadioButton("🕓 Mantener el más reciente")
        self.strategy_buttons.addButton(r2, 1)
        strategy_layout.addWidget(r2)
        
        
        self.strategy_buttons.buttonClicked.connect(self._on_strategy_changed)
        
        layout.addWidget(strategy_group)
        
        # Lista de grupos (primeros 10)
        groups_label = QLabel("📋 Vista previa de grupos:")
        groups_label.setStyleSheet(ui_styles.STYLE_GROUPS_LABEL)
        layout.addWidget(groups_label)
        
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Grupo", "Archivos", "Tamaño Total"])
        
        groups = self.analysis['groups'][:10]
        table.setRowCount(len(groups))
        
        for row, group in enumerate(groups):
            table.setItem(row, 0, QTableWidgetItem(f"Grupo {row + 1}"))
            table.setItem(row, 1, QTableWidgetItem(str(group.file_count)))
            table.setItem(row, 2, QTableWidgetItem(format_size(group.total_size)))
        
        table.setMaximumHeight(250)
        layout.addWidget(table)
        
        if len(self.analysis['groups']) > 10:
            more_label = QLabel(f"... y {len(self.analysis['groups']) - 10} grupos más")
            more_label.setStyleSheet(ui_styles.STYLE_MORE_ITALIC)
            layout.addWidget(more_label)
        
        # Opciones: backup checkbox desde BaseDialog
        self.add_backup_checkbox(layout, "☑ Crear backup antes de eliminar (Recomendado)", True)

        # Advertencia
        warning = QLabel(
            "⚠️ Estos son duplicados exactos (100%). Eliminarlos es seguro."
        )
        warning.setStyleSheet(ui_styles.STYLE_WARNING_LABEL)
        layout.addWidget(warning)

        # Botones
        buttons = self.make_ok_cancel_buttons(ok_text="🗑️ Eliminar Ahora")
        # apply danger style to ok button
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        ok_btn.setStyleSheet(ui_styles.STYLE_DANGER_BUTTON)
        layout.addWidget(buttons)
    
    def _on_strategy_changed(self, button):
        """Handle strategy change: only 'oldest' and 'newest' are supported."""
        strategies = {0: 'oldest', 1: 'newest'}
        self.keep_strategy = strategies[self.strategy_buttons.id(button)]
    
    def accept(self):
        self.accepted_plan = {
            'groups': self.analysis['groups'],
            'keep_strategy': self.keep_strategy,
            'create_backup': self.backup_checkbox.isChecked()
        }
        super().accept()


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

        # Advertencia
        warning = QLabel(
            "⚠️ <b>Estos archivos son similares pero NO idénticos.</b> "
            "Revisa cada grupo cuidadosamente antes de eliminar."
        )
        warning.setTextFormat(Qt.RichText)
        warning.setWordWrap(True)
        warning.setStyleSheet(ui_styles.STYLE_SAFETY_SECTION)
        layout.addWidget(warning)

        # Navegación de grupos
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Anterior")
        self.prev_btn.clicked.connect(self._previous_group)
        nav_layout.addWidget(self.prev_btn)
        self.group_label = QLabel()
        self.group_label.setAlignment(Qt.AlignCenter)
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
        summary_layout = QVLayout(summary_group)
        self.summary_label = QLabel()
        self.summary_label.setTextFormat(Qt.RichText)
        summary_layout.addWidget(self.summary_label)
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Opciones: backup checkbox desde BaseDialog
        self.add_backup_checkbox(layout, "Crear backup antes de eliminar (Recomendado)", True)

        # Botones
        buttons = self.make_ok_cancel_buttons(ok_text="🗑️ Eliminar Seleccionados", ok_enabled=False)
        self.ok_btn = buttons.button(QDialogButtonBox.Ok)
        layout.addWidget(buttons)

        # Cargar primer grupo
        self._load_group(0)

    def _load_group(self, index):
        """Carga y muestra un grupo específico con miniaturas"""
        if not 0 <= index < len(self.analysis['groups']):
            return
        self.current_group_index = index
        group = self.analysis['groups'][index]

        # Actualizar navegación
        total_groups = len(self.analysis['groups'])
        self.group_label.setText(f"Grupo {index + 1} de {total_groups}")
        self.prev_btn.setEnabled(index > 0)
        self.next_btn.setEnabled(index < total_groups - 1)

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
        info_label.setTextFormat(Qt.RichText)
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
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

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
            frame.setFrameStyle(QFrame.Box | QFrame.Raised)
            frame.setLineWidth(2)
            frame_layout = QVLayout(frame)
            frame_layout.setSpacing(5)
            frame_layout.setContentsMargins(5, 5, 5, 5)

            # Checkbox para selección
            checkbox = QCheckBox("Eliminar")
            checkbox.setChecked(file_path in previous_selection)
            checkbox.stateChanged.connect(lambda state, f=file_path: self._on_selection_changed(f, state))
            frame_layout.addWidget(checkbox, alignment=Qt.AlignCenter)

            # Miniatura
            thumbnail_label = self._create_thumbnail(file_path)
            if thumbnail_label:
                thumbnail_label.mousePressEvent = lambda event, f=file_path: self._open_file(f)
                thumbnail_label.setCursor(Qt.PointingHandCursor)
                thumbnail_label.setToolTip(f"Clic para abrir: {file_path.name}")
                frame_layout.addWidget(thumbnail_label, alignment=Qt.AlignCenter)
            else:
                # Si no se puede cargar la imagen, mostrar placeholder
                no_preview = QLabel("Sin vista previa")
                no_preview.setAlignment(Qt.AlignCenter)
                no_preview.setStyleSheet(ui_styles.STYLE_DIALOG_SMALL_GRAY)
                frame_layout.addWidget(no_preview)

            # Información del archivo
            from datetime import datetime
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            info_text = (
                f"<b>{file_path.name[:20]}{'...' if len(file_path.name) > 20 else ''}</b><br>"
                f"{format_size(file_path.stat().st_size)}<br>"
                f"{mtime.strftime('%Y-%m-%d %H:%M')}"
            )
            info_label = QLabel(info_text)
            info_label.setTextFormat(Qt.RichText)
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setWordWrap(True)
            info_label.setStyleSheet(ui_styles.STYLE_DIALOG_TINY_TEXT)
            frame_layout.addWidget(info_label)

            # Botón abrir (alternativa al clic en la miniatura)
            open_btn = QPushButton("🔍 Abrir")
            open_btn.setToolTip(f"Abrir {file_path}")
            open_btn.clicked.connect(lambda _, f=file_path: self._open_file(f))
            open_btn.setStyleSheet(ui_styles.STYLE_DIALOG_TINY_BUTTON)
            frame_layout.addWidget(open_btn)

            # Destacar el frame si está seleccionado
            if file_path in previous_selection:
                frame.setStyleSheet(ui_styles.STYLE_DIALOG_FRAME_SELECTED)
            else:
                frame.setStyleSheet(ui_styles.STYLE_DIALOG_FRAME_UNSELECTED)

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
        interpretation_label.setTextFormat(Qt.RichText)
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

    def _create_thumbnail(self, file_path: Path) -> QLabel:
        """Crea una miniatura para un archivo de imagen"""
        try:
            # Extensiones soportadas para preview
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.heic', '.heif'}
            if file_path.suffix.lower() not in image_extensions:
                return None

            # Intentar cargar con QPixmap (funciona para la mayoría de formatos)
            pixmap = QPixmap(str(file_path))
            
            # Si QPixmap falla (puede pasar con HEIC), intentar con pillow
            if pixmap.isNull():
                try:
                    from PIL import Image
                    from PyQt5.QtGui import QImage
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
                    # Pillow no está disponible
                    return None
                except Exception:
                    return None

            if pixmap.isNull():
                return None

            # Redimensionar manteniendo aspecto (150x150 máximo)
            thumbnail_size = 150
            scaled_pixmap = pixmap.scaled(
                thumbnail_size, thumbnail_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            label = QLabel()
            label.setPixmap(scaled_pixmap)
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(thumbnail_size, thumbnail_size)
            label.setStyleSheet(ui_styles.STYLE_DIALOG_LABEL_DISABLED)
            return label
        except Exception:
            return None

    def _update_frame_style(self, frame: QFrame, file_path: Path, state):
        """Actualiza el estilo visual del frame según el estado de selección"""
        if state == Qt.Checked:
            frame.setStyleSheet(ui_styles.STYLE_DIALOG_FRAME_SELECTED)
        else:
            frame.setStyleSheet(ui_styles.STYLE_DIALOG_FRAME_UNSELECTED)

    def _on_selection_changed(self, file_path, state):
        """Maneja cambios en la selección"""
        if self.current_group_index not in self.selections:
            self.selections[self.current_group_index] = []
        if state == Qt.Checked:
            if file_path not in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].append(file_path)
        else:
            if file_path in self.selections[self.current_group_index]:
                self.selections[self.current_group_index].remove(file_path)
        self._update_summary()

    def _previous_group(self):
        self._load_group(self.current_group_index - 1)

    def _next_group(self):
        self._load_group(self.current_group_index + 1)

    def _update_summary(self):
        """Actualiza el resumen de archivos seleccionados"""
        total_selected = sum(len(files) for files in self.selections.values())
        total_size = 0
        for files in self.selections.values():
            total_size += sum(f.stat().st_size for f in files)
        self.summary_label.setText(
            f"<b>Archivos seleccionados para eliminar:</b> {total_selected} "
            f"<br><b>Espacio a liberar:</b> {format_size(total_size)}"
        )
        self.ok_btn.setEnabled(total_selected > 0)

    def accept(self):
        # Crear grupos filtrados solo con archivos a eliminar
        groups_to_process = []
        for group_idx, files_to_delete in self.selections.items():
            if files_to_delete:
                original_group = self.analysis['groups'][group_idx]
                groups_to_process.append(DuplicateGroup(
                    hash_value=original_group.hash_value,
                    files=files_to_delete,
                    total_size=sum(f.stat().st_size for f in files_to_delete),
                    similarity_score=original_group.similarity_score
                ))
        self.accepted_plan = {
            'groups': groups_to_process,
            'keep_strategy': 'manual',
            'create_backup': self.backup_checkbox.isChecked()
        }
        super().accept()

    def _open_file(self, file_path: Path):
        """Abre un archivo con la aplicación predeterminada del sistema operativo"""
        if file_path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
        else:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Archivo no encontrado", f"No se encontró el archivo:\n{file_path}")
