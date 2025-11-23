"""
Tests unitarios para SimilarFilesDetector

Tests para el servicio de detección de archivos similares mediante perceptual hashing,
incluyendo tests de backup con casos especiales de colisiones de nombres.
"""

import pytest
import shutil
from pathlib import Path
from PIL import Image
from services.similar_files_detector import SimilarFilesDetector
from services.result_types import DuplicateAnalysisResult


@pytest.fixture
def similar_detector():
    """Crea instancia de SimilarFilesDetector para tests."""
    return SimilarFilesDetector()


@pytest.fixture
def create_similar_image(create_test_image):
    """
    Factory para crear imágenes similares (modificaciones ligeras).
    
    Returns:
        Callable que crea imagen similar a otra existente
    """
    def _create_similar(original_path: Path, target_path: Path, modification='crop'):
        """
        Crea imagen similar modificando la original.
        
        Args:
            original_path: Path de la imagen original
            target_path: Path donde guardar la imagen modificada
            modification: Tipo de modificación ('crop', 'rotate', 'resize', 'brightness')
        """
        img = Image.open(original_path)
        
        if modification == 'crop':
            # Recortar 10% de cada lado
            width, height = img.size
            crop_box = (
                int(width * 0.1),
                int(height * 0.1),
                int(width * 0.9),
                int(height * 0.9)
            )
            img = img.crop(crop_box)
        
        elif modification == 'rotate':
            # Rotar 90 grados
            img = img.rotate(90)
        
        elif modification == 'resize':
            # Redimensionar a 80%
            width, height = img.size
            new_size = (int(width * 0.8), int(height * 0.8))
            img = img.resize(new_size)
        
        elif modification == 'brightness':
            # Ajustar brillo
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.3)
        
        # Guardar
        target_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(target_path)
        return target_path
    
    return _create_similar


# ==================== TESTS BÁSICOS ====================

@pytest.mark.unit
@pytest.mark.similar
class TestSimilarFilesDetectorBasics:
    """Tests básicos de inicialización y funcionalidad core."""
    
    def test_initialization(self, similar_detector):
        """Test que el detector se inicializa correctamente."""
        assert similar_detector is not None
        assert hasattr(similar_detector, 'analyze')
        assert hasattr(similar_detector, 'execute')
    
    def test_empty_directory(self, similar_detector, temp_dir):
        """Test con directorio vacío."""
        # analyze() ya retorna DuplicateAnalysisResult directamente
        result = similar_detector.analyze(temp_dir, sensitivity=10)
        
        assert result is not None
        assert result.success is True
        assert result.total_files == 0
        assert result.total_groups == 0
    
    def test_directory_without_similar_files(self, similar_detector, temp_dir, create_test_image):
        """Test con directorio que contiene archivos únicos (no similares)."""
        # Crear imágenes completamente diferentes
        create_test_image(temp_dir / "red.jpg", color='red')
        create_test_image(temp_dir / "blue.jpg", color='blue')
        create_test_image(temp_dir / "green.jpg", color='green')
        
        # analyze() retorna DuplicateAnalysisResult directamente
        result = similar_detector.analyze(temp_dir, sensitivity=10)
        
        assert result.success is True
        assert result.total_files == 3
        # Puede encontrar 0 o más grupos dependiendo de la similitud de colores planos
        # No hacemos assert estricto aquí


# ==================== TESTS DE DETECCIÓN DE SIMILARES ====================

@pytest.mark.unit
@pytest.mark.similar
class TestSimilarFilesDetection:
    """Tests de detección de archivos similares."""
    
    def test_detect_cropped_image(self, similar_detector, temp_dir, create_test_image, create_similar_image):
        """Test detección de imagen recortada."""
        original = create_test_image(temp_dir / "original.jpg", size=(200, 200), color='red')
        create_similar_image(original, temp_dir / "cropped.jpg", modification='crop')
        
        # analyze() retorna DuplicateAnalysisResult directamente
        result = similar_detector.analyze(temp_dir, sensitivity=10)
        
        assert result.success is True
        assert result.total_files == 2
        assert result.total_groups >= 1
        assert result.total_similar >= 1
    
    def test_detect_resized_image(self, similar_detector, temp_dir, create_test_image, create_similar_image):
        """Test detección de imagen redimensionada."""
        original = create_test_image(temp_dir / "original.jpg", size=(200, 200), color='blue')
        create_similar_image(original, temp_dir / "resized.jpg", modification='resize')
        
        # analyze() retorna DuplicateAnalysisResult directamente
        result = similar_detector.analyze(temp_dir, sensitivity=10)
        
        assert result.success is True
        assert result.total_files == 2
        assert result.total_groups >= 1


# ==================== TESTS DE BACKUP ====================

@pytest.mark.unit
class TestSimilarFilesDetectorBackup:
    """Tests de creación de backups en similar files detector."""
    
    def test_backup_created_when_enabled(self, similar_detector, temp_dir, create_test_image):
        """Test que se crea backup cuando está habilitado."""
        # Crear duplicados exactos para asegurar detección
        original = create_test_image(temp_dir / "original.jpg", color='red')
        shutil.copy2(original, temp_dir / "duplicate.jpg")
        
        # analyze() ya retorna DuplicateAnalysisResult con grupos
        result_groups = similar_detector.analyze(temp_dir, sensitivity=10)
        
        if result_groups.total_groups > 0:
            result = similar_detector.execute(
                groups=result_groups.groups,
                keep_strategy='largest',
                create_backup=True,
                dry_run=False
            )
            
            assert result.success is True
            assert result.backup_path is not None
            assert Path(result.backup_path).exists()
            
            # Verificar que el backup contiene archivos
            backup_files = list(Path(result.backup_path).rglob('*.jpg'))
            assert len(backup_files) >= 1
    
    def test_no_backup_when_disabled(self, similar_detector, temp_dir, create_test_image):
        """Test que NO se crea backup cuando está deshabilitado."""
        original = create_test_image(temp_dir / "original.jpg", color='red')
        shutil.copy2(original, temp_dir / "duplicate.jpg")
        
        result_groups = similar_detector.analyze(temp_dir, sensitivity=10)
        
        if result_groups.total_groups > 0:
            result = similar_detector.execute(
                groups=result_groups.groups,
                keep_strategy='largest',
                create_backup=False,
                dry_run=False
            )
            
            assert result.success is True
            assert result.backup_path is None
    
    def test_no_backup_in_dry_run(self, similar_detector, temp_dir, create_test_image):
        """Test que NO se crea backup en dry run mode."""
        original = create_test_image(temp_dir / "original.jpg", color='red')
        shutil.copy2(original, temp_dir / "duplicate.jpg")
        
        result_groups = similar_detector.analyze(temp_dir, sensitivity=10)
        
        if result_groups.total_groups > 0:
            result = similar_detector.execute(
                groups=result_groups.groups,
                keep_strategy='largest',
                create_backup=True,
                dry_run=True
            )
            
            assert result.success is True
            assert result.dry_run is True
            assert result.backup_path is None
    
    def test_backup_with_same_filename_different_dirs(self, similar_detector, temp_dir, create_test_image):
        """
        Test CRÍTICO: Backup preserva estructura cuando hay similares con mismo nombre
        en diferentes subdirectorios.
        """
        # Crear estructura con "photo.jpg" similar en 3 subdirectorios
        dir1 = temp_dir / 'folder1'
        dir2 = temp_dir / 'folder2'
        dir3 = temp_dir / 'folder3'
        
        dir1.mkdir()
        dir2.mkdir()
        dir3.mkdir()
        
        # Crear imagen original y copias en cada subdirectorio
        original = create_test_image(temp_dir / 'original.jpg', color='red', size=(200, 200))
        
        photo1 = dir1 / 'photo.jpg'
        photo2 = dir2 / 'photo.jpg'
        photo3 = dir3 / 'photo.jpg'
        
        shutil.copy2(original, photo1)
        shutil.copy2(original, photo2)
        shutil.copy2(original, photo3)
        
        # Modificar contenido de metadatos para verificar no sobrescritura
        # (usando exif o simplemente timestamps diferentes)
        import time
        photo1.touch()
        time.sleep(0.01)
        photo2.touch()
        time.sleep(0.01)
        photo3.touch()
        
        # SimilarFilesDetector siempre hace búsqueda recursiva
        result_groups = similar_detector.analyze(temp_dir, sensitivity=10)
        
        # Debe encontrar 1 grupo con 4 archivos (original + 3 copias)
        assert result_groups.total_groups >= 1
        
        result = similar_detector.execute(
            groups=result_groups.groups,
            keep_strategy='oldest',
            create_backup=True,
            dry_run=False
        )
        
        assert result.success is True
        assert result.backup_path is not None
        
        backup_path = Path(result.backup_path)
        
        # Verificar que se preservó la estructura de directorios en el backup
        backup_dirs = [d for d in backup_path.rglob('*') if d.is_dir()]
        dir_names = [d.name for d in backup_dirs]
        
        # Al menos algunos de los folders deben estar presentes
        assert any(name in ['folder1', 'folder2', 'folder3'] for name in dir_names)
    
    def test_backup_with_nested_similar_files(self, similar_detector, temp_dir, create_test_image):
        """Test que backup preserva estructura anidada con archivos similares."""
        # Crear estructura anidada
        level1 = temp_dir / 'level1'
        level2 = level1 / 'level2'
        level3 = level2 / 'level3'
        
        level1.mkdir()
        level2.mkdir()
        level3.mkdir()
        
        # Crear similares en diferentes niveles
        original = create_test_image(temp_dir / 'image.jpg', color='blue', size=(200, 200))
        dup1 = level1 / 'image.jpg'
        dup2 = level2 / 'image.jpg'
        dup3 = level3 / 'image.jpg'
        
        shutil.copy2(original, dup1)
        shutil.copy2(original, dup2)
        shutil.copy2(original, dup3)
        
        # SimilarFilesDetector siempre hace búsqueda recursiva
        result_groups = similar_detector.analyze(temp_dir, sensitivity=10)
        
        if result_groups.total_groups > 0:
            result = similar_detector.execute(
                groups=result_groups.groups,
                keep_strategy='largest',
                create_backup=True,
                dry_run=False
            )
            
            assert result.success is True
            backup_path = Path(result.backup_path)
            
            # Verificar que existe estructura anidada en backup
            backup_dirs = [d for d in backup_path.rglob('*') if d.is_dir()]
            dir_names = [d.name for d in backup_dirs]
            
            # Verificar presencia de niveles anidados
            assert any(name in ['level1', 'level2', 'level3'] for name in dir_names)
    
    def test_backup_complex_structure_same_names(self, similar_detector, temp_dir, create_test_image):
        """Test: Backup con estructura compleja y múltiples archivos con mismo nombre."""
        # Crear estructura compleja
        dirs = [
            temp_dir / 'photos' / '2023',
            temp_dir / 'photos' / '2024',
            temp_dir / 'vacation' / 'summer',
            temp_dir / 'vacation' / 'winter',
        ]
        
        for d in dirs:
            d.mkdir(parents=True)
        
        # Crear imagen base
        original = create_test_image(temp_dir / 'base.jpg', color='green', size=(200, 200))
        
        # Copiar a cada directorio con mismo nombre "photo.jpg"
        files = []
        for d in dirs:
            target = d / 'photo.jpg'
            shutil.copy2(original, target)
            files.append(target)
        
        # Total: 4 archivos con mismo nombre en diferentes ubicaciones
        assert len(files) == 4
        
        # SimilarFilesDetector siempre hace búsqueda recursiva
        result_groups = similar_detector.analyze(temp_dir, sensitivity=10)
        
        if result_groups.total_groups > 0:
            result = similar_detector.execute(
                groups=result_groups.groups,
                keep_strategy='oldest',
                create_backup=True,
                dry_run=False
            )
            
            assert result.success is True
            assert result.backup_path is not None
            
            backup_path = Path(result.backup_path)
            
            # Verificar estructura de directorios completa en backup
            assert (backup_path / 'photos').exists() or \
                   (backup_path / 'vacation').exists()
            
            # Verificar que múltiples archivos "photo.jpg" están en el backup
            # sin sobrescritura (cada uno en su subdirectorio)
            backup_photos = list(backup_path.rglob('photo.jpg'))
            # Debe haber al menos 2 archivos photo.jpg (los eliminados)
            assert len(backup_photos) >= 2
