"""
Tests exhaustivos para el servicio FileOrganizer.

Cubre todos los casos de uso y edge cases:
- Análisis con diferentes tipos de organización (TO_ROOT, BY_MONTH, BY_YEAR, BY_YEAR_MONTH, BY_TYPE, BY_SOURCE)
- Detección de subdirectorios anidados
- Detección de archivos de WhatsApp (patrones y UUIDs)
- Resolución de conflictos de nombres
- Ejecución de movimientos con backup
- Dry run mode
- Limpieza de directorios vacíos
- Casos edge: archivos duplicados, permisos, etc.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from services.file_organizer_service import FileOrganizer, OrganizationType, FileMove
from services.result_types import OrganizationAnalysisResult, OrganizationExecutionResult
from utils.file_utils import is_whatsapp_file
from config import Config
import shutil


# ==================== FIXTURES ====================

@pytest.fixture
def organizer():
    """Crea una instancia de FileOrganizer para tests."""
    return FileOrganizer()


@pytest.fixture
def create_nested_structure(temp_dir, create_test_image):
    """
    Factory fixture para crear estructura de directorios anidados con archivos.
    
    Returns:
        Callable que crea estructura de directorios con archivos
    """
    def _create_structure(subdirs_config=None):
        """
        Crea estructura de directorios anidados con archivos.
        
        Args:
            subdirs_config: Dict con configuración de subdirectorios
                Ejemplo: {
                    'photos/2023': ['img1.jpg', 'img2.jpg'],
                    'photos/2024/vacation': ['photo.jpg'],
                    'WhatsApp Images': ['82DB60A3-002F-4FAE-80FC-96082431D247.jpg']
                }
        
        Returns:
            Tuple[Path, Dict[str, List[Path]]]: (root_dir, archivos_creados)
        """
        if subdirs_config is None:
            subdirs_config = {
                'subdir1': ['photo1.jpg', 'photo2.jpg'],
                'subdir2': ['video1.mp4'],
            }
        
        created_files = {}
        
        for subdir_path, filenames in subdirs_config.items():
            subdir = temp_dir / subdir_path
            subdir.mkdir(parents=True, exist_ok=True)
            
            files = []
            for filename in filenames:
                file_path = subdir / filename
                # Crear imagen o video dummy
                if filename.endswith(('.jpg', '.jpeg', '.png', '.heic')):
                    create_test_image(file_path, size=(100, 100), color='blue')
                else:
                    # Video/archivo dummy
                    file_path.write_bytes(b'dummy video content' * 100)
                files.append(file_path)
            
            created_files[subdir_path] = files
        
        return temp_dir, created_files
    
    return _create_structure


# ==================== TESTS DE DETECCIÓN DE WHATSAPP ====================

@pytest.mark.unit
@pytest.mark.organization
class TestWhatsAppDetection:
    """Tests de detección de archivos de WhatsApp."""
    
    def test_android_pattern_img(self):
        """Test de detección de patrón Android IMG-WA."""
        assert is_whatsapp_file('IMG-20231025-WA0001.jpg') is True
    
    def test_android_pattern_vid(self):
        """Test de detección de patrón Android VID-WA."""
        assert is_whatsapp_file('VID-20231025-WA0123.mp4') is True
    
    def test_iphone_uuid_pattern(self):
        """Test de detección de patrón UUID de iPhone."""
        assert is_whatsapp_file('82DB60A3-002F-4FAE-80FC-96082431D247.jpg') is True
    
    def test_iphone_uuid_lowercase(self):
        """Test de detección de UUID en minúsculas."""
        assert is_whatsapp_file('a1b2c3d4-5678-90ab-cdef-123456789012.heic') is True
    
    def test_whatsapp_folder_path(self):
        """Test de detección por ruta que contiene 'whatsapp'."""
        assert is_whatsapp_file(
            'photo.jpg',
            Path('/photos/WhatsApp Images/photo.jpg')
        ) is True
    
    def test_normal_file_not_detected(self):
        """Test que archivos normales no se detectan como WhatsApp."""
        assert is_whatsapp_file('vacation.jpg') is False
        assert is_whatsapp_file('IMG_1234.jpg') is False
    
    def test_uuid_wrong_extension_not_detected(self):
        """Test que UUIDs con extensión incorrecta no se detectan."""
        assert is_whatsapp_file('82DB60A3-002F-4FAE-80FC-96082431D247.txt') is False


# ==================== TESTS DE ANÁLISIS ====================

@pytest.mark.unit
@pytest.mark.organization
class TestFileOrganizerAnalysis:
    """Tests de análisis de estructura de directorios."""
    
    def test_analyze_simple_structure_to_root(self, organizer, create_nested_structure):
        """Test de análisis básico con organización TO_ROOT."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg', 'photo2.jpg'],
            'videos': ['video1.mp4']
        })
        
        result = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        
        assert result.success is True
        assert result.total_files_to_move == 3
        assert len(result.subdirectories) == 2
        assert len(result.move_plan) == 3
    
    def test_analyze_nested_subdirectories(self, organizer, create_nested_structure):
        """Test que detecta subdirectorios anidados en múltiples niveles."""
        root_dir, files = create_nested_structure({
            'level1': ['file1.jpg'],
            'level1/level2': ['file2.jpg'],
            'level1/level2/level3': ['file3.jpg']
        })
        
        result = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        
        assert result.success is True
        assert result.total_files_to_move == 3
        # Debe detectar 3 "subdirectorios" (rutas relativas diferentes)
        assert len(result.subdirectories) == 3
        assert 'level1' in result.subdirectories
        assert 'level1/level2' in result.subdirectories
        assert 'level1/level2/level3' in result.subdirectories
    
    def test_analyze_by_month(self, organizer, create_nested_structure):
        """Test de análisis con organización BY_MONTH."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg', 'photo2.jpg']
        })
        
        result = organizer.analyze(root_dir, OrganizationType.BY_MONTH)
        
        assert result.success is True
        assert result.total_files_to_move >= 2  # Puede incluir archivos de raíz
        assert len(result.folders_to_create) > 0  # Debe crear carpetas YYYY_MM
    
    def test_analyze_by_source_separate(self, organizer, create_nested_structure):
        """Test de análisis con separación por fuente (BY_SOURCE)."""
        root_dir, files = create_nested_structure({
            'photos': ['IMG-20231025-WA0001.jpg', 'normal_photo.jpg'],
            'WhatsApp Images': ['82DB60A3-002F-4FAE-80FC-96082431D247.jpg']
        })
        
        result = organizer.analyze(root_dir, OrganizationType.BY_SOURCE)
        
        assert result.success is True
        assert result.total_files_to_move == 3
        
        # Verificar que hay archivos que van a WhatsApp
        whatsapp_moves = [m for m in result.move_plan if m.target_folder == 'WhatsApp']
        assert len(whatsapp_moves) >= 2  # Al menos los 2 archivos de WhatsApp
    
    def test_analyze_empty_directory(self, organizer, temp_dir):
        """Test de análisis de directorio vacío."""
        result = organizer.analyze(temp_dir, OrganizationType.TO_ROOT)
        
        assert result.success is True
        assert result.total_files_to_move == 0
        assert len(result.subdirectories) == 0
        assert len(result.move_plan) == 0
    
    def test_analyze_no_subdirectories(self, organizer, temp_dir, create_test_image):
        """Test con archivos solo en raíz (sin subdirectorios)."""
        # Crear archivos directamente en raíz
        create_test_image(temp_dir / 'photo1.jpg')
        create_test_image(temp_dir / 'photo2.jpg')
        
        result = organizer.analyze(temp_dir, OrganizationType.TO_ROOT)
        
        assert result.success is True
        assert result.total_files_to_move == 0  # TO_ROOT no mueve archivos ya en raíz
        assert len(result.subdirectories) == 0


# ==================== TESTS DE NUEVOS TIPOS DE ORGANIZACIÓN ====================

@pytest.mark.unit
@pytest.mark.organization
class TestNewOrganizationTypes:
    """Tests para los nuevos tipos de organización (BY_YEAR, BY_YEAR_MONTH, BY_TYPE, BY_SOURCE)."""
    
    def test_analyze_by_year(self, organizer, create_nested_structure):
        """Test de análisis con organización BY_YEAR."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg', 'photo2.jpg'],
            'videos': ['video1.mp4']
        })
        
        result = organizer.analyze(root_dir, OrganizationType.BY_YEAR)
        
        assert result.success is True
        assert result.total_files_to_move >= 3
        # Debe crear carpetas YYYY
        year_folders = [f for f in result.folders_to_create if len(f) == 4 and f.isdigit()]
        assert len(year_folders) > 0
    
    def test_analyze_by_year_month(self, organizer, create_nested_structure):
        """Test de análisis con organización BY_YEAR_MONTH (jerárquica)."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg', 'photo2.jpg']
        })
        
        result = organizer.analyze(root_dir, OrganizationType.BY_YEAR_MONTH)
        
        assert result.success is True
        assert result.total_files_to_move >= 2
        # Debe crear estructura YYYY/MM
        assert len(result.folders_to_create) > 0
        # Verificar que hay rutas jerárquicas
        hierarchical_folders = [f for f in result.folders_to_create if '/' in f]
        assert len(hierarchical_folders) > 0
    
    def test_analyze_by_type(self, organizer, create_nested_structure):
        """Test de análisis con organización BY_TYPE (Fotos/Videos)."""
        root_dir, files = create_nested_structure({
            'mixed': ['photo1.jpg', 'photo2.png', 'video1.mp4', 'video2.mov']
        })
        
        result = organizer.analyze(root_dir, OrganizationType.BY_TYPE)
        
        assert result.success is True
        assert result.total_files_to_move == 4
        # Debe crear carpetas Fotos y Videos
        assert 'Fotos' in result.folders_to_create
        assert 'Videos' in result.folders_to_create
        
        # Verificar que fotos van a Fotos/ y videos a Videos/
        photo_moves = [m for m in result.move_plan if m.target_folder == 'Fotos']
        video_moves = [m for m in result.move_plan if m.target_folder == 'Videos']
        assert len(photo_moves) >= 2
        assert len(video_moves) >= 2
    
    def test_analyze_by_source_with_multiple_sources(self, organizer, create_nested_structure):
        """Test de BY_SOURCE con múltiples fuentes detectadas."""
        root_dir, files = create_nested_structure({
            'mixed': [
                'IMG-20231025-WA0001.jpg',  # WhatsApp Android
                '82DB60A3-002F-4FAE-80FC-96082431D247.jpg',  # WhatsApp iPhone UUID
                'IMG_1234.jpg',  # iPhone normal
                'PXL_20230101_120000.jpg',  # Android Pixel
                'normal_photo.jpg',  # Unknown
            ]
        })
        
        result = organizer.analyze(root_dir, OrganizationType.BY_SOURCE)
        
        assert result.success is True
        assert result.total_files_to_move == 5
        
        # Verificar que detecta múltiples fuentes
        sources_detected = set(m.target_folder for m in result.move_plan)
        assert 'WhatsApp' in sources_detected
        # Puede detectar iPhone, Android o Unknown dependiendo de metadata
        assert len(sources_detected) >= 2
    
    def test_execute_by_year_creates_year_folders(self, organizer, create_nested_structure):
        """Test que BY_YEAR crea carpetas de año correctamente."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg', 'photo2.jpg']
        })
        
        analysis = organizer.analyze(root_dir, OrganizationType.BY_YEAR)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=False,
            cleanup_empty_dirs=True,
            dry_run=False
        )
        
        assert result.success is True
        assert result.files_moved >= 2
        
        # Verificar que existe al menos una carpeta YYYY
        year_folders = [d for d in root_dir.iterdir() if d.is_dir() and len(d.name) == 4 and d.name.isdigit()]
        assert len(year_folders) > 0
    
    def test_execute_by_year_month_creates_hierarchy(self, organizer, create_nested_structure):
        """Test que BY_YEAR_MONTH crea jerarquía YYYY/MM correctamente."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg', 'photo2.jpg']
        })
        
        analysis = organizer.analyze(root_dir, OrganizationType.BY_YEAR_MONTH)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=False,
            cleanup_empty_dirs=True,
            dry_run=False
        )
        
        assert result.success is True
        assert result.files_moved >= 2
        
        # Verificar que existe estructura YYYY/MM
        year_folders = [d for d in root_dir.iterdir() if d.is_dir() and len(d.name) == 4 and d.name.isdigit()]
        assert len(year_folders) > 0
        
        # Verificar que dentro del año hay carpetas de mes
        for year_folder in year_folders:
            month_folders = [d for d in year_folder.iterdir() if d.is_dir()]
            if len(month_folders) > 0:
                # Verificar formato MM (01-12)
                assert any(d.name.isdigit() and 1 <= int(d.name) <= 12 for d in month_folders)
                break
    
    def test_execute_by_type_separates_media(self, organizer, create_nested_structure):
        """Test que BY_TYPE separa fotos y videos en carpetas diferentes."""
        root_dir, files = create_nested_structure({
            'mixed': ['photo1.jpg', 'video1.mp4']
        })
        
        analysis = organizer.analyze(root_dir, OrganizationType.BY_TYPE)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=False,
            cleanup_empty_dirs=True,
            dry_run=False
        )
        
        assert result.success is True
        assert result.files_moved == 2
        
        # Verificar que existen carpetas Fotos/ y Videos/
        fotos_dir = root_dir / 'Fotos'
        videos_dir = root_dir / 'Videos'
        assert fotos_dir.exists() and fotos_dir.is_dir()
        assert videos_dir.exists() and videos_dir.is_dir()
        
        # Verificar que hay archivos en cada carpeta
        assert len(list(fotos_dir.glob('*'))) > 0
        assert len(list(videos_dir.glob('*'))) > 0
    
    def test_by_source_respects_capitalization(self, organizer, create_nested_structure):
        """Test que BY_SOURCE usa capitalización correcta para carpetas."""
        root_dir, files = create_nested_structure({
            'photos': ['IMG-20231025-WA0001.jpg']
        })
        
        analysis = organizer.analyze(root_dir, OrganizationType.BY_SOURCE)
        
        # Verificar que la carpeta de WhatsApp está capitalizada
        whatsapp_moves = [m for m in analysis.move_plan if 'whatsapp' in m.target_folder.lower()]
        assert len(whatsapp_moves) > 0
        # Debe ser 'WhatsApp', no 'whatsapp'
        assert all(m.target_folder == 'WhatsApp' for m in whatsapp_moves)


# ==================== TESTS DE CONFLICTOS ====================

@pytest.mark.unit
@pytest.mark.organization
class TestFileOrganizerConflicts:
    """Tests de resolución de conflictos de nombres."""
    
    def test_conflict_detection(self, organizer, create_nested_structure, create_test_image, temp_dir):
        """Test de detección de conflictos cuando archivo ya existe en raíz."""
        # Crear archivo en raíz
        create_test_image(temp_dir / 'photo.jpg')
        
        # Crear archivo con mismo nombre en subdirectorio
        subdir = temp_dir / 'subdir'
        subdir.mkdir()
        create_test_image(subdir / 'photo.jpg')
        
        result = organizer.analyze(temp_dir, OrganizationType.TO_ROOT)
        
        assert result.success is True
        conflicts = [m for m in result.move_plan if m.has_conflict]
        assert len(conflicts) > 0
    
    def test_conflict_resolution_with_sequence(self, organizer, temp_dir, create_test_image):
        """Test que conflictos se resuelven con secuencias numéricas."""
        # Crear archivos con mismo nombre en diferentes subdirectorios
        for i in range(3):
            subdir = temp_dir / f'subdir{i}'
            subdir.mkdir()
            create_test_image(subdir / 'photo.jpg')
        
        result = organizer.analyze(temp_dir, OrganizationType.TO_ROOT)
        
        assert result.success is True
        assert len(result.move_plan) == 3
        
        # Verificar que hay nombres con secuencias
        new_names = [m.new_name for m in result.move_plan]
        # Al menos 2 deben tener secuencias (_001, _002, etc.)
        sequenced = [n for n in new_names if '_' in n and n.split('_')[-1].replace('.jpg', '').isdigit()]
        assert len(sequenced) >= 2


# ==================== TESTS DE EJECUCIÓN ====================

@pytest.mark.unit
@pytest.mark.organization
class TestFileOrganizerExecution:
    """Tests de ejecución de movimientos."""
    
    def test_execute_to_root_simple(self, organizer, create_nested_structure):
        """Test de ejecución simple de movimiento a raíz."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg', 'photo2.jpg']
        })
        
        # Analizar
        analysis = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        
        # Ejecutar sin backup
        result = organizer.execute(
            analysis.move_plan,
            create_backup=False,
            cleanup_empty_dirs=False,
            dry_run=False
        )
        
        assert result.success is True
        assert result.files_moved == 2
        
        # Verificar que archivos están en raíz
        assert (root_dir / 'photo1.jpg').exists()
        assert (root_dir / 'photo2.jpg').exists()
        assert not (root_dir / 'photos').exists() or len(list((root_dir / 'photos').iterdir())) == 0
    
    def test_execute_dry_run(self, organizer, create_nested_structure):
        """Test de ejecución en modo simulación (dry run)."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg']
        })
        
        original_photo = root_dir / 'photos' / 'photo1.jpg'
        assert original_photo.exists()
        
        # Analizar y ejecutar en dry run
        analysis = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=False,
            cleanup_empty_dirs=False,
            dry_run=True
        )
        
        assert result.success is True
        assert result.dry_run is True
        assert result.files_moved == 1
        
        # Verificar que archivo NO se movió
        assert original_photo.exists()
        assert not (root_dir / 'photo1.jpg').exists()
    
    def test_execute_with_cleanup(self, organizer, create_nested_structure):
        """Test que limpia directorios vacíos después de mover."""
        root_dir, files = create_nested_structure({
            'empty_after': ['photo.jpg']
        })
        
        # Analizar y ejecutar con cleanup
        analysis = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=False,
            cleanup_empty_dirs=True,
            dry_run=False
        )
        
        assert result.success is True
        assert result.files_moved == 1
        
        # Verificar que directorio vacío fue eliminado
        assert not (root_dir / 'empty_after').exists()
    
    def test_execute_by_month_creates_folders(self, organizer, create_nested_structure):
        """Test que BY_MONTH crea carpetas por mes."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg']
        })
        
        # Analizar y ejecutar
        analysis = organizer.analyze(root_dir, OrganizationType.BY_MONTH)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=False,
            cleanup_empty_dirs=False,
            dry_run=False
        )
        
        assert result.success is True
        assert result.files_moved >= 1
        
        # Verificar que se creó al menos una carpeta YYYY_MM
        month_folders = [d for d in root_dir.iterdir() if d.is_dir() and '_' in d.name]
        assert len(month_folders) > 0
    
    def test_execute_by_source_creates_whatsapp_folder(self, organizer, create_nested_structure):
        """Test que BY_SOURCE crea carpeta WhatsApp."""
        root_dir, files = create_nested_structure({
            'photos': ['IMG-20231025-WA0001.jpg', 'normal.jpg']
        })
        
        # Analizar y ejecutar
        analysis = organizer.analyze(root_dir, OrganizationType.BY_SOURCE)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=False,
            cleanup_empty_dirs=False,
            dry_run=False
        )
        
        assert result.success is True
        
        # Verificar que carpeta WhatsApp existe
        whatsapp_folder = root_dir / 'WhatsApp'
        assert whatsapp_folder.exists()
        
        # Verificar que archivo WhatsApp está en su carpeta
        assert (whatsapp_folder / 'IMG-20231025-WA0001.jpg').exists()
        
        # Verificar que archivo normal está en carpeta Unknown o similar
        # (dependiendo de la detección de fuente)
        assert (root_dir / 'Unknown' / 'normal.jpg').exists() or any(
            (root_dir / folder / 'normal.jpg').exists() 
            for folder in ['Camera', 'iPhone', 'Android', 'Unknown']
        )


# ==================== TESTS DE EDGE CASES ====================

@pytest.mark.unit
@pytest.mark.organization
class TestFileOrganizerEdgeCases:
    """Tests de casos edge y situaciones especiales."""
    
    def test_analyze_with_unsupported_files(self, organizer, temp_dir):
        """Test que ignora archivos no soportados."""
        subdir = temp_dir / 'subdir'
        subdir.mkdir()
        
        # Crear archivos soportados y no soportados
        (subdir / 'photo.jpg').write_bytes(b'fake image')
        (subdir / 'document.txt').write_text('not supported')
        (subdir / 'script.py').write_text('# python code')
        
        result = organizer.analyze(temp_dir, OrganizationType.TO_ROOT)
        
        assert result.success is True
        assert result.total_files_to_move == 1  # Solo la imagen
    
    def test_analyze_with_mixed_whatsapp_and_normal(self, organizer, create_nested_structure):
        """Test con mezcla de archivos WhatsApp y normales usando BY_SOURCE."""
        root_dir, files = create_nested_structure({
            'photos': [
                'IMG-20231025-WA0001.jpg',  # WhatsApp Android
                '82DB60A3-002F-4FAE-80FC-96082431D247.jpg',  # WhatsApp iPhone UUID
                'vacation.jpg',  # Normal
                'IMG_1234.jpg'  # Normal (no WhatsApp)
            ]
        })
        
        result = organizer.analyze(root_dir, OrganizationType.BY_SOURCE)
        
        assert result.success is True
        assert result.total_files_to_move == 4
        
        # Verificar clasificación
        whatsapp_moves = [m for m in result.move_plan if m.target_folder == 'WhatsApp']
        non_whatsapp_moves = [m for m in result.move_plan if m.target_folder != 'WhatsApp']
        
        assert len(whatsapp_moves) == 2  # Los 2 de WhatsApp
        assert len(non_whatsapp_moves) == 2  # Los 2 normales (irán a Unknown, iPhone, etc.)
    
    def test_execute_with_nonexistent_file(self, organizer, temp_dir, create_test_image):
        """Test que maneja archivos que desaparecen durante ejecución."""
        # Crear archivo temporal en subdirectorio
        subdir = temp_dir / 'subdir'
        subdir.mkdir()
        source_file = subdir / 'photo.jpg'
        create_test_image(source_file)
        
        # Crear FileMove válido
        fake_move = FileMove(
            source_path=source_file,
            target_path=temp_dir / 'photo.jpg',
            original_name='photo.jpg',
            new_name='photo.jpg',
            subdirectory='subdir',
            file_type='Fotos',
            size=source_file.stat().st_size,
            has_conflict=False
        )
        
        # Eliminar archivo después de crear FileMove
        source_file.unlink()
        
        result = organizer.execute(
            [fake_move],
            create_backup=False,
            cleanup_empty_dirs=False,
            dry_run=False
        )
        
        # Debe completarse pero con errores
        assert len(result.errors) > 0
    
    def test_deeply_nested_structure(self, organizer, create_nested_structure):
        """Test con estructura muy anidada (5+ niveles)."""
        root_dir, files = create_nested_structure({
            'a/b/c/d/e': ['deep_file.jpg']
        })
        
        result = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        
        assert result.success is True
        assert result.total_files_to_move == 1
        assert 'a/b/c/d/e' in result.subdirectories


# ==================== TESTS DE MÉTRICAS ====================

@pytest.mark.unit
@pytest.mark.organization
class TestFileOrganizerMetrics:
    """Tests de métricas y estadísticas."""
    
    def test_analysis_result_metrics(self, organizer, create_nested_structure):
        """Test que métricas de análisis son correctas."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg', 'photo2.jpg'],
            'videos': ['video1.mp4']
        })
        
        result = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        
        assert result.total_files_to_move == 3
        assert result.total_size_to_move > 0
        assert len(result.files_by_type) >= 1  # Al menos un tipo
        assert result.organization_type == OrganizationType.TO_ROOT.value
    
    def test_execution_result_metrics(self, organizer, create_nested_structure):
        """Test que métricas de ejecución son correctas."""
        root_dir, files = create_nested_structure({
            'photos': ['photo1.jpg', 'photo2.jpg']
        })
        
        analysis = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=False,
            cleanup_empty_dirs=True,
            dry_run=False
        )
        
        assert result.files_moved == 2
        assert result.empty_directories_removed >= 1
        assert len(result.moved_files) == 2


@pytest.mark.unit
@pytest.mark.organization
class TestFileOrganizerBackup:
    """Tests de creación de backups en file organizer."""
    
    def test_backup_created_when_enabled(self, organizer, create_nested_structure):
        """Test que se crea backup cuando está habilitado."""
        root_dir, files = create_nested_structure({
            'subdir': ['photo1.jpg', 'photo2.jpg']
        })
        
        analysis = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=True,
            cleanup_empty_dirs=False,
            dry_run=False
        )
        
        assert result.success is True
        assert result.backup_path is not None
        assert Path(result.backup_path).exists()
        
        # Verificar que el backup contiene los archivos
        backup_files = list(Path(result.backup_path).rglob('*.jpg'))
        assert len(backup_files) == 2
    
    def test_no_backup_when_disabled(self, organizer, create_nested_structure):
        """Test que NO se crea backup cuando está deshabilitado."""
        root_dir, files = create_nested_structure({
            'subdir': ['photo1.jpg']
        })
        
        analysis = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=False,
            cleanup_empty_dirs=False,
            dry_run=False
        )
        
        assert result.success is True
        assert result.backup_path is None
    
    def test_no_backup_in_dry_run(self, organizer, create_nested_structure):
        """Test que NO se crea backup en dry run mode."""
        root_dir, files = create_nested_structure({
            'subdir': ['photo1.jpg']
        })
        
        analysis = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=True,
            cleanup_empty_dirs=False,
            dry_run=True
        )
        
        assert result.success is True
        assert result.dry_run is True
        assert result.backup_path is None
    
    def test_backup_with_same_filename_different_dirs(self, organizer, create_nested_structure):
        """
        Test CRÍTICO: Backup preserva estructura cuando hay archivos con mismo nombre
        en diferentes subdirectorios.
        """
        # Crear estructura con "photo.jpg" en 3 subdirectorios
        root_dir, files = create_nested_structure({
            'folder1': ['photo.jpg'],
            'folder2': ['photo.jpg'],
            'folder3': ['photo.jpg']
        })
        
        # Modificar contenidos para verificar no sobrescritura
        (root_dir / 'folder1' / 'photo.jpg').write_text('content1')
        (root_dir / 'folder2' / 'photo.jpg').write_text('content2')
        (root_dir / 'folder3' / 'photo.jpg').write_text('content3')
        
        analysis = organizer.analyze(root_dir, OrganizationType.TO_ROOT)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=True,
            cleanup_empty_dirs=False,
            dry_run=False
        )
        
        assert result.success is True
        assert result.backup_path is not None
        
        backup_path = Path(result.backup_path)
        
        # Verificar que se preservó la estructura de directorios
        backup_file1 = backup_path / 'folder1' / 'photo.jpg'
        backup_file2 = backup_path / 'folder2' / 'photo.jpg'
        backup_file3 = backup_path / 'folder3' / 'photo.jpg'
        
        assert backup_file1.exists(), f"Expected {backup_file1} to exist"
        assert backup_file2.exists(), f"Expected {backup_file2} to exist"
        assert backup_file3.exists(), f"Expected {backup_file3} to exist"
        
        # Verificar contenidos (no hubo sobrescritura)
        assert backup_file1.read_text() == 'content1'
        assert backup_file2.read_text() == 'content2'
        assert backup_file3.read_text() == 'content3'
    
    def test_backup_with_nested_structure(self, organizer, create_nested_structure):
        """Test que backup preserva estructura anidada completa."""
        root_dir, files = create_nested_structure({
            'level1/level2/level3': ['deep.jpg'],
            'level1/other': ['shallow.jpg'],
            'root_level': ['top.jpg']
        })
        
        analysis = organizer.analyze(root_dir, OrganizationType.BY_MONTH)
        result = organizer.execute(
            analysis.move_plan,
            create_backup=True,
            cleanup_empty_dirs=False,
            dry_run=False
        )
        
        assert result.success is True
        backup_path = Path(result.backup_path)
        
        # Verificar estructura anidada en backup
        assert (backup_path / 'level1' / 'level2' / 'level3' / 'deep.jpg').exists()
        assert (backup_path / 'level1' / 'other' / 'shallow.jpg').exists()
        assert (backup_path / 'root_level' / 'top.jpg').exists()

