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
        ok_enabled = self.analysis.get('total_files_to_move', 0) > 0
        if ok_enabled:
            size = self.analysis.get('total_size_to_move', 0)
            size_formatted = format_size(size)
            ok_text = f"Proceder ({self.analysis['total_files_to_move']}, {size_formatted})"
        else:
            ok_text = None
        buttons = self.make_ok_cancel_buttons(ok_text=ok_text, ok_enabled=ok_enabled)
        self.buttons = buttons
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        layout.addWidget(buttons)

    def accept(self):
        self.accepted_plan = self.build_accepted_plan({
            'move_plan': self.analysis['move_plan'],
            'cleanup_empty_dirs': self.cleanup_checkbox.isChecked()
        })
        super().accept()
