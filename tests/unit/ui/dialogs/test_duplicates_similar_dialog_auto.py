"""
Tests específicos para la nueva funcionalidad de selección automática en DuplicatesSimilarDialog.
Cubre:
- Sobreescritura de selecciones manuales.
- Selección automática conservando el mayor (keep_largest).
- Selección automática conservando el más antiguo (keep_oldest).
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox

from services.duplicates_similar_service import DuplicatesSimilarAnalysis
from services.result_types import SimilarDuplicateGroup
from ui.dialogs.duplicates_similar_dialog import DuplicatesSimilarDialog

def create_mock_dialog(files_data):
    """
    Crea un diálogo con grupos simulados.
    files_data: Lista de grupos, donde cada grupo es una lista de tuplas (path, size, timestamp).
    """
    analysis = DuplicatesSimilarAnalysis()
    analysis.total_files = sum(len(g) for g in files_data)
    
    dialog = DuplicatesSimilarDialog(analysis)
    
    # Mockear repo para evitar dependencias reales
    dialog.repo = MagicMock()
    
    # Construir grupos simulados
    groups = []
    for group_data in files_data:
        files = [Path(f[0]) for f in group_data]
        # Mockear sizes y dates
        for path_str, size, ts in group_data:
            path = Path(path_str)
            # Mock para _get_file_size
            # Usamos side_effect en una función mockeada globalmente o mockeamos el método del diálogo
            # Aquí es más fácil mockear métodos privados del diálogo si son stateless, o el repo.
            # El diálogo usa _get_file_size que llama a repo.get_file_metadata
            
            meta = MagicMock()
            meta.fs_size = size
            dialog.repo.get_file_metadata.return_value = meta # Esto retornaría lo mismo siempre si no usamos side_effect
            
            # Setup side_effects is tricky for multiple files.
            # Better to mock _get_file_size and _get_file_best_date methods on the dialog instance directly.
            pass
            
        group = SimilarDuplicateGroup(
            hash_value="test_hash",
            files=files,
            file_sizes=[f[1] for f in group_data],
            similarity_score=90.0
        )
        groups.append(group)
        
    dialog.all_groups = groups
    dialog.filtered_groups = groups # Simular que no hay filtros
    dialog.current_sensitivity = 85
    
    # Mockear métodos helpers para facilitar setup de datos
    dialog._get_file_size = MagicMock()
    dialog._get_file_size.side_effect = lambda p: next((f[1] for g in files_data for f in g if f[0] == str(p)), 0)
    
    dialog._get_file_best_date = MagicMock()
    dialog._get_file_best_date.side_effect = lambda p: next((f[2] for g in files_data for f in g if f[0] == str(p)), 0)
    
    return dialog

@pytest.mark.ui
class TestDuplicatesSimilarDialogAutoSelection:
    
    def test_manual_selection_overwritten_by_auto(self, qtbot):
        """Test que la selección manual es eliminada al aplicar auto-selección."""
        # Setup: 1 grupo con 3 archivos
        # Archivo 1: 10MB, Date 100
        # Archivo 2: 20MB, Date 200
        # Archivo 3: 5MB,  Date 300
        data = [[
            ("/tmp/f1.jpg", 10*1024*1024, 100),
            ("/tmp/f2.jpg", 20*1024*1024, 200),
            ("/tmp/f3.jpg", 5*1024*1024, 300)
        ]]
        dialog = create_mock_dialog(data)
        
        # 1. Selección manual: Seleccionar f2 (el más grande)
        # Indicar que queremos eliminar f2
        dialog.selections[0] = [Path("/tmp/f2.jpg")]
        
        # Verify manual selection exists
        assert len(dialog.selections[0]) == 1
        assert dialog.selections[0][0] == Path("/tmp/f2.jpg")
        
        # 2. Ejecutar Auto: Conservar Mayor (debería eliminar f1 y f3, y mantener f2)
        # Mock message box to accept
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes):
             dialog._on_auto_select_click('keep_largest')
        
        # 3. Verify overwritten
        # Keep largest (20MB) -> Delete f1 (10MB) and f3 (5MB)
        assert 0 in dialog.selections
        selection = dialog.selections[0]
        assert len(selection) == 2
        assert Path("/tmp/f1.jpg") in selection
        assert Path("/tmp/f3.jpg") in selection
        assert Path("/tmp/f2.jpg") not in selection # f2 era seleccionado manualmente para borrar, ahora se conserva
        
    def test_auto_select_keep_largest(self, qtbot):
        """Test lógica de conservar el más grande."""
        # Group 1: f1(10), f2(20). Keep f2. Delete f1.
        # Group 2: f3(50), f4(30). Keep f3. Delete f4.
        data = [
            [("/tmp/f1.jpg", 10, 100), ("/tmp/f2.jpg", 20, 100)],
            [("/tmp/f3.jpg", 50, 100), ("/tmp/f4.jpg", 30, 100)]
        ]
        dialog = create_mock_dialog(data)
        
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes):
             dialog._on_auto_select_click('keep_largest')
             
        # Group 1
        assert Path("/tmp/f1.jpg") in dialog.selections[0]
        assert Path("/tmp/f2.jpg") not in dialog.selections[0]
        
        # Group 2
        assert Path("/tmp/f4.jpg") in dialog.selections[1]
        assert Path("/tmp/f3.jpg") not in dialog.selections[1]

    def test_auto_select_keep_oldest(self, qtbot):
        """Test lógica de conservar el más antiguo (menor fecha/best date)."""
        # Group 1: f1(Date 1000), f2(Date 2000). Keep f1(Oldest). Delete f2.
        # Group 2: f3(Date 5000), f4(Date 4000). Keep f4(Oldest). Delete f3.
        data = [
            [("/tmp/f1.jpg", 10, 1000), ("/tmp/f2.jpg", 10, 2000)],
            [("/tmp/f3.jpg", 10, 5000), ("/tmp/f4.jpg", 10, 4000)]
        ]
        dialog = create_mock_dialog(data)
        
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes):
             # keep_oldest implies keeping the one with "best date" being the oldest timestamp
             dialog._on_auto_select_click('keep_oldest')
        
        # Group 1: Keep 1000 (f1), Delete 2000 (f2)
        assert Path("/tmp/f2.jpg") in dialog.selections[0]
        assert Path("/tmp/f1.jpg") not in dialog.selections[0]
        
        # Group 2: Keep 4000 (f4), Delete 5000 (f3)
        assert Path("/tmp/f3.jpg") in dialog.selections[1]
        assert Path("/tmp/f4.jpg") not in dialog.selections[1]

