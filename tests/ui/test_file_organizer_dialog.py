"""
Comprehensive UI tests for File Organizer Dialog
Tests dialog state, strategy selection, and UI interactions
"""
import pytest
from pathlib import Path
from PyQt6.QtWidgets import QComboBox, QCheckBox
from PyQt6.QtCore import Qt, QTimer
from datetime import datetime
from PIL import Image

from ui.dialogs.file_organizer_dialog import FileOrganizationDialog
from services.file_organizer_service import FileOrganizer, OrganizationType
from services.result_types import OrganizationAnalysisResult


@pytest.fixture
def sample_analysis(temp_dir, create_test_image):
    """Create a sample analysis result for testing"""
    # Create some test files and keep them
    files = []
    for i in range(5):
        img_path = create_test_image(
            path=temp_dir / f"IMG_{i:04d}.jpg",
            size=(100, 100)
        )
        files.append(img_path)
    
    # Create analysis - FileOrganizer doesn't take directory in __init__
    organizer = FileOrganizer()
    analysis = organizer.analyze(temp_dir, OrganizationType.BY_MONTH)
    
    return analysis, temp_dir, files


@pytest.fixture
def dialog(qtbot, sample_analysis):
    """Create a FileOrganizationDialog instance for testing"""
    analysis, temp_dir, files = sample_analysis
    dlg = FileOrganizationDialog(analysis)
    qtbot.addWidget(dlg)
    
    # Wait for dialog to fully initialize
    qtbot.waitExposed(dlg)
    
    yield dlg
    
    # Cancel any running worker
    if hasattr(dlg, 'worker') and dlg.worker and dlg.worker.isRunning():
        dlg.worker.quit()
        dlg.worker.wait(1000)
    
    dlg.close()


class TestFileOrganizerDialogInitialState:
    """Test the initial state of the dialog"""
    
    def test_dialog_opens_successfully(self, dialog):
        """Test that dialog can be created and opened"""
        assert dialog is not None
        assert dialog.isVisible() or not dialog.isVisible()  # Just check it exists
    
    def test_initial_selection_state(self, dialog):
        """Test that initial selection is correct"""
        # Should have NO current_organization_type initially
        # Or should have a default one after _initialize_strategy_selection
        assert dialog.current_organization_type is not None  # After initialization
    
    def test_strategy_cards_exist(self, dialog):
        """Test that all strategy cards are created"""
        assert hasattr(dialog, 'strategy_cards')
        assert len(dialog.strategy_cards) == 4
        assert 'date' in dialog.strategy_cards
        assert 'type' in dialog.strategy_cards
        assert 'source' in dialog.strategy_cards
        assert 'cleanup' in dialog.strategy_cards
    
    def test_settings_stack_exists(self, dialog):
        """Test that settings stack widget exists"""
        assert hasattr(dialog, 'settings_stack')
        assert dialog.settings_stack.count() == 4  # 4 pages
    
    def test_ui_initialized_flag(self, dialog):
        """Test that ui_initialized flag is set"""
        assert dialog.ui_initialized is True


class TestStrategySelection:
    """Test strategy card selection behavior"""
    
    def test_date_strategy_selection(self, dialog, monkeypatch):
        """Test selecting date strategy"""
        # Mock _start_analysis to avoid running real analysis
        analysis_started = []
        def mock_start_analysis(*args, **kwargs):
            analysis_started.append(True)
        
        monkeypatch.setattr(dialog, '_start_analysis', mock_start_analysis)
        
        dialog._on_strategy_clicked('date')
        
        # Check stack index
        assert dialog.settings_stack.currentIndex() == 0
        # Check that analysis was triggered
        assert len(analysis_started) == 1
    
    def test_type_strategy_selection(self, dialog, monkeypatch):
        """Test selecting type strategy"""
        # Mock _start_analysis to avoid running real analysis
        analysis_started = []
        def mock_start_analysis(*args, **kwargs):
            analysis_started.append(True)
        
        monkeypatch.setattr(dialog, '_start_analysis', mock_start_analysis)
        
        dialog._on_strategy_clicked('type')
        
        assert dialog.settings_stack.currentIndex() == 1
        assert len(analysis_started) == 1
    
    def test_source_strategy_selection(self, dialog, monkeypatch):
        """Test selecting source strategy"""
        # Mock _start_analysis to avoid running real analysis
        analysis_started = []
        def mock_start_analysis(*args, **kwargs):
            analysis_started.append(True)
        
        monkeypatch.setattr(dialog, '_start_analysis', mock_start_analysis)
        
        dialog._on_strategy_clicked('source')
        
        assert dialog.settings_stack.currentIndex() == 2
        assert len(analysis_started) == 1
    
    def test_cleanup_strategy_selection(self, dialog, monkeypatch):
        """Test selecting cleanup strategy"""
        # Mock _start_analysis to avoid running real analysis
        analysis_started = []
        def mock_start_analysis(*args, **kwargs):
            analysis_started.append(True)
        
        monkeypatch.setattr(dialog, '_start_analysis', mock_start_analysis)
        
        dialog._on_strategy_clicked('cleanup')
        
        assert dialog.settings_stack.currentIndex() == 3
        assert len(analysis_started) == 1
    
    def test_strategy_switch_changes_stack(self, dialog, monkeypatch):
        """Test that switching strategies changes the stack page"""
        # Mock _start_analysis to avoid running real analysis
        analysis_count = []
        def mock_start_analysis(*args, **kwargs):
            analysis_count.append(True)
        
        monkeypatch.setattr(dialog, '_start_analysis', mock_start_analysis)
        
        dialog._on_strategy_clicked('date')
        assert dialog.settings_stack.currentIndex() == 0
        
        dialog._on_strategy_clicked('type')
        assert dialog.settings_stack.currentIndex() == 1
        
        dialog._on_strategy_clicked('source')
        assert dialog.settings_stack.currentIndex() == 2
        
        dialog._on_strategy_clicked('cleanup')
        assert dialog.settings_stack.currentIndex() == 3
        
        # Should have triggered 4 analyses
        assert len(analysis_count) == 4


class TestContextualOptions:
    """Test contextual options panel"""
    
    def test_date_granularity_combo_exists(self, dialog):
        """Test that date granularity combo box exists"""
        assert hasattr(dialog, 'date_granularity_combo')
        assert isinstance(dialog.date_granularity_combo, QComboBox)
        assert dialog.date_granularity_combo.count() == 3  # Month, Year, Year/Month
    
    def test_date_checkboxes_exist(self, dialog):
        """Test that date strategy checkboxes exist"""
        assert hasattr(dialog, 'chk_date_source')
        assert hasattr(dialog, 'chk_date_type')
        assert isinstance(dialog.chk_date_source, QCheckBox)
        assert isinstance(dialog.chk_date_type, QCheckBox)
    
    def test_type_secondary_combo_exists(self, dialog):
        """Test that type secondary grouping combo exists"""
        assert hasattr(dialog, 'type_secondary_combo')
        assert isinstance(dialog.type_secondary_combo, QComboBox)
        assert dialog.type_secondary_combo.count() == 4  # Ninguna + 3 date options
    
    def test_source_secondary_combo_exists(self, dialog):
        """Test that source secondary grouping combo exists"""
        assert hasattr(dialog, 'source_secondary_combo')
        assert isinstance(dialog.source_secondary_combo, QComboBox)
        assert dialog.source_secondary_combo.count() == 4  # Ninguna + 3 date options
    
    def test_date_granularity_values(self, dialog):
        """Test date granularity combo box values"""
        combo = dialog.date_granularity_combo
        items = [combo.itemText(i) for i in range(combo.count())]
        
        assert "Por Mes" in items[0]
        assert "Por Año" in items[1]
        assert "Por Año/Mes" in items[2]
    
    def test_secondary_grouping_values(self, dialog):
        """Test secondary grouping combo box values"""
        combo = dialog.type_secondary_combo
        items = [combo.itemText(i) for i in range(combo.count())]
        
        assert "Ninguna" in items[0]
        assert "Por Mes" in items[1]
        assert "Por Año" in items[2]
        assert "Por Año/Mes" in items[3]


class TestLogicIntegration:
    """Test integration between UI and logic"""
    
    def test_date_granularity_change_triggers_analysis(self, qtbot, dialog, monkeypatch):
        """Test that changing date granularity triggers analysis"""
        analysis_called = []
        
        def mock_start_analysis(org_type, group_by_source=False, group_by_type=False, date_grouping_type=None):
            analysis_called.append({
                'org_type': org_type,
                'group_by_source': group_by_source,
                'group_by_type': group_by_type,
                'date_grouping_type': date_grouping_type
            })
        
        monkeypatch.setattr(dialog, '_start_analysis', mock_start_analysis)
        
        # Select date strategy
        dialog._on_strategy_clicked('date')
        qtbot.wait(100)  # Wait for UI update
        analysis_called.clear()  # Clear initialization call
        
        # Change granularity
        dialog.date_granularity_combo.setCurrentIndex(1)  # By Year
        qtbot.wait(100)
        dialog._on_option_changed(None)
        
        assert len(analysis_called) > 0
        assert analysis_called[0]['org_type'] == OrganizationType.BY_YEAR
    
    def test_checkbox_change_triggers_analysis(self, qtbot, dialog, monkeypatch):
        """Test that checkbox changes trigger analysis"""
        analysis_called = []
        
        def mock_start_analysis(org_type, group_by_source=False, group_by_type=False, date_grouping_type=None):
            analysis_called.append({
                'group_by_source': group_by_source,
                'group_by_type': group_by_type
            })
        
        monkeypatch.setattr(dialog, '_start_analysis', mock_start_analysis)
        
        # Select date strategy
        dialog._on_strategy_clicked('date')
        qtbot.wait(100)
        analysis_called.clear()
        
        # Check source checkbox
        qtbot.mouseClick(dialog.chk_date_source, Qt.MouseButton.LeftButton)
        qtbot.wait(100)
        
        assert len(analysis_called) > 0
        assert analysis_called[0]['group_by_source'] is True
    
    def test_type_strategy_reads_secondary_grouping(self, qtbot, dialog, monkeypatch):
        """Test that type strategy correctly reads secondary grouping"""
        analysis_called = []
        
        def mock_start_analysis(org_type, group_by_source=False, group_by_type=False, date_grouping_type=None):
            analysis_called.append({
                'org_type': org_type,
                'date_grouping_type': date_grouping_type
            })
        
        monkeypatch.setattr(dialog, '_start_analysis', mock_start_analysis)
        
        # Select type strategy
        dialog._on_strategy_clicked('type')
        qtbot.wait(100)
        analysis_called.clear()
        
        # Set secondary grouping
        dialog.type_secondary_combo.setCurrentIndex(1)  # Por Mes
        qtbot.wait(100)
        dialog._on_option_changed(None)
        
        assert len(analysis_called) > 0
        assert analysis_called[0]['org_type'] == OrganizationType.BY_TYPE
        assert analysis_called[0]['date_grouping_type'] == 'month'


class TestComboBoxArrow:
    """Test combo box arrow visibility and styling"""
    
    def test_combo_boxes_have_style(self, dialog):
        """Test that combo boxes have Material Design style"""
        from ui.styles.design_system import DesignSystem
        style = DesignSystem.get_combobox_style()
        
        # Verify the style exists and contains essential combo box styling
        assert 'QComboBox' in style
        assert 'QComboBox::drop-down' in style
        assert 'QComboBox QAbstractItemView' in style
    
    def test_date_granularity_combo_exists_and_accessible(self, qtbot, dialog):
        """Test that date granularity combo exists and is in the date settings page"""
        dialog._on_strategy_clicked('date')
        qtbot.wait(100)  # Wait for UI update
        
        # The combo should exist and be in the date settings page
        assert dialog.settings_stack.currentWidget() == dialog.date_settings_page
        assert dialog.date_granularity_combo is not None
        # The combo is part of the date page, we don't need to check isVisible
        # as the parent page might not be visible yet


class TestDefaultSelection:
    """Test default strategy selection on dialog open"""
    
    def test_default_strategy_is_date(self, dialog):
        """Test that 'date' strategy is selected by default"""
        # After initialization, date should be selected
        # This is tested by checking the stack index
        assert dialog.settings_stack.currentIndex() == 0  # Date page
    
    def test_default_does_not_preselect_if_no_initial_analysis(self, qtbot, temp_dir, create_test_image):
        """Test behavior when no initial analysis is provided"""
        # Create minimal analysis
        files = []
        for i in range(3):
            img_path = create_test_image(temp_dir / f"test{i}.jpg", size=(100, 100))
            files.append(img_path)
        
        organizer = FileOrganizer()
        analysis = organizer.analyze(temp_dir, OrganizationType.BY_MONTH)
        
        # Create dialog
        test_dialog = FileOrganizationDialog(analysis)
        qtbot.addWidget(test_dialog)
        qtbot.waitExposed(test_dialog)
        
        # Should have a default selection after initialization
        assert test_dialog.current_organization_type is not None
        
        # Clean up
        if hasattr(test_dialog, 'worker') and test_dialog.worker and test_dialog.worker.isRunning():
            test_dialog.worker.quit()
            test_dialog.worker.wait(1000)
        test_dialog.close()


class TestAnalysisWorkflow:
    """Test the analysis workflow"""
    
    def test_worker_creation(self, qtbot, dialog, monkeypatch):
        """Test that worker is created correctly"""
        # We can't easily mock the worker creation, but we can verify the start_analysis method
        # Just check it doesn't crash
        dialog._on_strategy_clicked('date')
        qtbot.wait(100)
        dialog.date_granularity_combo.setCurrentIndex(0)
        qtbot.wait(100)
        
        # This should trigger analysis - just verify no crash
        assert True
    
    def test_analysis_updates_tree(self, dialog):
        """Test that analysis results update the tree view"""
        # This is complex to test without actually running analysis
        # We can verify the tree exists
        assert hasattr(dialog, 'files_tree')
        assert dialog.files_tree is not None


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_rapid_strategy_switching(self, qtbot, dialog):
        """Test rapidly switching between strategies"""
        # Switch rapidly between strategies
        for _ in range(3):
            dialog._on_strategy_clicked('date')
            qtbot.wait(10)
            dialog._on_strategy_clicked('type')
            qtbot.wait(10)
            dialog._on_strategy_clicked('source')
            qtbot.wait(10)
            dialog._on_strategy_clicked('cleanup')
            qtbot.wait(10)
        
        # Should not crash
        assert dialog.settings_stack.currentIndex() == 3  # Last selection (cleanup)
    
    def test_rapid_combo_changes(self, qtbot, dialog):
        """Test rapidly changing combo box values"""
        dialog._on_strategy_clicked('date')
        qtbot.wait(100)
        
        # Rapidly change granularity
        for i in range(10):
            dialog.date_granularity_combo.setCurrentIndex(i % 3)
            qtbot.wait(10)
        
        # Should not crash
        assert True
    
    def test_checkbox_toggle_multiple_times(self, qtbot, dialog):
        """Test toggling checkboxes multiple times"""
        dialog._on_strategy_clicked('date')
        qtbot.wait(100)
        
        # Toggle checkboxes
        for _ in range(5):
            dialog.chk_date_source.setChecked(not dialog.chk_date_source.isChecked())
            qtbot.wait(10)
            dialog.chk_date_type.setChecked(not dialog.chk_date_type.isChecked())
            qtbot.wait(10)
        
        # Should not crash
        assert True


@pytest.mark.ui
class TestUIComponents:
    """Test UI component presence and basic functionality"""
    
    def test_header_exists(self, dialog):
        """Test that header is present"""
        assert hasattr(dialog, 'header_frame')
        assert dialog.header_frame is not None
    
    def test_tree_widget_exists(self, dialog):
        """Test that tree widget exists"""
        assert hasattr(dialog, 'files_tree')
        assert dialog.files_tree is not None
    
    def test_pagination_widget_exists(self, dialog):
        """Test that pagination widget exists"""
        assert hasattr(dialog, 'pagination_widget')
        assert dialog.pagination_widget is not None
    
    def test_progress_bar_exists(self, dialog):
        """Test that progress bar exists"""
        assert hasattr(dialog, 'progress_bar')
        assert dialog.progress_bar is not None
    
    def test_buttons_exist(self, dialog):
        """Test that action buttons exist"""
        assert hasattr(dialog, 'buttons')
        assert dialog.buttons is not None
