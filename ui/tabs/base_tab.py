# ---- Utilities for tabs (info labels, details, action buttons) ----
from PyQt5.QtWidgets import QLabel, QTextEdit, QPushButton
from PyQt5.QtCore import Qt
from ui import styles


def create_info_label(text: str, rich: bool = True, extra_style: str = None) -> QLabel:
    lbl = QLabel(text)
    if rich:
        lbl.setTextFormat(Qt.RichText)
    if extra_style:
        lbl.setStyleSheet(extra_style)
    else:
        # Default informative box style
        lbl.setStyleSheet("color: #495057; padding: 10px; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 4px;")
    lbl.setWordWrap(True)
    return lbl


def create_details_textedit(window, attr_name: str, placeholder: str = "Los detalles aparecerán después del análisis...", max_height: int = 200) -> QTextEdit:
    te = QTextEdit()
    te.setReadOnly(True)
    te.setMaximumHeight(max_height)
    te.setPlaceholderText(placeholder)
    # Attach to window attribute for compatibility with existing code
    setattr(window, attr_name, te)
    return te


def create_action_button(window, attr_name: str, text: str, callback_name: str, color: str = "#28a745") -> QPushButton:
    btn = QPushButton(text)
    btn.setEnabled(False)
    # connect to callback if it exists on window otherwise leave disabled
    cb = getattr(window, callback_name, None)
    if cb is not None:
        try:
            btn.clicked.connect(cb)
        except Exception:
            pass
    btn.setStyleSheet(styles.get_button_style(color))
    setattr(window, attr_name, btn)
    return btn

