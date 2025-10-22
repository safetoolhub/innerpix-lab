"""Clases/base utilities para diálogos."""
from PyQt5.QtWidgets import QDialog


class BaseDialog(QDialog):
    """Clase base simple para futuros diálogos (extensible)."""
    def __init__(self, parent=None):
        super().__init__(parent)
