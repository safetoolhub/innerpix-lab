from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QVBoxLayout as QVLayout, QRadioButton,
    QButtonGroup, QTableWidget, QTableWidgetItem, QCheckBox, QDialogButtonBox, QLabel
)
from config import Config
from utils.format_utils import format_size
from ui import styles as ui_styles
from .base_dialog import BaseDialog


class HEICDuplicateRemovalDialog(BaseDialog):
    """Diálogo para eliminación de duplicados HEIC"""

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis
        self.selected_format = 'jpg'
        self.accepted_plan = None
        self.init_ui()

    def _update_button_text(self):
        """Actualiza el texto del botón según el formato seleccionado"""
        if self.analysis.get('total_duplicates', 0) > 0:
            if self.selected_format == 'jpg':
                savings = self.analysis.get('potential_savings_keep_jpg', 0)
            else:
                savings = self.analysis.get('potential_savings_keep_heic', 0)

            space_formatted = format_size(savings)
            self.ok_button.setText(
                f"Proceder ({self.analysis['total_duplicates']}, {space_formatted})"
            )

    def init_ui(self):
        self.setWindowTitle("Duplicados HEIC/JPG")
        self.setModal(True)
        self.resize(900, 600)
        layout = QVBoxLayout(self)

        # Formato a mantener
        format_group = QGroupBox("Formato a Mantener")
        format_layout = QVLayout(format_group)
        self.format_buttons = QButtonGroup()

        r1 = QRadioButton("📸 Mantener JPG (Recomendado)")
        r1.setChecked(True)
        self.format_buttons.addButton(r1, 0)
        format_layout.addWidget(r1)

        r2 = QRadioButton("🖼️ Mantener HEIC")
        self.format_buttons.addButton(r2, 1)
        format_layout.addWidget(r2)

        self.format_buttons.buttonClicked.connect(self._on_format_changed)
        layout.addWidget(format_group)

        # Tabla de duplicados
        if self.analysis.get('duplicate_pairs'):
            layout.addWidget(QLabel("Pares detectados (primeros 20):"))
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Nombre", "HEIC (KB)", "JPG (KB)", "Ratio"])

            pairs = self.analysis['duplicate_pairs'][:20]
            table.setRowCount(len(pairs))
            for row, pair in enumerate(pairs):
                table.setItem(row, 0, QTableWidgetItem(pair.base_name))
                table.setItem(row, 1, QTableWidgetItem(f"{pair.heic_size / 1024:.1f}"))
                table.setItem(row, 2, QTableWidgetItem(f"{pair.jpg_size / 1024:.1f}"))
                table.setItem(row, 3, QTableWidgetItem(f"{pair.compression_ratio:.2f}x"))

            table.setMaximumHeight(Config.TABLE_MAX_HEIGHT)
            layout.addWidget(table)

        # Opciones: backup checkbox desde BaseDialog
        self.add_backup_checkbox(layout, "Crear backup antes de eliminar (Recomendado)", True)

        # Botones
        ok_enabled = self.analysis.get('total_duplicates', 0) > 0
        self.buttons = self.make_ok_cancel_buttons(ok_enabled=ok_enabled)
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_enabled:
            self._update_button_text()
        layout.addWidget(self.buttons)

    def _on_format_changed(self, button):
        self.selected_format = 'jpg' if self.format_buttons.id(button) == 0 else 'heic'
        self._update_button_text()

    def accept(self):
        self.accepted_plan = self.build_accepted_plan({
            'duplicate_pairs': self.analysis['duplicate_pairs'],
            'keep_format': self.selected_format,
        })
        super().accept()
