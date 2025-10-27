"""Clases/base utilities para diálogos."""
from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QDialog,
    QCheckBox,
    QDialogButtonBox,
    QPushButton,
    QTableWidget,
)


class BaseDialog(QDialog):
    """Clase base para diálogos con utilidades comunes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.backup_checkbox = None
        self._ok_button_ref = None

    def add_backup_checkbox(self, layout=None, label: str = "Crear backup", checked: bool = True):
        """Crea y retorna un QCheckBox para la opción de backup.

        Si se pasa un layout, el checkbox se añadirá al layout.
        Guarda la referencia en `self.backup_checkbox`.
        """
        cb = QCheckBox(label)
        cb.setChecked(checked)
        self.backup_checkbox = cb
        if layout is not None:
            layout.addWidget(cb)
        return cb

    def is_backup_enabled(self) -> bool:
        """Devuelve True si el checkbox de backup existe y está marcado."""
        return bool(self.backup_checkbox and self.backup_checkbox.isChecked())

    def build_accepted_plan(self, extra: Optional[Dict] = None) -> Dict:
        """Construye un dict para accepted_plan incluyendo el flag de backup.

        Usage: return self.build_accepted_plan({'groups': ..., 'keep_strategy': 'oldest'})
        """
        result = {} if extra is None else dict(extra)
        # Always set create_backup based on the current checkbox state so the
        # dialog selection takes precedence over any provided extra value.
        result['create_backup'] = self.is_backup_enabled()
        return result

    def make_ok_cancel_buttons(self, ok_text: Optional[str] = None, ok_style: Optional[str] = None,
                               ok_enabled: bool = True) -> QDialogButtonBox:
        """Crea y devuelve un QDialogButtonBox con Ok/Cancel enlazados a accept/reject.

        Does not mutate dialog state except wiring signals. The caller can further
        customize the returned button box or button texts/styles.
        """
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = box.button(QDialogButtonBox.Ok)
        cancel_btn = box.button(QDialogButtonBox.Cancel)
        if ok_text is not None:
            ok_btn.setText(ok_text)
        if ok_style is not None:
            ok_btn.setStyleSheet(ok_style)
        ok_btn.setEnabled(ok_enabled)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        # remember ok button for convenience
        self.register_ok_button(ok_btn)
        return box

    def register_ok_button(self, button: Optional[QPushButton]):
        """Register the dialog's primary OK button so helpers can enable/disable it.

        Pass None to clear the registration.
        """
        self._ok_button_ref = button

    def set_ok_enabled(self, enabled: bool):
        """Enable/disable previously registered OK button (no-op if none)."""
        if self._ok_button_ref is not None:
            self._ok_button_ref.setEnabled(enabled)

    def make_table(self, headers: List[str], max_height: Optional[int] = None) -> QTableWidget:
        """Create a QTableWidget with given headers and optional maximum height.

        Caller is responsible for populating rows and adding it to a layout.
        """
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        if max_height is not None:
            table.setMaximumHeight(max_height)
        return table

    def add_dry_run_checkbox(self, layout, label: str = "Modo simulación (no eliminar archivos)", checked: bool = False):
        """Convenience: add a dry-run checkbox to dialog and return it."""
        cb = QCheckBox(label)
        cb.setChecked(checked)
        layout.addWidget(cb)
        # store if there's a need to access later; name-based access is simplest
        self.dry_run_checkbox = cb
        return cb  
