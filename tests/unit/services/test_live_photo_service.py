"""
Tests unitarios para LivePhotoService.

Prueba el servicio consolidado de Live Photos que integra detección y limpieza:
- Análisis de Live Photos con plan de limpieza
- Ejecución de limpieza (real y dry-run)
- Diferentes modos de limpieza (KEEP_IMAGE, KEEP_VIDEO, etc.)
- Creación de backups
- Cancelación de operaciones
"""

import pytest
from pathlib import Path
from services.live_photo_service import LivePhotoService, CleanupMode, LivePhotoGroup


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoServiceBasics:
    """Tests básicos de funcionalidad del servicio."""
    
    def test_service_initialization(self):
        """Test que el servicio se inicializa correctamente."""
        service = LivePhotoService()
        
        assert service is not None
        assert service.logger is not None
        assert service.backup_dir is None
        assert service.photo_extensions == {'.HEIC', '.JPG', '.JPEG'}
        assert service.video_extensions == {'.MOV'}
        assert service.time_tolerance == 2.0
    
    def test_service_has_cleanup_modes(self):
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
class TestLivePhotoServiceAnalysis:
    """Tests de análisis de Live Photos con plan de limpieza."""
    
    def test_analyze_keep_image_mode(self, temp_dir, create_live_photo_pair):
        """Test análisis en modo KEEP_IMAGE (eliminar videos)."""
        # Crear 2 Live Photos
        create_live_photo_pair(temp_dir, 'IMG_0001')
        create_live_photo_pair(temp_dir, 'IMG_0002')
        
        # Analizar
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
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
    
    def test_analyze_keep_video_mode(self, temp_dir, create_live_photo_pair):
        """Test análisis en modo KEEP_VIDEO (eliminar imágenes)."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_VIDEO)
        
        assert analysis.success == True
        assert len(analysis.files_to_delete) == 1
        assert len(analysis.files_to_keep) == 1
        
        # Debe eliminar imagen, mantener video
        assert analysis.files_to_delete[0]['type'] == 'image'
        assert analysis.files_to_keep[0]['type'] == 'video'
    
    def test_analyze_keep_larger_mode(self, temp_dir, create_live_photo_pair):
        """Test análisis en modo KEEP_LARGER (mantener archivo más grande)."""
        create_live_photo_pair(temp_dir, 'IMG_0001', img_size=(200, 200), vid_size=3000)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_LARGER)
        
        assert analysis.success == True
        # Debe mantener video (más grande) y eliminar imagen
        assert analysis.files_to_keep[0]['type'] == 'video'
        assert analysis.files_to_delete[0]['type'] == 'image'
        assert analysis.files_to_keep[0]['size'] == 3000
    
    def test_analyze_keep_smaller_mode(self, temp_dir, create_live_photo_pair):
        """Test análisis en modo KEEP_SMALLER (mantener archivo más pequeño)."""
        create_live_photo_pair(temp_dir, 'IMG_0001', img_size=(200, 200), vid_size=3000)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_SMALLER)
        
        assert analysis.success == True
        # Debe mantener imagen (más pequeña) y eliminar video
        assert analysis.files_to_keep[0]['type'] == 'image'
        assert analysis.files_to_delete[0]['type'] == 'video'
    
    def test_analyze_empty_directory(self, temp_dir):
        """Test análisis en directorio sin Live Photos."""
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.success == True
        assert analysis.live_photos_found == 0
        assert len(analysis.files_to_delete) == 0
        assert len(analysis.files_to_keep) == 0
        assert analysis.space_to_free == 0
    
    def test_analyze_calculates_space_correctly(self, temp_dir, create_live_photo_pair):
        """Test que el análisis calcula correctamente el espacio a liberar."""
        create_live_photo_pair(temp_dir, 'IMG_0001', img_size=(100, 100), vid_size=3000)
        create_live_photo_pair(temp_dir, 'IMG_0002', img_size=(120, 120), vid_size=3500)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Debe calcular espacio de videos (a eliminar)
        expected_space = 3000 + 3500
        assert analysis.space_to_free == expected_space
        # No validamos total_space exacto porque depende del tamaño real de imágenes generadas


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoServiceExecution:
    """Tests de ejecución de limpieza."""
    
    def test_execute_dry_run(self, temp_dir, create_live_photo_pair):
        """Test ejecución en modo dry-run (simulación)."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        result = service.execute(analysis, create_backup=False, dry_run=True)
        
        # Validar resultado
        assert result.success == True
        assert result.dry_run == True
        assert result.simulated_files_deleted == 1
        assert result.files_deleted == 0  # No debe eliminar realmente
        
        # Verificar que los archivos siguen existiendo
        video_path = temp_dir / 'IMG_0001.MOV'
        assert video_path.exists()
    
    def test_execute_real_deletion(self, temp_dir, create_live_photo_pair):
        """Test ejecución real de limpieza (elimina archivos)."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        video_path = temp_dir / 'IMG_0001.MOV'
        
        assert video_path.exists()  # Verificar que existe antes
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        # Validar resultado
        assert result.success == True
        assert result.dry_run == False
        assert result.files_deleted == 1
        assert result.space_freed > 0
        
        # Verificar que el video fue eliminado
        assert not video_path.exists()
        
        # Verificar que la imagen se conserva
        image_path = temp_dir / 'IMG_0001.HEIC'
        assert image_path.exists()
    
    def test_execute_with_backup(self, temp_dir, create_live_photo_pair):
        """Test que se crea backup antes de eliminar."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        result = service.execute(analysis, create_backup=True, dry_run=False)
        
        # Validar que se creó backup
        assert result.success == True
        assert result.backup_path is not None
        assert Path(result.backup_path).exists()
        
        # Verificar que el backup contiene el archivo
        backup_path = Path(result.backup_path)
        backup_files = list(backup_path.rglob('*'))
        assert len([f for f in backup_files if f.is_file()]) > 0
    
    def test_execute_multiple_live_photos(self, temp_dir, create_live_photo_pair):
        """Test limpieza de múltiples Live Photos."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        create_live_photo_pair(temp_dir, 'IMG_0002')
        create_live_photo_pair(temp_dir, 'IMG_0003')
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        assert result.success == True
        assert result.files_deleted == 3  # 3 videos eliminados
        
        # Verificar que las imágenes se conservan
        assert (temp_dir / 'IMG_0001.HEIC').exists()
        assert (temp_dir / 'IMG_0002.HEIC').exists()
        assert (temp_dir / 'IMG_0003.HEIC').exists()
        
        # Verificar que los videos fueron eliminados
        assert not (temp_dir / 'IMG_0001.MOV').exists()
        assert not (temp_dir / 'IMG_0002.MOV').exists()
        assert not (temp_dir / 'IMG_0003.MOV').exists()
    
    def test_execute_empty_analysis(self, temp_dir):
        """Test ejecución con análisis vacío (sin archivos para eliminar)."""
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        assert result.success == True
        assert result.files_deleted == 0
        assert result.message == 'No hay archivos para eliminar'


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoServiceEdgeCases:
    """Tests de casos especiales y manejo de errores."""
    
    def test_analyze_nonexistent_directory(self):
        """Test análisis de directorio que no existe."""
        service = LivePhotoService()
        nonexistent = Path('/path/that/does/not/exist')
        
        with pytest.raises(ValueError, match="Directorio no existe"):
            service.analyze(nonexistent, cleanup_mode=CleanupMode.KEEP_IMAGE)
    
    def test_analyze_with_progress_callback(self, temp_dir, create_live_photo_pair):
        """Test que el callback de progreso se llama correctamente."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        
        progress_calls = []
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
            return True  # Continuar
        
        service = LivePhotoService()
        analysis = service.analyze(
            temp_dir, 
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            progress_callback=progress_callback
        )
        
        assert analysis.success == True
        assert len(progress_calls) > 0
    
    def test_execute_with_progress_callback(self, temp_dir, create_live_photo_pair):
        """Test que el callback de progreso se llama durante ejecución."""
        create_live_photo_pair(temp_dir, 'IMG_0001')
        
        progress_calls = []
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
            return True  # Continuar
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        result = service.execute(
            analysis, 
            create_backup=False, 
            dry_run=False,
            progress_callback=progress_callback
        )
        
        assert result.success == True
        assert len(progress_calls) > 0
    
    def test_cancel_via_progress_callback(self, temp_dir, create_live_photo_pair):
        """Test cancelación de operación mediante callback."""
        # Crear varios Live Photos
        for i in range(5):
            create_live_photo_pair(temp_dir, f'IMG_{i:04d}')
        
        cancel_after = 2
        call_count = [0]
        
        def cancel_callback(current, total, message):
            call_count[0] += 1
            return call_count[0] < cancel_after  # Cancelar después de N llamadas
        
        service = LivePhotoService()
        analysis = service.analyze(
            temp_dir, 
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            progress_callback=cancel_callback
        )
        
        # Si se canceló, debe retornar resultado vacío
        if call_count[0] >= cancel_after:
            assert analysis.live_photos_found == 0


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoGroupDataclass:
    """Tests de la dataclass LivePhotoGroup."""
    
    def test_live_photo_group_creation(self, temp_dir, create_test_image):
        """Test creación de LivePhotoGroup."""
        image_path = create_test_image(temp_dir / 'IMG_0001.HEIC', size=(100, 100))
        video_path = create_test_image(temp_dir / 'IMG_0001.MOV', size=(120, 120))
        
        # Obtener tamaños reales de los archivos
        image_size = image_path.stat().st_size
        video_size = video_path.stat().st_size
        
        group = LivePhotoGroup(
            image_path=image_path,
            video_path=video_path,
            base_name='IMG_0001',
            directory=temp_dir,
            image_size=image_size,
            video_size=video_size
        )
        
        assert group.image_path == image_path
        assert group.video_path == video_path
        assert group.base_name == 'IMG_0001'
        assert group.total_size == image_size + video_size
    
    def test_live_photo_group_validation(self, temp_dir):
        """Test que LivePhotoGroup valida existencia de archivos."""
        # Crear solo uno de los archivos
        image_path = temp_dir / 'IMG_0001.HEIC'
        video_path = temp_dir / 'IMG_0001.MOV'
        
        image_path.write_bytes(b'fake image')
        
        with pytest.raises(ValueError, match="Video no existe"):
            LivePhotoGroup(
                image_path=image_path,
                video_path=video_path,
                base_name='IMG_0001',
                directory=temp_dir,
                image_size=100,
                video_size=100
            )
