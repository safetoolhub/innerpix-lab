"""
Tests unitarios para LivePhotoCleaner.

Prueba la limpieza de Live Photos, incluyendo:
- Análisis de limpieza (qué archivos se eliminarían)
- Ejecución de limpieza (real y dry-run)
- Diferentes modos de limpieza (KEEP_IMAGE, KEEP_VIDEO, etc.)
- Creación de backups
"""

import pytest
from pathlib import Path
from datetime import datetime
from services.live_photo_cleaner import LivePhotoCleaner, CleanupMode
from services.live_photo_detector import LivePhotoDetector


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoCleanerBasics:
    """Tests básicos de funcionalidad del cleaner."""
    
    def test_cleaner_initialization(self):
        """Test que el cleaner se inicializa correctamente."""
        cleaner = LivePhotoCleaner()
        
        assert cleaner is not None
        assert cleaner.logger is not None
        assert cleaner.detector is not None
        assert isinstance(cleaner.detector, LivePhotoDetector)
        assert cleaner.backup_dir is None
        assert cleaner.dry_run == False
    
    def test_cleaner_has_cleanup_modes(self):
        """Test que CleanupMode tiene los modos correctos."""
        assert hasattr(CleanupMode, 'KEEP_IMAGE')
        assert hasattr(CleanupMode, 'KEEP_VIDEO')
        assert hasattr(CleanupMode, 'KEEP_LARGER')
        assert hasattr(CleanupMode, 'KEEP_SMALLER')
        assert hasattr(CleanupMode, 'CUSTOM')
        
        # Verificar valores
        assert CleanupMode.KEEP_IMAGE.value == 'keep_image'
        assert CleanupMode.KEEP_VIDEO.value == 'keep_video'


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoCleanupAnalysis:
    """Tests de análisis de limpieza (qué se eliminaría)."""
    
    def test_analyze_cleanup_keep_image_mode(self, temp_dir, create_live_photo_pair):
        """Test análisis en modo KEEP_IMAGE (eliminar videos)."""
        # Crear 2 Live Photos
        create_live_photo_pair(temp_dir, 'IMG_0001')
        create_live_photo_pair(temp_dir, 'IMG_0002')
        
        # Analizar
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        # Validar resultados
        assert analysis.success == True
        assert analysis.live_photos_found == 2
        assert analysis.total_files == 4  # 2 pares = 4 archivos
        
        # Debe marcar videos para eliminar
        assert len(analysis.files_to_delete) == 2
        assert len(analysis.files_to_keep) == 2
        
        # Todos los archivos a eliminar deben ser videos (.MOV)
        for file_info in analysis.files_to_delete:
            assert file_info['type'] == 'video'
            assert file_info['path'].suffix.upper() == '.MOV'
        
        # Todos los archivos a mantener deben ser imágenes
        for file_info in analysis.files_to_keep:
            assert file_info['type'] == 'image'
    
    def test_analyze_cleanup_keep_video_mode(self, temp_dir, create_live_photo_pair):
        """Test análisis en modo KEEP_VIDEO (eliminar imágenes)."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_VIDEO)
        
        assert analysis.live_photos_found == 1
        
        # Debe marcar imagen para eliminar
        assert len(analysis.files_to_delete) == 1
        assert analysis.files_to_delete[0]['type'] == 'image'
        
        # Debe mantener video
        assert len(analysis.files_to_keep) == 1
        assert analysis.files_to_keep[0]['type'] == 'video'
    
    def test_analyze_cleanup_keep_larger_mode(self, temp_dir, create_live_photo_pair):
        """Test análisis en modo KEEP_LARGER (mantener archivo más grande)."""
        # Crear Live Photo con video más grande que imagen
        img_path, vid_path = create_live_photo_pair(
            temp_dir,
            'IMG_0001',
            img_size=(50, 50),  # Imagen pequeña
            vid_size=5000  # Video grande
        )
        
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_LARGER)
        
        assert analysis.live_photos_found == 1
        
        # El video es más grande, debe mantenerse
        kept_file = analysis.files_to_keep[0]
        assert kept_file['type'] == 'video'
        assert kept_file['path'] == vid_path
        
        # La imagen debe eliminarse
        deleted_file = analysis.files_to_delete[0]
        assert deleted_file['type'] == 'image'
        assert deleted_file['path'] == img_path
    
    def test_analyze_cleanup_keep_smaller_mode(self, temp_dir, create_live_photo_pair):
        """Test análisis en modo KEEP_SMALLER (mantener archivo más pequeño)."""
        img_path, vid_path = create_live_photo_pair(
            temp_dir,
            'IMG_0001',
            img_size=(50, 50),  # Imagen pequeña
            vid_size=5000  # Video grande
        )
        
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_SMALLER)
        
        # La imagen es más pequeña, debe mantenerse
        kept_file = analysis.files_to_keep[0]
        assert kept_file['type'] == 'image'
        assert kept_file['path'] == img_path
        
        # El video debe eliminarse
        deleted_file = analysis.files_to_delete[0]
        assert deleted_file['type'] == 'video'
        assert deleted_file['path'] == vid_path
    
    def test_analyze_cleanup_empty_directory(self, temp_dir):
        """Test análisis en directorio sin Live Photos."""
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.success == True
        assert analysis.live_photos_found == 0
        assert analysis.total_files == 0
        assert len(analysis.files_to_delete) == 0
        assert len(analysis.files_to_keep) == 0
        assert analysis.space_to_free == 0
    
    def test_analyze_cleanup_calculates_space_correctly(self, temp_dir, create_live_photo_pair):
        """Test que el análisis calcula el espacio correctamente."""
        # Crear Live Photo con tamaños conocidos
        img_path, vid_path = create_live_photo_pair(
            temp_dir,
            'IMG_0001',
            vid_size=2048  # 2KB
        )
        
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        # El espacio a liberar debe ser el tamaño del video
        assert analysis.space_to_free == vid_path.stat().st_size
        
        # El espacio total debe ser imagen + video
        expected_total = img_path.stat().st_size + vid_path.stat().st_size
        assert analysis.total_space == expected_total


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoCleanupExecution:
    """Tests de ejecución de limpieza (real y dry-run)."""
    
    def test_execute_cleanup_dry_run_keeps_files(self, temp_dir, create_live_photo_pair):
        """Test que dry-run no elimina archivos reales."""
        img_path, vid_path = create_live_photo_pair(temp_dir, 'IMG_0001')
        
        # Analizar
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        # Ejecutar en dry-run
        result = cleaner.execute_cleanup(
            analysis,
            create_backup=False,
            dry_run=True
        )
        
        # Debe indicar que es simulación
        assert result.dry_run == True
        assert result.success == True
        
        # Los archivos NO deben haber sido eliminados
        assert img_path.exists()
        assert vid_path.exists()
    
    def test_execute_cleanup_real_deletes_files(self, temp_dir, create_live_photo_pair):
        """Test que ejecución real elimina archivos."""
        img_path, vid_path = create_live_photo_pair(temp_dir, 'IMG_0001')
        
        # Analizar
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        # Ejecutar sin dry-run y sin backup (para simplificar test)
        result = cleaner.execute_cleanup(
            analysis,
            create_backup=False,
            dry_run=False
        )
        
        # Debe haber eliminado el video
        assert result.success == True
        assert result.files_deleted == 1
        assert result.space_freed > 0
        
        # La imagen debe seguir existiendo
        assert img_path.exists()
        
        # El video debe haber sido eliminado
        assert not vid_path.exists()
    
    def test_execute_cleanup_with_backup(self, temp_dir, create_live_photo_pair):
        """Test que se crea backup antes de eliminar."""
        img_path, vid_path = create_live_photo_pair(temp_dir, 'IMG_0001')
        
        # Analizar
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        # Ejecutar con backup
        result = cleaner.execute_cleanup(
            analysis,
            create_backup=True,
            dry_run=False
        )
        
        # Debe haber creado backup
        assert result.backup_path is not None
        backup_path = Path(result.backup_path)
        assert backup_path.exists()
        assert backup_path.is_dir()
        
        # El backup debe contener el video eliminado
        backed_up_video = backup_path / vid_path.name
        assert backed_up_video.exists()
    
    def test_execute_cleanup_empty_analysis(self, temp_dir):
        """Test ejecutar con análisis vacío."""
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        # Ejecutar con análisis vacío
        result = cleaner.execute_cleanup(
            analysis,
            create_backup=False,
            dry_run=False
        )
        
        assert result.success == True
        assert result.files_deleted == 0
        assert result.message == 'No hay archivos para eliminar'
    
    def test_execute_cleanup_multiple_live_photos(self, temp_dir, create_live_photo_pair):
        """Test eliminar múltiples Live Photos."""
        # Crear 3 Live Photos
        paths = []
        for i in range(1, 4):
            img, vid = create_live_photo_pair(temp_dir, f'IMG_{i:04d}')
            paths.append((img, vid))
        
        # Analizar y ejecutar
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        result = cleaner.execute_cleanup(
            analysis,
            create_backup=False,
            dry_run=False
        )
        
        # Debe haber eliminado 3 videos
        assert result.files_deleted == 3
        
        # Las imágenes deben existir
        for img, vid in paths:
            assert img.exists()
            assert not vid.exists()
    
    def test_execute_cleanup_reports_space_freed(self, temp_dir, create_live_photo_pair):
        """Test que se reporta correctamente el espacio liberado."""
        img_path, vid_path = create_live_photo_pair(
            temp_dir,
            'IMG_0001',
            vid_size=3072  # 3KB
        )
        
        video_size = vid_path.stat().st_size
        
        # Analizar y ejecutar
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        result = cleaner.execute_cleanup(
            analysis,
            create_backup=False,
            dry_run=False
        )
        
        # El espacio liberado debe coincidir con el tamaño del video
        assert result.space_freed == video_size





@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoCleanupEdgeCases:
    """Tests de casos edge y situaciones especiales."""
    
    def test_cleanup_with_missing_file(self, temp_dir, create_live_photo_pair):
        """Test cleanup cuando un archivo desaparece durante la operación."""
        img_path, vid_path = create_live_photo_pair(temp_dir, 'IMG_0001')
        
        # Analizar
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        # Eliminar el video manualmente antes de ejecutar
        vid_path.unlink()
        
        # Ejecutar cleanup
        result = cleaner.execute_cleanup(
            analysis,
            create_backup=False,
            dry_run=False
        )
        
        # Debe manejar el error gracefully
        assert result.success == False or result.has_errors
    
    def test_cleanup_preserves_correct_files_by_mode(self, temp_dir, create_live_photo_pair):
        """Test que cada modo preserva los archivos correctos."""
        img_path, vid_path = create_live_photo_pair(temp_dir, 'IMG_0001')
        
        # Modo KEEP_IMAGE
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        assert len(analysis.files_to_keep) == 1
        assert analysis.files_to_keep[0]['type'] == 'image'
        
        # Modo KEEP_VIDEO
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_VIDEO)
        assert len(analysis.files_to_keep) == 1
        assert analysis.files_to_keep[0]['type'] == 'video'
    
    def test_cleanup_analysis_dataclass_structure(self, temp_dir, create_live_photo_pair):
        """Test que el resultado del análisis tiene la estructura correcta."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        # Verificar campos del dataclass
        assert hasattr(analysis, 'total_files')
        assert hasattr(analysis, 'live_photos_found')
        assert hasattr(analysis, 'files_to_delete')
        assert hasattr(analysis, 'files_to_keep')
        assert hasattr(analysis, 'space_to_free')
        assert hasattr(analysis, 'total_space')
        assert hasattr(analysis, 'cleanup_mode')
        
        # Verificar tipos
        assert isinstance(analysis.files_to_delete, list)
        assert isinstance(analysis.files_to_keep, list)
        assert isinstance(analysis.space_to_free, int)
    
    def test_cleanup_result_dataclass_structure(self, temp_dir, create_live_photo_pair):
        """Test que el resultado de ejecución tiene la estructura correcta."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        result = cleaner.execute_cleanup(
            analysis,
            create_backup=False,
            dry_run=True
        )
        
        # Verificar campos del dataclass
        assert hasattr(result, 'success')
        assert hasattr(result, 'files_deleted')
        assert hasattr(result, 'space_freed')
        assert hasattr(result, 'dry_run')
        assert hasattr(result, 'message')
        assert hasattr(result, 'backup_path')
        
        # Verificar valores para dry-run
        assert result.dry_run == True
        assert result.success == True


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoCleanupIntegrationWithDetector:
    """Tests de integración entre cleaner y detector."""
    
    def test_cleaner_uses_detector_internally(self, temp_dir, create_live_photo_pair):
        """Test que el cleaner usa el detector internamente."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        
        cleaner = LivePhotoCleaner()
        
        # El cleaner debe tener un detector
        assert cleaner.detector is not None
        assert isinstance(cleaner.detector, LivePhotoDetector)
        
        # El análisis debe usar el detector
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        # Debe haber detectado el Live Photo
        assert analysis.live_photos_found == 1
    
    def test_cleaner_analysis_matches_detector_results(self, temp_dir, create_live_photo_pair):
        """Test que el análisis del cleaner coincide con la detección."""
        # Crear 2 Live Photos
        create_live_photo_pair(temp_dir, 'IMG_0001')
        create_live_photo_pair(temp_dir, 'IMG_0002')
        
        # Detectar directamente
        detector = LivePhotoDetector()
        detected = detector.detect_in_directory(temp_dir, recursive=False)
        
        # Analizar con cleaner
        cleaner = LivePhotoCleaner()
        analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
        
        # Deben coincidir
        assert analysis.live_photos_found == len(detected)
        assert analysis.live_photos_found == 2
