import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime
import re
from services.file_organizer_service import FileOrganizer, OrganizationType
from utils.file_utils import is_whatsapp_file

@pytest.fixture
def organizer():
    return FileOrganizer()

@pytest.fixture
def create_nested_structure(temp_dir, create_test_image):
    def _create_structure(subdirs_config=None):
        if subdirs_config is None:
            subdirs_config = {}
        
        created_files = {}
        for subdir_path, filenames in subdirs_config.items():
            subdir = temp_dir / subdir_path
            subdir.mkdir(parents=True, exist_ok=True)
            files = []
            for filename in filenames:
                file_path = subdir / filename
                if filename.endswith(('.jpg', '.jpeg', '.png', '.heic')):
                    create_test_image(file_path, size=(100, 100), color='blue')
                else:
                    file_path.write_bytes(b'dummy video content' * 100)
                files.append(file_path)
            created_files[subdir_path] = files
        return temp_dir, created_files
    return _create_structure

@pytest.mark.unit
@pytest.mark.organization
class TestFileOrganizerCombined:
    """Tests for combined organization strategies."""

    def test_by_month_grouped_by_source(self, organizer, create_nested_structure):
        """Test BY_MONTH with group_by_source=True."""
        root_dir, files = create_nested_structure({
            'photos': ['IMG-20231025-WA0001.jpg', 'photo1.jpg']
        })
        
        result = organizer.analyze(
            root_dir, 
            OrganizationType.BY_MONTH,
            group_by_source=True
        )
        
        assert result.success is True
        
        # Check for YYYY_MM/WhatsApp and YYYY_MM/Unknown (or other source)
        whatsapp_moves = [m for m in result.move_plan if 'WhatsApp' in m.target_folder]
        assert len(whatsapp_moves) > 0
        
        # Verify structure: 2023_10/WhatsApp
        for move in whatsapp_moves:
            parts = Path(move.target_folder).parts
            assert len(parts) == 2
            assert '_' in parts[0]  # YYYY_MM
            assert parts[1] == 'WhatsApp'

    def test_by_month_grouped_by_type(self, organizer, create_nested_structure):
        """Test BY_MONTH with group_by_type=True."""
        root_dir, files = create_nested_structure({
            'mixed': ['photo1.jpg', 'video1.mp4']
        })
        
        result = organizer.analyze(
            root_dir, 
            OrganizationType.BY_MONTH,
            group_by_type=True
        )
        
        assert result.success is True
        
        # Check for YYYY_MM/Fotos and YYYY_MM/Videos
        photo_moves = [m for m in result.move_plan if 'Fotos' in m.target_folder]
        video_moves = [m for m in result.move_plan if 'Videos' in m.target_folder]
        
        assert len(photo_moves) > 0
        assert len(video_moves) > 0
        
        # Verify structure
        for move in photo_moves:
            parts = Path(move.target_folder).parts
            assert len(parts) == 2
            assert parts[1] == 'Fotos'

    def test_by_type_grouped_by_source(self, organizer, create_nested_structure):
        """Test BY_TYPE with group_by_source=True."""
        root_dir, files = create_nested_structure({
            'photos': ['IMG-20231025-WA0001.jpg', 'photo1.jpg']
        })
        
        result = organizer.analyze(
            root_dir, 
            OrganizationType.BY_TYPE,
            group_by_source=True
        )
        
        assert result.success is True
        
        # Check for Fotos/WhatsApp
        whatsapp_moves = [m for m in result.move_plan if 'WhatsApp' in m.target_folder]
        assert len(whatsapp_moves) > 0
        
        for move in whatsapp_moves:
            parts = Path(move.target_folder).parts
            assert len(parts) == 2
            assert parts[0] == 'Fotos'
            assert parts[1] == 'WhatsApp'

    def test_by_source_grouped_by_date(self, organizer, create_nested_structure):
        """Test BY_SOURCE with group_by_date=True."""
        root_dir, files = create_nested_structure({
            'photos': ['IMG-20231025-WA0001.jpg']
        })
        
        result = organizer.analyze(
            root_dir, 
            OrganizationType.BY_SOURCE,
            date_grouping_type='month'
        )
        
        assert result.success is True
        
        # Check for WhatsApp/2023_10
        whatsapp_moves = [m for m in result.move_plan if 'WhatsApp' in m.target_folder]
        assert len(whatsapp_moves) > 0
        
        for move in whatsapp_moves:
            parts = Path(move.target_folder).parts
            assert len(parts) == 2
            assert parts[0] == 'WhatsApp'
            assert re.match(r'\d{4}_\d{2}', parts[1])

    def test_by_type_grouped_by_date(self, organizer, create_nested_structure):
        """Test organización por Tipo agrupada por Fecha"""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg']
        })
        
        result = organizer.analyze(
            root_dir,
            OrganizationType.BY_TYPE,
            date_grouping_type='year'
        )
        
        move_plan = result.move_plan
        
        # Verificar estructura: Tipo/YYYY/archivo
        photo_moves = [m for m in move_plan if 'Fotos' in str(m.target_path)]
        assert len(photo_moves) > 0
        
        for move in photo_moves:
            # Debe tener formato Fotos/YYYY
            parts = Path(move.target_folder).parts
            assert len(parts) == 2 # Tipo, Fecha
            assert parts[0] == 'Fotos'
            assert re.match(r'\d{4}', parts[1])  # YYYY
