from pathlib import Path
from PyQt5.QtWidgets import (
    QVBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialogButtonBox, QLabel
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from ui.ui_helpers import format_size
from ui import styles as ui_styles
from .base_dialog import BaseDialog


class RenamingPreviewDialog(BaseDialog):
    """Diálogo de preview para renombrado"""

    def __init__(self, analysis_results, parent=None):
        super().__init__(parent)
        self.analysis_results = analysis_results
        self.accepted_plan = None
        self.init_ui()

    def update_statistics(self, results):
        """Actualiza las estadísticas después del renombrado"""
        if hasattr(self, 'stats_table'):
            self.stats_table.item(0, 1).setText(str(results['files_renamed']))
            if 'conflicts_resolved' in results:
                self.stats_table.item(1, 1).setText(str(results['conflicts_resolved']))
            if len(results['errors']) > 0:
                self.stats_table.item(2, 1).setText(str(len(results['errors'])))
            self.stats_table.viewport().update()

    def init_ui(self):
        self.setWindowTitle("Preview de Renombrado")
        self.setModal(True)
        self.resize(900, 600)
        layout = QVBoxLayout(self)

        # Estadísticas
        stats_group = QGroupBox("Estadísticas")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setRowCount(3)
        self.stats_table.setHorizontalHeaderLabels(["Concepto", "Cantidad"])
        header = self.stats_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # Filas de estadísticas
        stats_rows = [
            ("Archivos renombrados", "0"),
            ("Conflictos resueltos", "0"),
            ("Errores", "0")
        ]

        for row, (label, value) in enumerate(stats_rows):
            self.stats_table.setItem(row, 0, QTableWidgetItem(label))
            self.stats_table.setItem(row, 1, QTableWidgetItem(value))

        stats_layout.addWidget(self.stats_table)
        layout.addWidget(stats_group)

        # Tabla de cambios propuestos
        if self.analysis_results.get('renaming_plan'):
            layout.addWidget(QLabel("Cambios propuestos (primeros 50):"))
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Original", "Nuevo", "Fecha", "Conflicto"])
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

            plan = self.analysis_results['renaming_plan'][:50]
            table.setRowCount(len(plan))
            for row, item in enumerate(plan):
                table.setItem(row, 0, QTableWidgetItem(item['original_path'].name))
                table.setItem(row, 1, QTableWidgetItem(item['new_name']))
                table.setItem(row, 2, QTableWidgetItem(item['date'].strftime('%Y-%m-%d %H:%M:%S')))
                conflict_item = QTableWidgetItem("Sí" if item['has_conflict'] else "No")
                if item['has_conflict']:
                    conflict_item.setBackground(QColor(255, 255, 0))
                table.setItem(row, 3, conflict_item)

            table.setMaximumHeight(400)
            layout.addWidget(table)

            if len(self.analysis_results['renaming_plan']) > 50:
                more_label = QLabel(f"... y {len(self.analysis_results['renaming_plan']) - 50} más")
                more_label.setStyleSheet(ui_styles.STYLE_ITALIC_GRAY)
                layout.addWidget(more_label)

        # Opciones: checkbox de backup (desde BaseDialog)
        self.add_backup_checkbox(layout, "Crear backup antes de eliminar (Recomendado)", True)

        # Botones
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        if self.analysis_results.get('need_renaming', 0) > 0:
            buttons.button(QDialogButtonBox.Ok).setText(
                f"Proceder ({self.analysis_results['need_renaming']})"
            )
        else:
            buttons.button(QDialogButtonBox.Ok).setEnabled(False)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        self.accepted_plan = {
            'plan': self.analysis_results['renaming_plan'],
            'create_backup': self.backup_checkbox.isChecked()
        }
        super().accept()
