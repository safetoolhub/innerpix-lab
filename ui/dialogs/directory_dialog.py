from PyQt5.QtWidgets import (
    QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QGroupBox, QDialogButtonBox, QCheckBox
)

from ui.ui_helpers import format_size
from ui import styles as ui_styles
from .base_dialog import BaseDialog


class DirectoryUnificationDialog(BaseDialog):
    """Diálogo para unificación de directorios"""

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.accepted_plan = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Unificación de Directorios")
        self.setModal(True)
        self.resize(800, 500)
        layout = QVBoxLayout(self)

        # Información
        info = QLabel("Esta operación moverá todos los archivos al directorio raíz "
                      "y eliminará los subdirectorios vacíos.")
        info.setWordWrap(True)
        info.setStyleSheet(ui_styles.STYLE_WARNING_LIGHT)
        layout.addWidget(info)

        # Lista de subdirectorios
        if self.analysis.get('subdirectories'):
            layout.addWidget(QLabel("Subdirectorios a unificar:"))
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Subdirectorio", "Archivos", "Tamaño"])

            subdirs = list(self.analysis['subdirectories'].items())
            table.setRowCount(len(subdirs))
            for row, (name, info) in enumerate(subdirs):
                table.setItem(row, 0, QTableWidgetItem(name))
                table.setItem(row, 1, QTableWidgetItem(str(info['file_count'])))
                size_formatted = format_size(info['total_size'])
                table.setItem(row, 2, QTableWidgetItem(size_formatted))

            table.setMaximumHeight(300)
            layout.addWidget(table)

        # Opciones
        options_group = QGroupBox("Opciones")
        options_layout = QVBoxLayout(options_group)

        # Backup checkbox desde BaseDialog
        self.add_backup_checkbox(options_layout, "Crear backup antes de eliminar (Recomendado)", True)


        self.cleanup_checkbox = QCheckBox("Eliminar directorios vacíos")
        self.cleanup_checkbox.setChecked(True)
        options_layout.addWidget(self.cleanup_checkbox)
        layout.addWidget(options_group)

        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        if self.analysis.get('total_files_to_move', 0) > 0:
            size = self.analysis.get('total_size_to_move', 0)
            size_formatted = format_size(size)
            buttons.button(QDialogButtonBox.Ok).setText(
                f"Proceder ({self.analysis['total_files_to_move']}, {size_formatted})"
            )
        else:
            buttons.button(QDialogButtonBox.Ok).setEnabled(False)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        self.accepted_plan = {
            'move_plan': self.analysis['move_plan'],
            'create_backup': self.backup_checkbox.isChecked(),
            'cleanup_empty_dirs': self.cleanup_checkbox.isChecked()
        }
        super().accept()
