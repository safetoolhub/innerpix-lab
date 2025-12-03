"""
Tests exhaustivos para el servicio HEICRemover.

Cubre todos los casos de uso y edge cases:
- Análisis básico con duplicados
- Validación de diferencias temporales
- Archivos en diferentes directorios (no deben ser marcados como duplicados)
- Archivos con mismo nombre pero diferentes fechas
- Archivos huérfanos (sin pareja)
- Eliminación de duplicados (keep JPG / keep HEIC)
- Dry run mode
- Backup creation
- Estadísticas y métricas
- Casos edge: archivos vacíos, permisos, etc.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from services.heic_remover_service import HEICRemover, DuplicatePair
from config import Config
from services.result_types import HeicAnalysisResult, HeicDeletionResult
import time
import os


# ==================== FIXTURES ====================

@pytest.fixture
def heic_remover():
    """Crea una instancia de HEICRemover para tests."""
    return HEICRemover()


@pytest.fixture
def create_heic_jpg_pair(create_test_image):
    """
    Factory fixture para crear pares HEIC/JPG con control completo de fechas.
    
    Returns:
        Callable que crea un par HEIC/JPG con fechas específicas
    """
    def _create_pair(
        directory: Path,
        base_name: str,
        heic_mtime: datetime = None,
        jpg_mtime: datetime = None,
        heic_size_kb: int = 100,
        jpg_size_kb: int = 150
    ):
        """
        Crea un par HEIC/JPG con fechas de modificación específicas.
        
        Args:
            directory: Directorio donde crear los archivos
            base_name: Nombre base (sin extensión)
            heic_mtime: Fecha de modificación del HEIC
            jpg_mtime: Fecha de modificación del JPG
            heic_size_kb: Tamaño del HEIC en KB
            jpg_size_kb: Tamaño del JPG en KB
        
        Returns:
            Tuple[Path, Path]: (heic_path, jpg_path)
        """
        directory.mkdir(parents=True, exist_ok=True)
        
        # Crear archivos HEIC y JPG con tamaños aproximados
        heic_path = directory / f"{base_name}.heic"
        jpg_path = directory / f"{base_name}.jpg"
        
        # Usar imágenes reales de diferentes tamaños
        heic_img_size = (50, 50) if heic_size_kb < 100 else (100, 100)
        jpg_img_size = (75, 75) if jpg_size_kb < 150 else (150, 150)
        
        create_test_image(heic_path, size=heic_img_size, color='blue', format='JPEG')
        create_test_image(jpg_path, size=jpg_img_size, color='blue', format='JPEG')
        
        # Ajustar fechas de modificación si se especificaron
        if heic_mtime:
            mtime_timestamp = heic_mtime.timestamp()
            os.utime(heic_path, (mtime_timestamp, mtime_timestamp))
        
        if jpg_mtime:
            mtime_timestamp = jpg_mtime.timestamp()
            os.utime(jpg_path, (mtime_timestamp, mtime_timestamp))
        
        return heic_path, jpg_path
    
    return _create_pair


# ==================== TESTS BÁSICOS ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverBasics:
    """Tests básicos de inicialización y configuración."""
    
    def test_initialization(self, heic_remover):
        """Test de inicialización correcta del servicio."""
        assert heic_remover is not None
        assert heic_remover.heic_extensions == {'.heic', '.heif'}
        assert heic_remover.jpg_extensions == {'.jpg', '.jpeg'}
        assert Config.MAX_TIME_DIFFERENCE_SECONDS == 60
        assert heic_remover.stats['heic_files_found'] == 0
        assert heic_remover.stats['jpg_files_found'] == 0
    
    def test_empty_directory(self, heic_remover, temp_dir):
        """Test de análisis en directorio vacío."""
        result = heic_remover.analyze(temp_dir)
        
        assert isinstance(result, HeicAnalysisResult)
        assert result.total_files == 0
        assert result.total_pairs == 0
        assert len(result.duplicate_pairs) == 0
        assert result.heic_files == 0
        assert result.jpg_files == 0
    
    def test_directory_without_duplicates(self, heic_remover, temp_dir, create_test_image):
        """Test con archivos HEIC y JPG pero sin duplicados (nombres diferentes)."""
        # Crear archivos con nombres diferentes
        create_test_image(temp_dir / "photo1.heic", format='JPEG')
        create_test_image(temp_dir / "photo2.jpg", format='JPEG')
        create_test_image(temp_dir / "image3.heic", format='JPEG')
        
        result = heic_remover.analyze(temp_dir)
        
        assert result.heic_files == 2
        assert result.jpg_files == 1
        assert result.total_pairs == 0  # Sin duplicados porque nombres no coinciden
        assert len(result.orphan_heic) == 2
        assert len(result.orphan_jpg) == 1


# ==================== TESTS DE DUPLICADOS SIMPLES ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverSimpleDuplicates:
    """Tests de detección de duplicados en casos simples."""
    
    def test_single_duplicate_pair(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con un único par de duplicados con fechas similares."""
        now = datetime.now()
        create_heic_jpg_pair(temp_dir, "photo1", heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 1
        assert result.heic_files == 1
        assert result.jpg_files == 1
        assert len(result.duplicate_pairs) == 1
        
        pair = result.duplicate_pairs[0]
        assert pair.base_name == "photo1"
        assert pair.heic_path.name == "photo1.heic"
        assert pair.jpg_path.name == "photo1.jpg"
        assert pair.directory == temp_dir
    
    def test_multiple_duplicate_pairs_same_directory(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con múltiples pares de duplicados en el mismo directorio."""
        now = datetime.now()
        
        create_heic_jpg_pair(temp_dir, "photo1", heic_mtime=now, jpg_mtime=now)
        create_heic_jpg_pair(temp_dir, "photo2", heic_mtime=now, jpg_mtime=now)
        create_heic_jpg_pair(temp_dir, "photo3", heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 3
        assert result.heic_files == 3
        assert result.jpg_files == 3
        assert len(result.duplicate_pairs) == 3
        
        base_names = {pair.base_name for pair in result.duplicate_pairs}
        assert base_names == {"photo1", "photo2", "photo3"}
    
    def test_duplicate_with_heif_extension(self, heic_remover, temp_dir, create_test_image):
        """Test que detecta archivos .heif además de .heic."""
        now = datetime.now()
        
        heif_path = temp_dir / "photo.heif"
        jpg_path = temp_dir / "photo.jpg"
        
        create_test_image(heif_path, format='JPEG')
        create_test_image(jpg_path, format='JPEG')
        
        # Establecer fechas similares
        mtime = now.timestamp()
        os.utime(heif_path, (mtime, mtime))
        os.utime(jpg_path, (mtime, mtime))
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 1
        assert result.heic_files == 1  # Cuenta .heif como HEIC
        assert result.jpg_files == 1
    
    def test_duplicate_with_jpeg_extension(self, heic_remover, temp_dir, create_test_image):
        """Test que detecta archivos .jpeg además de .jpg."""
        now = datetime.now()
        
        heic_path = temp_dir / "photo.heic"
        jpeg_path = temp_dir / "photo.jpeg"
        
        create_test_image(heic_path, format='JPEG')
        create_test_image(jpeg_path, format='JPEG')
        
        # Establecer fechas similares
        mtime = now.timestamp()
        os.utime(heic_path, (mtime, mtime))
        os.utime(jpeg_path, (mtime, mtime))
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 1
        assert result.jpg_files == 1  # Cuenta .jpeg como JPG


# ==================== TESTS DE VALIDACIÓN TEMPORAL ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverTimeValidation:
    """Tests de validación de diferencias temporales entre archivos."""
    
    def test_duplicate_within_time_threshold(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con duplicado dentro del umbral de tiempo (30 segundos)."""
        base_time = datetime(2024, 1, 15, 12, 0, 0)
        heic_time = base_time
        jpg_time = base_time + timedelta(seconds=30)
        
        create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=heic_time, jpg_mtime=jpg_time)
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 1
        pair = result.duplicate_pairs[0]
        assert pair.time_difference.total_seconds() == 30
    
    def test_duplicate_at_time_threshold_boundary(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con duplicado exactamente en el límite del umbral (60 segundos)."""
        base_time = datetime(2024, 1, 15, 12, 0, 0)
        heic_time = base_time
        jpg_time = base_time + timedelta(seconds=60)
        
        create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=heic_time, jpg_mtime=jpg_time)
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        # En el límite exacto debe ser aceptado
        assert result.total_pairs == 1
    
    def test_duplicate_exceeds_time_threshold(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con archivos que exceden el umbral temporal (>60 segundos)."""
        base_time = datetime(2024, 1, 15, 12, 0, 0)
        heic_time = base_time
        jpg_time = base_time + timedelta(seconds=120)  # 2 minutos
        
        create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=heic_time, jpg_mtime=jpg_time)
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        # NO debe ser detectado como duplicado
        assert result.total_pairs == 0
        assert heic_remover.stats['rejected_by_time_diff'] == 1
        assert len(result.orphan_heic) == 1
        assert len(result.orphan_jpg) == 1
    
    def test_duplicate_with_days_difference(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con archivos con diferencia de días (claramente no duplicados)."""
        base_time = datetime(2024, 1, 15, 12, 0, 0)
        heic_time = base_time
        jpg_time = base_time + timedelta(days=5)
        
        create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=heic_time, jpg_mtime=jpg_time)
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 0
        assert heic_remover.stats['rejected_by_time_diff'] == 1
    
    def test_validation_disabled_ignores_time_difference(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con validación desactivada - debe aceptar archivos con cualquier diferencia temporal."""
        base_time = datetime(2024, 1, 15, 12, 0, 0)
        heic_time = base_time
        jpg_time = base_time + timedelta(days=30)  # 30 días de diferencia
        
        create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=heic_time, jpg_mtime=jpg_time)
        
        result = heic_remover.analyze(temp_dir, validate_dates=False)
        
        # Con validación desactivada, DEBE detectar el duplicado
        assert result.total_pairs == 1
        assert heic_remover.stats['rejected_by_time_diff'] == 0
    
    def test_mixed_validation_results(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con múltiples pares: algunos válidos y otros rechazados por tiempo."""
        base_time = datetime(2024, 1, 15, 12, 0, 0)
        
        # Par 1: Válido (30 segundos)
        create_heic_jpg_pair(
            temp_dir, "photo1",
            heic_mtime=base_time,
            jpg_mtime=base_time + timedelta(seconds=30)
        )
        
        # Par 2: Inválido (2 minutos)
        create_heic_jpg_pair(
            temp_dir, "photo2",
            heic_mtime=base_time,
            jpg_mtime=base_time + timedelta(seconds=120)
        )
        
        # Par 3: Válido (10 segundos)
        create_heic_jpg_pair(
            temp_dir, "photo3",
            heic_mtime=base_time,
            jpg_mtime=base_time + timedelta(seconds=10)
        )
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 2  # Solo photo1 y photo3
        assert heic_remover.stats['rejected_by_time_diff'] == 1
        assert len(result.orphan_heic) == 1  # photo2.heic
        assert len(result.orphan_jpg) == 1  # photo2.jpg


# ==================== TESTS DE DIRECTORIOS DIFERENTES ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverDifferentDirectories:
    """
    Tests críticos: archivos con mismo nombre en directorios diferentes
    NO deben ser marcados como duplicados.
    """
    
    def test_same_name_different_directories_not_duplicates(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """
        Test CRÍTICO: archivos con mismo nombre en directorios diferentes
        NO deben considerarse duplicados.
        """
        now = datetime.now()
        
        dir1 = temp_dir / "folder1"
        dir2 = temp_dir / "folder2"
        
        # Crear par "image-outline" en ambos directorios
        create_heic_jpg_pair(dir1, "image-outline", heic_mtime=now, jpg_mtime=now)
        create_heic_jpg_pair(dir2, "image-outline", heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, recursive=True, validate_dates=True)
        
        # Debe encontrar 2 pares separados (uno por directorio)
        assert result.total_pairs == 2
        assert result.heic_files == 2
        assert result.jpg_files == 2
        
        # Verificar que cada par está en su propio directorio
        directories = {pair.directory for pair in result.duplicate_pairs}
        assert len(directories) == 2
        assert dir1 in directories
        assert dir2 in directories
    
    def test_nested_directories_separate_pairs(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con directorios anidados - cada nivel tiene sus propios pares."""
        now = datetime.now()
        
        root = temp_dir
        level1 = temp_dir / "level1"
        level2 = temp_dir / "level1" / "level2"
        
        # Mismo nombre "image" en cada nivel
        create_heic_jpg_pair(root, "image", heic_mtime=now, jpg_mtime=now)
        create_heic_jpg_pair(level1, "image", heic_mtime=now, jpg_mtime=now)
        create_heic_jpg_pair(level2, "image", heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, recursive=True, validate_dates=True)
        
        # Debe encontrar 3 pares independientes
        assert result.total_pairs == 3
        
        directories = {pair.directory for pair in result.duplicate_pairs}
        assert len(directories) == 3
        assert root in directories
        assert level1 in directories
        assert level2 in directories
    
    def test_cross_directory_not_matched(self, heic_remover, temp_dir, create_test_image):
        """
        Test que verifica que HEIC en un directorio y JPG en otro
        NO se emparejan aunque tengan el mismo nombre.
        """
        now = datetime.now()
        
        dir1 = temp_dir / "dir1"
        dir2 = temp_dir / "dir2"
        dir1.mkdir(parents=True)
        dir2.mkdir(parents=True)
        
        # HEIC en dir1, JPG en dir2
        heic_path = dir1 / "photo.heic"
        jpg_path = dir2 / "photo.jpg"
        
        create_test_image(heic_path, format='JPEG')
        create_test_image(jpg_path, format='JPEG')
        
        mtime = now.timestamp()
        os.utime(heic_path, (mtime, mtime))
        os.utime(jpg_path, (mtime, mtime))
        
        result = heic_remover.analyze(temp_dir, recursive=True, validate_dates=True)
        
        # NO debe encontrar duplicados
        assert result.total_pairs == 0
        assert result.heic_files == 1
        assert result.jpg_files == 1
        assert len(result.orphan_heic) == 1
        assert len(result.orphan_jpg) == 1


# ==================== TESTS DE ARCHIVOS HUÉRFANOS ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverOrphans:
    """Tests de detección de archivos huérfanos (sin pareja)."""
    
    def test_orphan_heic_files(self, heic_remover, temp_dir, create_test_image):
        """Test con archivos HEIC sin su correspondiente JPG."""
        create_test_image(temp_dir / "photo1.heic", format='JPEG')
        create_test_image(temp_dir / "photo2.heic", format='JPEG')
        create_test_image(temp_dir / "photo3.heic", format='JPEG')
        
        result = heic_remover.analyze(temp_dir)
        
        assert result.heic_files == 3
        assert result.jpg_files == 0
        assert result.total_pairs == 0
        assert len(result.orphan_heic) == 3
        assert len(result.orphan_jpg) == 0
    
    def test_orphan_jpg_files(self, heic_remover, temp_dir, create_test_image):
        """Test con archivos JPG sin su correspondiente HEIC."""
        create_test_image(temp_dir / "photo1.jpg", format='JPEG')
        create_test_image(temp_dir / "photo2.jpg", format='JPEG')
        
        result = heic_remover.analyze(temp_dir)
        
        assert result.heic_files == 0
        assert result.jpg_files == 2
        assert result.total_pairs == 0
        assert len(result.orphan_heic) == 0
        assert len(result.orphan_jpg) == 2
    
    def test_mixed_orphans_and_pairs(self, heic_remover, temp_dir, create_heic_jpg_pair, create_test_image):
        """Test con mezcla de pares válidos y archivos huérfanos."""
        now = datetime.now()
        
        # Par válido
        create_heic_jpg_pair(temp_dir, "photo1", heic_mtime=now, jpg_mtime=now)
        
        # Huérfanos HEIC
        create_test_image(temp_dir / "orphan1.heic", format='JPEG')
        create_test_image(temp_dir / "orphan2.heic", format='JPEG')
        
        # Huérfano JPG
        create_test_image(temp_dir / "lonely.jpg", format='JPEG')
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 1
        assert result.heic_files == 3
        assert result.jpg_files == 2
        assert len(result.orphan_heic) == 2
        assert len(result.orphan_jpg) == 1


# ==================== TESTS DE BÚSQUEDA RECURSIVA ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverRecursiveSearch:
    """Tests de búsqueda recursiva en subdirectorios."""
    
    def test_recursive_search_enabled(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con búsqueda recursiva activada."""
        now = datetime.now()
        
        # Crear estructura de directorios
        (temp_dir / "sub1").mkdir()
        (temp_dir / "sub2").mkdir()
        (temp_dir / "sub1" / "nested").mkdir()
        
        # Pares en diferentes niveles
        create_heic_jpg_pair(temp_dir, "root", heic_mtime=now, jpg_mtime=now)
        create_heic_jpg_pair(temp_dir / "sub1", "sub1", heic_mtime=now, jpg_mtime=now)
        create_heic_jpg_pair(temp_dir / "sub2", "sub2", heic_mtime=now, jpg_mtime=now)
        create_heic_jpg_pair(temp_dir / "sub1" / "nested", "nested", heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, recursive=True, validate_dates=True)
        
        assert result.total_pairs == 4
        assert result.heic_files == 4
        assert result.jpg_files == 4
    
    def test_recursive_search_disabled(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con búsqueda recursiva desactivada - solo nivel raíz."""
        now = datetime.now()
        
        # Par en raíz
        create_heic_jpg_pair(temp_dir, "root", heic_mtime=now, jpg_mtime=now)
        
        # Pares en subdirectorios (no deben ser encontrados)
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        create_heic_jpg_pair(subdir, "sub", heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, recursive=False, validate_dates=True)
        
        # Solo debe encontrar el par de la raíz
        assert result.total_pairs == 1
        assert result.heic_files == 1
        assert result.jpg_files == 1
        assert result.duplicate_pairs[0].base_name == "root"


# ==================== TESTS DE ESTADÍSTICAS ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverStatistics:
    """Tests de cálculo de estadísticas y métricas."""
    
    def test_potential_savings_calculation(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test de cálculo de ahorro potencial."""
        now = datetime.now()
        
        # Crear pares con tamaños conocidos
        create_heic_jpg_pair(temp_dir, "photo1", heic_mtime=now, jpg_mtime=now, heic_size_kb=100, jpg_size_kb=150)
        create_heic_jpg_pair(temp_dir, "photo2", heic_mtime=now, jpg_mtime=now, heic_size_kb=200, jpg_size_kb=300)
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 2
        # El ahorro viene de los tamaños reales de los archivos creados
        assert result.potential_savings_keep_jpg > 0
        assert result.potential_savings_keep_heic > 0
    
    def test_by_directory_statistics(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test de estadísticas agrupadas por directorio."""
        now = datetime.now()
        
        dir1 = temp_dir / "dir1"
        dir2 = temp_dir / "dir2"
        
        create_heic_jpg_pair(dir1, "photo1", heic_mtime=now, jpg_mtime=now)
        create_heic_jpg_pair(dir1, "photo2", heic_mtime=now, jpg_mtime=now)
        create_heic_jpg_pair(dir2, "photo3", heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, recursive=True, validate_dates=True)
        
        assert str(dir1) in result.by_directory
        assert str(dir2) in result.by_directory
        assert result.by_directory[str(dir1)] == 2
        assert result.by_directory[str(dir2)] == 1


# ==================== TESTS DE ELIMINACIÓN (KEEP JPG) ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverDeletionKeepJPG:
    """Tests de eliminación de archivos manteniendo JPG."""
    
    def test_delete_heic_keep_jpg(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test de eliminación básica: eliminar HEIC, mantener JPG."""
        now = datetime.now()
        heic_path, jpg_path = create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=now, jpg_mtime=now)
        
        # Analizar primero
        analysis = heic_remover.analyze(temp_dir, validate_dates=True)
        assert len(analysis.duplicate_pairs) == 1
        
        # Ejecutar eliminación sin backup
        result = heic_remover.execute(
            duplicate_pairs=analysis.duplicate_pairs,
            keep_format='file-jpg-box',
            create_backup=False,
            dry_run=False
        )
        
        assert result.success
        assert result.files_deleted == 1
        assert not heic_path.exists()  # HEIC eliminado
        assert jpg_path.exists()  # JPG preservado
        assert result.space_freed > 0
    
    def test_delete_multiple_heic_keep_jpg(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test de eliminación múltiple: varios pares HEIC/JPG."""
        now = datetime.now()
        
        pairs = []
        for i in range(5):
            heic, jpg = create_heic_jpg_pair(temp_dir, f"photo{i}", heic_mtime=now, jpg_mtime=now)
            pairs.append((heic, jpg))
        
        analysis = heic_remover.analyze(temp_dir, validate_dates=True)
        assert len(analysis.duplicate_pairs) == 5
        
        result = heic_remover.execute(
            duplicate_pairs=analysis.duplicate_pairs,
            keep_format='file-jpg-box',
            create_backup=False,
            dry_run=False
        )
        
        assert result.success
        assert result.files_deleted == 5
        
        # Verificar que todos los HEIC fueron eliminados y JPG preservados
        for heic, jpg in pairs:
            assert not heic.exists()
            assert jpg.exists()


# ==================== TESTS DE ELIMINACIÓN (KEEP HEIC) ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverDeletionKeepHEIC:
    """Tests de eliminación de archivos manteniendo HEIC."""
    
    def test_delete_jpg_keep_heic(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test de eliminación: eliminar JPG, mantener HEIC."""
        now = datetime.now()
        heic_path, jpg_path = create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=now, jpg_mtime=now)
        
        analysis = heic_remover.analyze(temp_dir, validate_dates=True)
        
        result = heic_remover.execute(
            duplicate_pairs=analysis.duplicate_pairs,
            keep_format='file-image',
            create_backup=False,
            dry_run=False
        )
        
        assert result.success
        assert result.files_deleted == 1
        assert heic_path.exists()  # HEIC preservado
        assert not jpg_path.exists()  # JPG eliminado
        assert result.format_kept == 'file-image'
    
    def test_delete_multiple_jpg_keep_heic(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test de eliminación múltiple manteniendo HEIC."""
        now = datetime.now()
        
        pairs = []
        for i in range(3):
            heic, jpg = create_heic_jpg_pair(temp_dir, f"photo{i}", heic_mtime=now, jpg_mtime=now)
            pairs.append((heic, jpg))
        
        analysis = heic_remover.analyze(temp_dir, validate_dates=True)
        
        result = heic_remover.execute(
            duplicate_pairs=analysis.duplicate_pairs,
            keep_format='file-image',
            create_backup=False,
            dry_run=False
        )
        
        assert result.success
        assert result.files_deleted == 3
        
        for heic, jpg in pairs:
            assert heic.exists()
            assert not jpg.exists()


# ==================== TESTS DE DRY RUN ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverDryRun:
    """Tests de modo simulación (dry run)."""
    
    def test_dry_run_does_not_delete(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test que dry run no elimina archivos realmente."""
        now = datetime.now()
        heic_path, jpg_path = create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=now, jpg_mtime=now)
        
        analysis = heic_remover.analyze(temp_dir, validate_dates=True)
        
        result = heic_remover.execute(
            duplicate_pairs=analysis.duplicate_pairs,
            keep_format='file-jpg-box',
            create_backup=False,
            dry_run=True
        )
        
        assert result.success
        assert result.dry_run
        assert result.simulated_files_deleted == 1
        assert result.files_deleted == 0
        
        # Ambos archivos deben seguir existiendo
        assert heic_path.exists()
        assert jpg_path.exists()
    
    def test_dry_run_calculates_space_freed(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test que dry run calcula correctamente el espacio que se liberaría."""
        now = datetime.now()
        create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=now, jpg_mtime=now, heic_size_kb=100)
        
        analysis = heic_remover.analyze(temp_dir, validate_dates=True)
        
        result = heic_remover.execute(
            duplicate_pairs=analysis.duplicate_pairs,
            keep_format='file-jpg-box',
            create_backup=False,
            dry_run=True
        )
        
        assert result.simulated_space_freed > 0
        assert result.space_freed == 0


# ==================== TESTS DE BACKUP ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverBackup:
    """Tests de creación de backups antes de eliminación."""
    
    def test_backup_created_when_enabled(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test que se crea backup cuando está habilitado."""
        now = datetime.now()
        heic_path, jpg_path = create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=now, jpg_mtime=now)
        
        analysis = heic_remover.analyze(temp_dir, validate_dates=True)
        
        result = heic_remover.execute(
            duplicate_pairs=analysis.duplicate_pairs,
            keep_format='file-jpg-box',
            create_backup=True,
            dry_run=False
        )
        
        assert result.success
        assert result.backup_path is not None
        
        backup_dir = Path(result.backup_path)
        assert backup_dir.exists()
        assert backup_dir.is_dir()
    
    def test_no_backup_when_disabled(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test que no se crea backup cuando está deshabilitado."""
        now = datetime.now()
        create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=now, jpg_mtime=now)
        
        analysis = heic_remover.analyze(temp_dir, validate_dates=True)
        
        result = heic_remover.execute(
            duplicate_pairs=analysis.duplicate_pairs,
            keep_format='file-jpg-box',
            create_backup=False,
            dry_run=False
        )
        
        assert result.success
        assert result.backup_path is None
    
    def test_no_backup_in_dry_run(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test que no se crea backup en modo dry run."""
        now = datetime.now()
        create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=now, jpg_mtime=now)
        
        analysis = heic_remover.analyze(temp_dir, validate_dates=True)
        
        result = heic_remover.execute(
            duplicate_pairs=analysis.duplicate_pairs,
            keep_format='file-jpg-box',
            create_backup=True,
            dry_run=True
        )
        
        assert result.dry_run
        assert result.backup_path is None


# ==================== TESTS DE CASOS EDGE ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverEdgeCases:
    """Tests de casos especiales y situaciones límite."""
    
    def test_empty_duplicate_pairs_list(self, heic_remover):
        """Test de ejecución con lista vacía de duplicados."""
        result = heic_remover.execute(
            duplicate_pairs=[],
            keep_format='file-jpg-box',
            create_backup=False,
            dry_run=False
        )
        
        assert result.success
        assert result.files_deleted == 0
        assert "No hay archivos" in result.message
    
    def test_case_insensitive_extensions(self, heic_remover, temp_dir, create_test_image):
        """Test que las extensiones no son case-sensitive."""
        now = datetime.now()
        
        # Crear con extensiones en mayúsculas
        heic_path = temp_dir / "photo.HEIC"
        jpg_path = temp_dir / "photo.JPG"
        
        create_test_image(heic_path, format='JPEG')
        create_test_image(jpg_path, format='JPEG')
        
        mtime = now.timestamp()
        os.utime(heic_path, (mtime, mtime))
        os.utime(jpg_path, (mtime, mtime))
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 1
    
    def test_files_with_spaces_in_name(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con nombres de archivo que contienen espacios."""
        now = datetime.now()
        heic, jpg = create_heic_jpg_pair(temp_dir, "my photo with spaces", heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 1
        assert result.duplicate_pairs[0].base_name == "my photo with spaces"
    
    def test_files_with_special_characters(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con nombres que contienen caracteres especiales."""
        now = datetime.now()
        
        # Nombre con varios caracteres especiales
        special_name = "photo_2024-01-15_#1"
        heic, jpg = create_heic_jpg_pair(temp_dir, special_name, heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        assert result.total_pairs == 1
        assert result.duplicate_pairs[0].base_name == special_name
    
    def test_very_large_directory_structure(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test con estructura de directorios profunda."""
        now = datetime.now()
        
        # Crear estructura profunda
        deep_path = temp_dir
        for i in range(10):
            deep_path = deep_path / f"level{i}"
        
        create_heic_jpg_pair(deep_path, "image-outline", heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, recursive=True, validate_dates=True)
        
        assert result.total_pairs == 1
    
    def test_duplicate_pair_properties(self, temp_dir, create_heic_jpg_pair):
        """Test de propiedades calculadas de DuplicatePair."""
        now = datetime.now()
        heic_path, jpg_path = create_heic_jpg_pair(
            temp_dir, "image-outline",
            heic_mtime=now,
            jpg_mtime=now + timedelta(seconds=30),
            heic_size_kb=100,
            jpg_size_kb=150
        )
        
        heic_size = heic_path.stat().st_size
        jpg_size = jpg_path.stat().st_size
        
        pair = DuplicatePair(
            heic_path=heic_path,
            jpg_path=jpg_path,
            base_name="image-outline",
            heic_size=heic_size,
            jpg_size=jpg_size,
            directory=temp_dir,
            heic_date=now,
            jpg_date=now + timedelta(seconds=30)
        )
        
        assert pair.total_size == heic_size + jpg_size
        assert pair.size_saving_keep_jpg == heic_size
        assert pair.size_saving_keep_heic == jpg_size
        assert pair.time_difference.total_seconds() == 30
    
    def test_nonexistent_file_in_duplicate_pair_raises_error(self, temp_dir):
        """Test que DuplicatePair valida existencia de archivos."""
        fake_heic = temp_dir / "nonexistent.heic"
        fake_jpg = temp_dir / "nonexistent.jpg"
        
        with pytest.raises(ValueError):
            DuplicatePair(
                heic_path=fake_heic,
                jpg_path=fake_jpg,
                base_name="nonexistent",
                heic_size=100,
                jpg_size=150,
                directory=temp_dir
            )
    
    def test_progress_callback_invoked(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test que el callback de progreso se invoca durante el análisis."""
        now = datetime.now()
        
        for i in range(5):
            create_heic_jpg_pair(temp_dir, f"photo{i}", heic_mtime=now, jpg_mtime=now)
        
        progress_calls = []
        
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
            return True  # Continuar
        
        result = heic_remover.analyze(temp_dir, validate_dates=True, progress_callback=progress_callback)
        
        assert result.total_pairs == 5
        assert len(progress_calls) > 0
    
    def test_analysis_can_be_cancelled(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test que el análisis puede ser cancelado mediante callback."""
        now = datetime.now()
        
        for i in range(10):
            create_heic_jpg_pair(temp_dir, f"photo{i}", heic_mtime=now, jpg_mtime=now)
        
        call_count = [0]
        
        def cancel_callback(current, total, message):
            call_count[0] += 1
            # Cancelar después de 3 llamadas
            return call_count[0] < 3
        
        result = heic_remover.analyze(temp_dir, validate_dates=True, progress_callback=cancel_callback)
        
        # El resultado debe estar vacío porque se canceló
        assert result.total_pairs == 0
        assert result.total_files == 0


# ==================== TESTS DE RESULTADOS ====================

@pytest.mark.unit
@pytest.mark.heic
class TestHEICRemoverResults:
    """Tests de los objetos de resultado y sus propiedades."""
    
    def test_analysis_result_structure(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test de estructura completa del resultado de análisis."""
        now = datetime.now()
        create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=now, jpg_mtime=now)
        
        result = heic_remover.analyze(temp_dir, validate_dates=True)
        
        # Verificar todos los campos del resultado
        assert hasattr(result, 'total_files')
        assert hasattr(result, 'duplicate_pairs')
        assert hasattr(result, 'total_pairs')
        assert hasattr(result, 'heic_files')
        assert hasattr(result, 'jpg_files')
        assert hasattr(result, 'total_size')
        assert hasattr(result, 'potential_savings_keep_jpg')
        assert hasattr(result, 'potential_savings_keep_heic')
        assert hasattr(result, 'orphan_heic')
        assert hasattr(result, 'orphan_jpg')
        assert hasattr(result, 'by_directory')
    
    def test_deletion_result_structure(self, heic_remover, temp_dir, create_heic_jpg_pair):
        """Test de estructura completa del resultado de eliminación."""
        now = datetime.now()
        create_heic_jpg_pair(temp_dir, "image-outline", heic_mtime=now, jpg_mtime=now)
        
        analysis = heic_remover.analyze(temp_dir, validate_dates=True)
        result = heic_remover.execute(
            duplicate_pairs=analysis.duplicate_pairs,
            keep_format='file-jpg-box',
            create_backup=False,
            dry_run=False
        )
        
        assert hasattr(result, 'success')
        assert hasattr(result, 'files_deleted')
        assert hasattr(result, 'space_freed')
        assert hasattr(result, 'message')
        assert hasattr(result, 'format_kept')
        assert hasattr(result, 'dry_run')
        assert hasattr(result, 'backup_path')
        assert hasattr(result, 'deleted_files')
        assert hasattr(result, 'errors')
