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


@pytest.mark.unit
class TestBackupWithSameFilenameInDifferentDirectories:
    """
    Tests CRÍTICOS: Backup debe preservar estructura de directorios
    cuando archivos con el mismo nombre están en subdirectorios diferentes.
    
    Esto asegura que no haya conflictos ni sobrescritura durante el backup.
    """
    
    def test_backup_same_filename_different_dirs(self, temp_dir):
        """Test: Archivos con mismo nombre en diferentes directorios se respaldan correctamente"""
        # Arrange
        service = ConcreteService('TestService')
        
        # Crear estructura con archivo "photo.jpg" en 3 directorios diferentes
        dir1 = temp_dir / 'folder1'
        dir2 = temp_dir / 'folder2'
        dir3 = temp_dir / 'folder3'
        
        dir1.mkdir()
        dir2.mkdir()
        dir3.mkdir()
        
        file1 = dir1 / 'photo.jpg'
        file2 = dir2 / 'photo.jpg'
        file3 = dir3 / 'photo.jpg'
        
        # Contenidos diferentes para verificar no sobrescritura
        file1.write_text('content from folder1')
        file2.write_text('content from folder2')
        file3.write_text('content from folder3')
        
        files = [file1, file2, file3]
        
        # Act
        backup_path = service._create_backup_for_operation(
            files,
            'deletion'
        )
        
        # Assert
        assert backup_path is not None
        assert backup_path.exists()
        
        # Verificar que se crearon 3 archivos en el backup
        backup_files = list(backup_path.rglob('photo.jpg'))
        assert len(backup_files) == 3, f"Expected 3 files but found {len(backup_files)}"
        
        # Verificar que se preservó la estructura de directorios
        backup_file1 = backup_path / 'folder1' / 'photo.jpg'
        backup_file2 = backup_path / 'folder2' / 'photo.jpg'
        backup_file3 = backup_path / 'folder3' / 'photo.jpg'
        
        assert backup_file1.exists(), f"Expected {backup_file1} to exist"
        assert backup_file2.exists(), f"Expected {backup_file2} to exist"
        assert backup_file3.exists(), f"Expected {backup_file3} to exist"
        
        # Verificar que los contenidos se preservaron correctamente (sin sobrescritura)
        assert backup_file1.read_text() == 'content from folder1'
        assert backup_file2.read_text() == 'content from folder2'
        assert backup_file3.read_text() == 'content from folder3'
    
    def test_backup_nested_directories_same_filename(self, temp_dir):
        """Test: Estructura anidada con mismo nombre de archivo en cada nivel"""
        # Arrange
        service = ConcreteService('TestService')
        
        # Estructura: temp_dir/image.jpg
        #            temp_dir/level1/image.jpg
        #            temp_dir/level1/level2/image.jpg
        #            temp_dir/level1/level2/level3/image.jpg
        
        level1 = temp_dir / 'level1'
        level2 = level1 / 'level2'
        level3 = level2 / 'level3'
        
        level1.mkdir()
        level2.mkdir()
        level3.mkdir()
        
        file_root = temp_dir / 'image.jpg'
        file_l1 = level1 / 'image.jpg'
        file_l2 = level2 / 'image.jpg'
        file_l3 = level3 / 'image.jpg'
        
        file_root.write_text('root')
        file_l1.write_text('level1')
        file_l2.write_text('level2')
        file_l3.write_text('level3')
        
        files = [file_root, file_l1, file_l2, file_l3]
        
        # Act
        backup_path = service._create_backup_for_operation(
            files,
            'nested_deletion'
        )
        
        # Assert
        assert backup_path is not None
        
        # Verificar estructura anidada en backup
        assert (backup_path / 'image.jpg').exists()
        assert (backup_path / 'level1' / 'image.jpg').exists()
        assert (backup_path / 'level1' / 'level2' / 'image.jpg').exists()
        assert (backup_path / 'level1' / 'level2' / 'level3' / 'image.jpg').exists()
        
        # Verificar contenidos
        assert (backup_path / 'image.jpg').read_text() == 'root'
        assert (backup_path / 'level1' / 'image.jpg').read_text() == 'level1'
        assert (backup_path / 'level1' / 'level2' / 'image.jpg').read_text() == 'level2'
        assert (backup_path / 'level1' / 'level2' / 'level3' / 'image.jpg').read_text() == 'level3'
    
    def test_backup_multiple_files_same_name_different_dirs(self, temp_dir):
        """Test: Múltiples archivos con mismo nombre en estructura compleja"""
        # Arrange
        service = ConcreteService('TestService')
        
        # Crear estructura compleja
        dirs = [
            temp_dir / 'photos' / '2023',
            temp_dir / 'photos' / '2024',
            temp_dir / 'videos' / '2023',
            temp_dir / 'videos' / '2024',
            temp_dir / 'backup' / 'old'
        ]
        
        for d in dirs:
            d.mkdir(parents=True)
        
        # Crear archivos con nombres duplicados en diferentes lugares
        files = []
        for i, d in enumerate(dirs):
            # Crear 2 archivos en cada directorio
            f1 = d / 'file.jpg'
            f2 = d / 'document.pdf'
            
            f1.write_text(f'content_{i}_jpg')
            f2.write_text(f'content_{i}_pdf')
            
            files.extend([f1, f2])
        
        # Total: 10 archivos (5 directorios × 2 archivos)
        assert len(files) == 10
        
        # Act
        backup_path = service._create_backup_for_operation(
            files,
            'complex_deletion'
        )
        
        # Assert
        assert backup_path is not None
        
        # Verificar que se crearon 10 archivos en backup
        all_backup_files = list(backup_path.rglob('*'))
        backup_files_only = [f for f in all_backup_files if f.is_file() and not f.name.endswith('_metadata.txt')]
        assert len(backup_files_only) == 10
        
        # Verificar estructura de directorios completa
        assert (backup_path / 'photos' / '2023').exists()
        assert (backup_path / 'photos' / '2024').exists()
        assert (backup_path / 'videos' / '2023').exists()
        assert (backup_path / 'videos' / '2024').exists()
        assert (backup_path / 'backup' / 'old').exists()
        
        # Verificar algunos contenidos específicos
        assert (backup_path / 'photos' / '2023' / 'file.jpg').read_text() == 'content_0_jpg'
        assert (backup_path / 'videos' / '2024' / 'document.pdf').read_text() == 'content_3_pdf'
    
    def test_backup_preserves_relative_paths_correctly(self, temp_dir):
        """Test: Verificar que las rutas relativas se preservan correctamente desde base_directory"""
        # Arrange
        service = ConcreteService('TestService')
        
        # Crear subdirectorios con mismo archivo
        sub1 = temp_dir / 'a' / 'b' / 'c'
        sub2 = temp_dir / 'x' / 'y' / 'z'
        
        sub1.mkdir(parents=True)
        sub2.mkdir(parents=True)
        
        file1 = sub1 / 'test.txt'
        file2 = sub2 / 'test.txt'
        
        file1.write_text('abc content')
        file2.write_text('xyz content')
        
        files = [file1, file2]
        
        # Act
        backup_path = service._create_backup_for_operation(
            files,
            'path_test'
        )
        
        # Assert
        # La estructura relativa desde temp_dir debe preservarse
        assert (backup_path / 'a' / 'b' / 'c' / 'test.txt').exists()
        assert (backup_path / 'x' / 'y' / 'z' / 'test.txt').exists()
        
        assert (backup_path / 'a' / 'b' / 'c' / 'test.txt').read_text() == 'abc content'
        assert (backup_path / 'x' / 'y' / 'z' / 'test.txt').read_text() == 'xyz content'
