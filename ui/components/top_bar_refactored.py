"""
TopBar - Barra superior compacta con Smart Stats integrados.

Componente profesional optimizado para maximizar espacio vertical.
Diseño modular que integra:
- Control Bar (60px): Título + directorio + badge integrado + acciones
- Smart Stats Bar (colapsable): Estadísticas organizadas en 3 columnas
- Progress Overlay: Barra de progreso superpuesta durante análisis
"""
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QLineEdit, 
    QFrame, QMenu, QToolButton, QStyle, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve

from config import Config
from ui import styles
from ui.components.smart_stats_bar import SmartStatsBar
from ui.components.progress_overlay import ProgressOverlay
from utils.settings_manager import settings_manager
from utils.format_utils import format_count_short, format_size_short, format_count_full, format_size_full
from utils.icons import icon_manager


class TopBar(QWidget):