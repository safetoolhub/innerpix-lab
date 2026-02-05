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
    """
    Especificamente prueba las estrategias automáticas (Mayor Tamaño y Mejor Fecha)
    con mocks detallados para asegurar que el comportamiento es predecible.
    """
    
    def test_manual_selection_overwritten_by_auto(self, qtbot):
        """
        Ejemplo: El usuario marca un archivo para borrar manualmente, pero luego
        decide usar el modo automático. La selección manual anterior debe desaparecer.
        """
        # Data: 1 grupo
        # f1: 10MB (Más pequeño)
        # f2: 20MB (Más grande)
        data = [[
            ("/tmp/f1.jpg", 10*1024*1024, 1000),
            ("/tmp/f2.jpg", 20*1024*1024, 2000)
        ]]
        dialog = create_mock_dialog(data)
        
        # Simular selección manual: el usuario marca f2 para borrar (f2 es el grande)
        dialog.selections[0] = [Path("/tmp/f2.jpg")]
        
        # Aplicar "Conservar Mayor" (debería borrar f1 y CONSERVAR f2)
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes):
             dialog._on_auto_select_click('keep_largest')
        
        # Resultado esperado: f1 seleccionado para borrar, f2 NO seleccionado (se conserva)
        assert Path("/tmp/f1.jpg") in dialog.selections[0]
        assert Path("/tmp/f2.jpg") not in dialog.selections[0]
        
    def test_auto_select_keep_largest_concrete_example(self, qtbot):
        """
        Caso concreto:
        Archivo A: 1.5MB (Versión optimizada)
        Archivo B: 15MB (Original alta calidad)
        -> Seleccionando 'Conservar Mayor' debe marcar Archivo A para borrar.
        """
        data = [[
            ("/tmp/optimized.jpg", 1.5*1024*1024, 1000),
            ("/tmp/original.jpg", 15*1024*1024, 1000)
        ]]
        dialog = create_mock_dialog(data)
        
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes):
             dialog._on_auto_select_click('keep_largest')
             
        assert Path("/tmp/optimized.jpg") in dialog.selections[0]
        assert Path("/tmp/original.jpg") not in dialog.selections[0]

    def test_auto_select_keep_oldest_concrete_example(self, qtbot):
        """
        Caso concreto (Mejor Fecha / Más Antiguo):
        Archivo A: Fecha 2015 (Original)
        Archivo B: Fecha 2024 (Copia editada recibida por WhatsApp recientemente)
        -> Seleccionando 'Mejor Fecha' debe marcar Archivo B para borrar (conservar el de 2015).
        """
        # Timestamps: 2015 < 2024
        ts_2015 = 1420070400 # 2015-01-01
        ts_2024 = 1704067200 # 2024-01-01
        
        data = [[
            ("/tmp/old_photo.jpg", 5*1024*1024, ts_2015),
            ("/tmp/whatsapp_copy.jpg", 1*1024*1024, ts_2024)
        ]]
        dialog = create_mock_dialog(data)
        
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes):
             dialog._on_auto_select_click('keep_oldest')
        
        assert Path("/tmp/whatsapp_copy.jpg") in dialog.selections[0]
        assert Path("/tmp/old_photo.jpg") not in dialog.selections[0]

    def test_auto_select_multi_group_consistency(self, qtbot):
        """Prueba que el modo automático se aplica consistentemente a varios grupos a la vez."""
        data = [
            # Grupo 1: f1(small), f2(big)
            [("/tmp/g1_small.jpg", 10, 100), ("/tmp/g1_big.jpg", 20, 100)],
            # Grupo 2: f3(big), f4(small)
            [("/tmp/g2_big.jpg", 50, 100), ("/tmp/g2_small.jpg", 30, 100)]
        ]
        dialog = create_mock_dialog(data)
        
        with patch.object(QMessageBox, 'exec', return_value=QMessageBox.StandardButton.Yes):
             dialog._on_auto_select_click('keep_largest')
             
        # G1: Borrar small
        assert Path("/tmp/g1_small.jpg") in dialog.selections[0]
        # G2: Borrar small
        assert Path("/tmp/g2_small.jpg") in dialog.selections[1]


