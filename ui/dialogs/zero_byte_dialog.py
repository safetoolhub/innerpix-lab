from typing import List, Dict, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem,
    QCheckBox, QMessageBox, QWidget, QDialogButtonBox, QFrame
)
from PyQt6.QtCore import Qt
import qtawesome as qta

from ui.styles.design_system import DesignSystem
from utils.format_utils import format_file_count
from services.result_types import ZeroByteAnalysisResult
from .base_dialog import BaseDialog
from utils.icons import icon_manager

class ZeroByteDialog(BaseDialog):
    """
    Diálogo para gestionar archivos de 0 bytes.
    Muestra la lista de archivos encontrados y permite eliminarlos.
    """
    
    def __init__(self, analysis_result: ZeroByteAnalysisResult, parent=None):
        super().__init__(parent)
        self.analysis_result = analysis_result
        self.accepted_plan = {}  # Plan de ejecución para el worker
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Archivos Vacíos (0 bytes)")
        self.resize(800, 600)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(int(DesignSystem.SPACE_12))
        main_layout.setContentsMargins(0, 0, 0, int(DesignSystem.SPACE_20))
        
        # Header compacto
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='trash-alt',
            title='Archivos Vacíos Detectados',
            description='Estos archivos ocupan 0 bytes y no contienen información. Es seguro eliminarlos.',
            metrics=[
                {
                    'value': str(len(self.analysis_result.files)),
                    'label': 'Archivos',
                    'color': DesignSystem.COLOR_ERROR
                }
            ]
        )
        main_layout.addWidget(self.header_frame)
        
        # Contenedor con margen para el resto del contenido
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(int(DesignSystem.SPACE_16))
        content_layout.setContentsMargins(
            int(DesignSystem.SPACE_24),
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_24),
            0
        )
        main_layout.addWidget(content_container)
        
        # Lista de archivos
        self.files_list = QListWidget()
        self.files_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.files_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_8}px;
            }}
            QListWidget::item {{
                padding: {DesignSystem.SPACE_8}px;
                border-bottom: 1px solid {DesignSystem.COLOR_BORDER};
            }}
            QListWidget::item:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        
        # Poblar lista
        for file_path in self.analysis_result.files:
            item = QListWidgetItem(str(file_path))
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            item.setCheckState(Qt.CheckState.Checked)
            self.files_list.addItem(item)
            
        content_layout.addWidget(self.files_list)
        
        # Botones de selección
        selection_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Seleccionar todos")
        select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        select_all_btn.clicked.connect(self.select_all)
        select_all_btn.setStyleSheet(f"color: {DesignSystem.COLOR_PRIMARY}; border: none; font-weight: bold;")
        
        select_none_btn = QPushButton("Deseleccionar todos")
        select_none_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        select_none_btn.clicked.connect(self.select_none)
        select_none_btn.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; border: none;")
        
        selection_layout.addWidget(select_all_btn)
        selection_layout.addWidget(select_none_btn)
        selection_layout.addStretch()
        
        content_layout.addLayout(selection_layout)
        
        # Opciones de seguridad
        options_group = self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear copia de seguridad antes de eliminar",
            dry_run_label="Modo simulación (no eliminar realmente)"
        )
        content_layout.addWidget(options_group)
        
        # Botones de acción
        self.buttons = self.make_ok_cancel_buttons(
            ok_enabled=True,
            button_style='danger'
        )
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText(f"Eliminar {format_file_count(len(self.analysis_result.files))}")
        
        content_layout.addWidget(self.buttons)
        
        # Conectar cambios en selección para actualizar botón
        self.files_list.itemChanged.connect(self.update_button_text)
        
    def select_all(self):
        for i in range(self.files_list.count()):
            self.files_list.item(i).setCheckState(Qt.CheckState.Checked)
            
    def select_none(self):
        for i in range(self.files_list.count()):
            self.files_list.item(i).setCheckState(Qt.CheckState.Unchecked)
            
    def update_button_text(self):
        count = 0
        for i in range(self.files_list.count()):
            if self.files_list.item(i).checkState() == Qt.CheckState.Checked:
                count += 1
        
        self.ok_button.setText(f"Eliminar {format_file_count(count)}")
        self.ok_button.setEnabled(count > 0)
        
    def accept(self):
        files_to_delete = []
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                files_to_delete.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not files_to_delete:
            return
            
        self.accepted_plan = {
            'files_to_delete': files_to_delete,
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        
        super().accept()
