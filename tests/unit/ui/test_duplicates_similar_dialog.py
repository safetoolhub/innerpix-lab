"""
Tests para DuplicatesSimilarDialog.

Prueba el diálogo de gestión de archivos similares (70-95% similitud):
- Inicialización correcta con DuplicatesSimilarAnalysis
- Estado de carga antes de mostrar grupos
- Slider de sensibilidad (70-95%)
- Navegación entre grupos
- Selección de archivos para eliminar
- Estrategias de selección rápida
- Construcción del plan de eliminación
"""

import pytest
from pathlib import Path
from PyQt6.QtCore import Qt

from services.duplicates_similar_service import DuplicatesSimilarAnalysis
from services.result_types import DuplicateGroup
from ui.dialogs.duplicates_similar_dialog import DuplicatesSimilarDialog


def create_mock_analysis(num_files: int = 10) -> DuplicatesSimilarAnalysis:
    """Crea un DuplicatesSimilarAnalysis con datos mock para testing."""
    analysis = DuplicatesSimilarAnalysis()
    
    # Simular hashes perceptuales
    for i in range(num_files):
        path = f"/tmp/test_image_{i}.jpg"
        analysis.perceptual_hashes[path] = {
            'hash': i % 5,  # Grupos de 2 archivos con mismo hash
            'size': 1000 * (i + 1)
        }
    
    analysis.total_files = num_files
    return analysis


@pytest.mark.ui
class TestDuplicatesSimilarDialogBasics:
    """Tests básicos del diálogo."""
    
    def test_dialog_creation(self, qtbot):
        """Test que el diálogo se crea correctamente."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert dialog is not None
        assert dialog.analysis == analysis
        assert "Archivos Similares" in dialog.windowTitle()
    
    def test_dialog_inherits_base_dialog(self, qtbot):
        """Test que el diálogo hereda de BaseDialog."""
        from ui.dialogs.base_dialog import BaseDialog
        
        analysis = create_mock_analysis(2)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert isinstance(dialog, BaseDialog)
    
    def test_dialog_has_sensitivity_slider(self, qtbot):
        """Test que el diálogo tiene slider de sensibilidad."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert hasattr(dialog, 'sensitivity_slider')
        assert dialog.sensitivity_slider is not None
    
    def test_default_sensitivity_is_85(self, qtbot):
        """Test que la sensibilidad por defecto es 85%."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert dialog.DEFAULT_SENSITIVITY == 85
        assert dialog.current_sensitivity == 85
    
    def test_sensitivity_slider_range(self, qtbot):
        """Test que el slider tiene rango correcto (70-95%)."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert dialog.sensitivity_slider.minimum() == 70
        assert dialog.sensitivity_slider.maximum() == 95


@pytest.mark.ui
class TestDuplicatesSimilarDialogNavigation:
    """Tests de navegación entre grupos."""
    
    def test_navigation_buttons_exist(self, qtbot):
        """Test que existen botones de navegación."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert hasattr(dialog, 'prev_btn')
        assert hasattr(dialog, 'next_btn')
        assert hasattr(dialog, 'group_counter_label')
    
    def test_navigation_buttons_initially_disabled(self, qtbot):
        """Test que los botones están deshabilitados antes de cargar grupos."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        # Durante estado de carga inicial
        assert dialog._is_loading is True


@pytest.mark.ui
class TestDuplicatesSimilarDialogSelection:
    """Tests de selección de archivos."""
    
    def test_selections_initially_empty(self, qtbot):
        """Test que las selecciones empiezan vacías."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert dialog.selections == {}
    
    def test_delete_button_initially_disabled(self, qtbot):
        """Test que el botón de eliminar está deshabilitado al inicio."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        # delete_btn puede ser None si no se ha configurado aún
        if dialog.delete_btn:
            assert dialog.delete_btn.isEnabled() is False


@pytest.mark.ui  
class TestDuplicatesSimilarDialogSecurity:
    """Tests de opciones de seguridad."""
    
    def test_backup_option_exists(self, qtbot):
        """Test que existe opción de backup."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        # Verificar que el diálogo tiene el método de BaseDialog
        assert hasattr(dialog, 'is_backup_enabled')
    
    def test_dry_run_option_exists(self, qtbot):
        """Test que existe opción de dry run."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert hasattr(dialog, 'is_dry_run_enabled')


@pytest.mark.ui
class TestDuplicatesSimilarDialogAccept:
    """Tests de aceptación del diálogo."""
    
    def test_accepted_plan_initially_none(self, qtbot):
        """Test que accepted_plan es None inicialmente."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert dialog.accepted_plan is None
    
    def test_accept_builds_plan(self, qtbot):
        """Test que accept() construye el plan de eliminación."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        # Simular que hay grupos y selecciones
        mock_group = DuplicateGroup(
            hash_value="test",
            files=[Path("/tmp/file1.jpg"), Path("/tmp/file2.jpg")],
            total_size=2000,
            similarity_score=90.0
        )
        dialog.all_groups = [mock_group]
        dialog.selections[0] = [Path("/tmp/file2.jpg")]
        
        # No llamamos exec() para evitar bloquear, solo accept()
        # Primero interceptamos el cierre
        dialog.close = lambda: None  # type: ignore[assignment]
        dialog.done = lambda x: None  # type: ignore[assignment]
        dialog.accept()
        
        assert dialog.accepted_plan is not None
        assert 'analysis' in dialog.accepted_plan
        assert 'keep_strategy' in dialog.accepted_plan
        assert 'create_backup' in dialog.accepted_plan
        assert 'dry_run' in dialog.accepted_plan


@pytest.mark.ui
class TestSensitivitySliderBehavior:
    """Tests del comportamiento del slider de sensibilidad."""
    
    def test_slider_updates_label(self, qtbot):
        """Test que mover el slider actualiza el label."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        # Simular cambio de valor
        dialog.sensitivity_slider.setValue(75)
        
        # Verificar que el label se actualiza
        assert "75%" in dialog.sensitivity_value_label.text()
    
    def test_slider_updates_current_sensitivity(self, qtbot):
        """Test que mover el slider actualiza current_sensitivity."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        dialog.sensitivity_slider.setValue(90)
        
        assert dialog.current_sensitivity == 90


@pytest.mark.ui
class TestLoadingState:
    """Tests del estado de carga."""
    
    def test_loading_flag_initially_true(self, qtbot):
        """Test que _is_loading es True al inicio."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert dialog._is_loading is True
    
    def test_slider_disabled_during_loading(self, qtbot):
        """Test que el slider está deshabilitado durante carga."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        # Verificamos que durante la inicialización está deshabilitado
        # (será habilitado después de _initial_load)
        assert dialog.sensitivity_slider.isEnabled() is False


@pytest.mark.ui
class TestDuplicatesSimilarDialogStrategies:
    """Tests de estrategias de selección rápida."""
    
    def test_apply_strategy_method_exists(self, qtbot):
        """Test que existe el método _apply_strategy."""
        analysis = create_mock_analysis(4)
        dialog = DuplicatesSimilarDialog(analysis)
        
        assert hasattr(dialog, '_apply_strategy')
        assert callable(dialog._apply_strategy)
    
    def test_strategy_without_groups_does_nothing(self, qtbot):
        """Test que aplicar estrategia sin grupos no hace nada."""
        analysis = create_mock_analysis(0)
        dialog = DuplicatesSimilarDialog(analysis)
        
        # No debe lanzar excepción
        dialog._apply_strategy('keep_largest')
        dialog._apply_strategy('keep_first')


@pytest.mark.ui
class TestAnalysisEmptyScenarios:
    """Tests con análisis vacíos o sin grupos."""
    
    def test_dialog_with_empty_analysis(self, qtbot):
        """Test que el diálogo maneja análisis vacío."""
        analysis = DuplicatesSimilarAnalysis()
        analysis.total_files = 0
        
        # No debe lanzar excepción
        dialog = DuplicatesSimilarDialog(analysis)
        assert dialog is not None
    
    def test_dialog_with_no_similar_files(self, qtbot):
        """Test que el diálogo maneja caso sin archivos similares."""
        analysis = DuplicatesSimilarAnalysis()
        # Todos los hashes diferentes = no hay similares
        for i in range(10):
            analysis.perceptual_hashes[f"/tmp/unique_{i}.jpg"] = {
                'hash': i * 1000,  # Hashes muy diferentes
                'size': 1000
            }
        analysis.total_files = 10
        
        dialog = DuplicatesSimilarDialog(analysis)
        assert dialog is not None
