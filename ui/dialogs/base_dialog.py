"""Clases/base utilities para diálogos."""
from PyQt5.QtWidgets import QDialog, QCheckBox


class BaseDialog(QDialog):
    """Clase base para diálogos con utilidades comunes.

    Actualmente expone helpers para añadir una opción de backup y
    consultar su estado. Los diálogos pueden llamar a
    `self.add_backup_checkbox(layout, label, checked)` durante su UI
    y luego leer `self.backup_checkbox.isChecked()` en `accept()`.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.backup_checkbox = None

    def add_backup_checkbox(self, layout=None, label: str = "Crear backup", checked: bool = True):
        """Crea y retorna un QCheckBox para la opción de backup.

        Si se pasa un layout, el checkbox se añadirá al layout.
        Guarda la referencia en `self.backup_checkbox`.
        """
        cb = QCheckBox(label)
        cb.setChecked(checked)
        self.backup_checkbox = cb
        if layout is not None:
            try:
                layout.addWidget(cb)
            except Exception:
                # layout podría ser un QGroupBox o algo distinto; intentar addWidget falla
                pass
        return cb

    def is_backup_enabled(self) -> bool:
        """Devuelve True si el checkbox de backup existe y está marcado."""
        return bool(self.backup_checkbox and self.backup_checkbox.isChecked())
