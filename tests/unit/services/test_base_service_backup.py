"""
Tests unitarios para BaseService._create_backup_for_operation

Verifica la funcionalidad centralizada de gestión de backups:
- Extracción de paths desde diferentes estructuras
- Creación de backup con nombres consistentes
- Manejo de errores
"""

import pytest
from pathlib import Path
from dataclasses import dataclass
from services.base_service import BaseService, BackupCreationError


@dataclass
class MockFileInfo:
    """Mock de estructura con atributo path"""
    path: Path
    size: int


@dataclass
class MockRenameItem:
    """Mock de item de renombrado con original_path"""
    original_path: Path
    new_name: str


@dataclass
class MockDuplicatePair:
    """Mock de DuplicatePair con heic_path y jpg_path"""
    heic_path: Path
    jpg_path: Path
    base_name: str


class ConcreteService(BaseService):
    """Servicio concreto para testing (BaseService es abstracta)"""
    pass


class TestCreateBackupForOperation:
    """Tests para método _create_backup_for_operation"""
    
    def test_backup_with_path_list(self, temp_dir):
        """Test: Crear backup desde lista de Path objects"""
        # Arrange
        service = ConcreteService('TestService')
        files = [
            temp_dir / 'file1.jpg',
            temp_dir / 'file2.jpg',
            temp_dir / 'file3.jpg'
        ]
        
        # Crear archivos reales
        for f in files:
            f.write_text('test content')
        
        # Act
        backup_path = service._create_backup_for_operation(
            files,
            'test_operation'
        )
        
        # Assert
        assert backup_path is not None
        assert backup_path.exists()
        assert 'backup_test_operation' in backup_path.name
        assert service.backup_dir == backup_path
        
        # Verificar que se crearon archivos en backup
        backup_files = list(backup_path.rglob('*.jpg'))
        assert len(backup_files) == 3
    
    def test_backup_with_dict_list(self, temp_dir):
        """Test: Crear backup desde lista de dicts con 'original_path'"""
        # Arrange
        service = ConcreteService('TestService')
        files = [
            temp_dir / 'file1.jpg',
            temp_dir / 'file2.jpg'
        ]
        
        for f in files:
            f.write_text('test content')
        
        # Simular plan de renombrado (dicts)
        plan = [
            {'original_path': files[0], 'new_name': 'renamed1.jpg'},
            {'original_path': files[1], 'new_name': 'renamed2.jpg'}
        ]
        
        # Act
        backup_path = service._create_backup_for_operation(
            plan,
            'renaming'
        )
        
        # Assert
        assert backup_path is not None
        assert 'backup_renaming' in backup_path.name
        backup_files = list(backup_path.rglob('*.jpg'))
        assert len(backup_files) == 2
    
    def test_backup_with_dataclass_list(self, temp_dir):
        """Test: Crear backup desde lista de dataclasses"""
        # Arrange
        service = ConcreteService('TestService')
        files = [
            temp_dir / 'file1.jpg',
            temp_dir / 'file2.jpg'
        ]
        
        for f in files:
            f.write_text('test content')
        
        # Usar dataclass mock
        items = [MockFileInfo(path=f, size=100) for f in files]
        
        # Act
        backup_path = service._create_backup_for_operation(
            items,
            'cleanup'
        )
        
        # Assert
        assert backup_path is not None
        assert 'backup_cleanup' in backup_path.name
    
    def test_backup_with_duplicate_pair(self, temp_dir):
        """Test: Crear backup desde DuplicatePair (heic_path, jpg_path)"""
        # Arrange
        service = ConcreteService('TestService')
        heic_file = temp_dir / 'photo.heic'
        jpg_file = temp_dir / 'photo.jpg'
        
        heic_file.write_text('heic content')
        jpg_file.write_text('jpg content')
        
        pairs = [
            MockDuplicatePair(
                heic_path=heic_file,
                jpg_path=jpg_file,
                base_name='photo'
            )
        ]
        
        # Act - debe extraer heic_path (primer attr en la lista de to_path)
        backup_path = service._create_backup_for_operation(
            pairs,
            'heic_removal'
        )
        
        # Assert
        assert backup_path is not None
        assert 'backup_heic_removal' in backup_path.name
    
    def test_backup_empty_list(self):
        """Test: Backup con lista vacía retorna None"""
        # Arrange
        service = ConcreteService('TestService')
        
        # Act
        backup_path = service._create_backup_for_operation(
            [],
            'test_operation'
        )
        
        # Assert
        assert backup_path is None
    
    def test_backup_with_nonexistent_files(self, temp_dir):
        """Test: Backup falla si archivos no existen"""
        # Arrange
        service = ConcreteService('TestService')
        files = [
            temp_dir / 'nonexistent1.jpg',
            temp_dir / 'nonexistent2.jpg'
        ]
        
        # Act & Assert
        with pytest.raises(BackupCreationError):
            service._create_backup_for_operation(
                files,
                'test_operation'
            )
    
    def test_backup_finds_common_directory(self, temp_dir):
        """Test: Encuentra directorio común entre múltiples paths"""
        # Arrange
        service = ConcreteService('TestService')
        
        subdir1 = temp_dir / 'subdir1'
        subdir2 = temp_dir / 'subdir2'
        subdir1.mkdir()
        subdir2.mkdir()
        
        files = [
            subdir1 / 'file1.jpg',
            subdir2 / 'file2.jpg'
        ]
        
        for f in files:
            f.write_text('content')
        
        # Act
        backup_path = service._create_backup_for_operation(
            files,
            'test_operation'
        )
        
        # Assert
        assert backup_path is not None
        # Backup se crea en la ubicación configurada por Config
        # Verificar que ambos archivos fueron respaldados
        backup_files = list(backup_path.rglob('*.jpg'))
        assert len(backup_files) == 2
    
    def test_backup_metadata_file_created(self, temp_dir):
        """Test: Verifica que se crea archivo de metadata"""
        # Arrange
        service = ConcreteService('TestService')
        files = [temp_dir / 'file.jpg']
        files[0].write_text('content')
        
        # Act
        backup_path = service._create_backup_for_operation(
            files,
            'test_operation'
        )
        
        # Assert
        metadata_file = backup_path / 'test_operation_metadata.txt'
        assert metadata_file.exists()
        
        # Verificar contenido del metadata
        content = metadata_file.read_text()
        assert 'file.jpg' in content
    
    def test_backup_sets_backup_dir_attribute(self, temp_dir):
        """Test: Backup actualiza self.backup_dir"""
        # Arrange
        service = ConcreteService('TestService')
        assert service.backup_dir is None
        
        files = [temp_dir / 'file.jpg']
        files[0].write_text('content')
        
        # Act
        backup_path = service._create_backup_for_operation(
            files,
            'test_operation'
        )
        
        # Assert
        assert service.backup_dir == backup_path
        assert service.backup_dir is not None


class TestBackupCreationError:
    """Tests para excepción BackupCreationError"""
    
    def test_exception_can_be_raised(self):
        """Test: Excepción puede lanzarse correctamente"""
        with pytest.raises(BackupCreationError) as exc_info:
            raise BackupCreationError("Test error")
        
        assert "Test error" in str(exc_info.value)
    
    def test_exception_with_chaining(self):
        """Test: Excepción soporta chaining de excepciones"""
        original_error = ValueError("Original error")
        
        with pytest.raises(BackupCreationError) as exc_info:
            try:
                raise original_error
            except ValueError as e:
                raise BackupCreationError("Backup failed") from e
        
        assert exc_info.value.__cause__ == original_error
