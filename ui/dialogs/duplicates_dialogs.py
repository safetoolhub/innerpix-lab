from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QGroupBox, QButtonGroup, QRadioButton,
    QTableWidget, QTableWidgetItem, QCheckBox, QDialogButtonBox, QPushButton,
    QHBoxLayout, QVBoxLayout as QVLayout
)
from PyQt5.QtCore import Qt
from services.duplicate_detector import DuplicateGroup
from ui.helpers import format_size
from ui import styles as ui_styles
from .base_dialog import BaseDialog
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl


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
        """Carga y muestra un grupo específico"""
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

        # Info del grupo
        info_label = QLabel(
            f"<b>Similitud:</b> {group.similarity_score:.1f}% | "
            f"<b>Archivos:</b> {group.file_count} | "
            f"<b>Tamaño total:</b> {format_size(group.total_size)}"
        )
        info_label.setTextFormat(Qt.RichText)
        info_label.setStyleSheet(ui_styles.STYLE_PANEL_LABEL)
        self.group_layout.addWidget(info_label)

        # Tabla de archivos
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Eliminar", "Archivo", "Tamaño", "Fecha Modificación", "Abrir archivo"])
        table.setRowCount(len(group.files))

        previous_selection = self.selections.get(index, [])

        for row, file_path in enumerate(group.files):
            checkbox = QCheckBox()
            checkbox.setChecked(file_path in previous_selection)
            checkbox.stateChanged.connect(lambda state, f=file_path: self._on_selection_changed(f, state))
            table.setCellWidget(row, 0, checkbox)

            table.setItem(row, 1, QTableWidgetItem(file_path.name))
            table.setItem(row, 2, QTableWidgetItem(format_size(file_path.stat().st_size)))

            from datetime import datetime
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            table.setItem(row, 3, QTableWidgetItem(mtime.strftime("%Y-%m-%d %H:%M")))

            open_btn = QPushButton("Abrir")
            open_btn.setToolTip(f"Abrir {file_path}")
            open_btn.clicked.connect(lambda _, f=file_path: self._open_file(f))
            table.setCellWidget(row, 4, open_btn)

        table.resizeColumnsToContents()
        self.group_layout.addWidget(table)

        self._update_summary()

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
