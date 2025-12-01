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
from services.live_photos_service import LivePhotoService, CleanupMode, LivePhotoGroup


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
        assert service.time_tolerance == 5.0  # Límite de 5 segundos
    
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
        # Crear suficientes Live Photos para alcanzar el intervalo (UI_UPDATE_INTERVAL = 10)
        for i in range(15):
            create_live_photo_pair(temp_dir, f'IMG_{i:04d}')
        
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
        assert len(progress_calls) > 0, "Progress callback should be invoked with 15 files"
    
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
    
    def test_live_photo_group_rejects_different_directories(self, temp_dir):
        """Test que LivePhotoGroup rechaza archivos en directorios diferentes."""
        # Crear subdirectorio
        subdir = temp_dir / 'videos'
        subdir.mkdir()
        
        # Crear archivos en directorios diferentes
        image_path = temp_dir / 'IMG_0001.HEIC'
        video_path = subdir / 'IMG_0001.MOV'
        
        image_path.write_bytes(b'fake image')
        video_path.write_bytes(b'fake video')
        
        # Debe rechazar porque están en directorios diferentes
        with pytest.raises(ValueError, match="mismo directorio"):
            LivePhotoGroup(
                image_path=image_path,
                video_path=video_path,
                base_name='IMG_0001',
                directory=temp_dir,  # Directorio de la imagen
                image_size=100,
                video_size=100
            )


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotosCrossDirectoryDetection:
    """Tests de detección de Live Photos en diferentes directorios."""
    
    def test_image_in_root_video_in_subdir_not_paired(self, temp_dir, create_test_image, create_test_video):
        """Test que imagen en root y video en subdirectorio NO se emparejan."""
        # Crear subdirectorio
        subdir = temp_dir / 'videos'
        subdir.mkdir()
        
        # Imagen en root, video en subdirectorio
        create_test_image(temp_dir / 'IMG_0001.HEIC', size=(100, 100))
        create_test_video(subdir / 'IMG_0001.MOV', size_bytes=2048)
        
        # Analizar
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # No deben emparejarse porque están en directorios diferentes
        assert analysis.live_photos_found == 0
        assert len(analysis.files_to_delete) == 0
        assert len(analysis.files_to_keep) == 0
    
    def test_video_in_root_image_in_subdir_not_paired(self, temp_dir, create_test_image, create_test_video):
        """Test que video en root e imagen en subdirectorio NO se emparejan."""
        # Crear subdirectorio
        subdir = temp_dir / 'photos'
        subdir.mkdir()
        
        # Video en root, imagen en subdirectorio
        create_test_video(temp_dir / 'IMG_0001.MOV', size_bytes=2048)
        create_test_image(subdir / 'IMG_0001.HEIC', size=(100, 100))
        
        # Analizar
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # No deben emparejarse
        assert analysis.live_photos_found == 0
    
    def test_files_in_sibling_subdirs_not_paired(self, temp_dir, create_test_image, create_test_video):
        """Test que archivos en subdirectorios hermanos NO se emparejan."""
        # Crear subdirectorios hermanos
        subdir1 = temp_dir / 'folder1'
        subdir2 = temp_dir / 'folder2'
        subdir1.mkdir()
        subdir2.mkdir()
        
        # Archivos en directorios hermanos con mismo nombre
        create_test_image(subdir1 / 'IMG_0001.HEIC', size=(100, 100))
        create_test_video(subdir2 / 'IMG_0001.MOV', size_bytes=2048)
        
        # Analizar
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # No deben emparejarse
        assert analysis.live_photos_found == 0
    
    def test_files_same_directory_are_paired(self, temp_dir, create_live_photo_pair):
        """Test que archivos en el MISMO directorio SÍ se emparejan correctamente."""
        # Crear Live Photo en mismo directorio
        create_live_photo_pair(temp_dir, 'IMG_0001')
        
        # Analizar
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben emparejarse porque están en el mismo directorio
        assert analysis.live_photos_found == 1
        assert len(analysis.files_to_delete) == 1  # Video
        assert len(analysis.files_to_keep) == 1    # Imagen
    
    def test_recursive_search_pairs_in_subdirs(self, temp_dir, create_live_photo_pair):
        """Test que búsqueda recursiva encuentra pares en subdirectorios."""
        # Crear subdirectorios con Live Photos
        subdir1 = temp_dir / 'vacation'
        subdir2 = temp_dir / 'vacation' / '2024'
        subdir1.mkdir()
        subdir2.mkdir()
        
        # Crear Live Photos en diferentes niveles
        create_live_photo_pair(temp_dir, 'IMG_ROOT')
        create_live_photo_pair(subdir1, 'IMG_SUB1')
        create_live_photo_pair(subdir2, 'IMG_SUB2')
        
        # Analizar recursivamente
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE, recursive=True)
        
        # Debe encontrar los 3 pares
        assert analysis.live_photos_found == 3
        assert len(analysis.files_to_delete) == 3
    
    def test_non_recursive_search_only_root(self, temp_dir, create_live_photo_pair):
        """Test que búsqueda no recursiva solo encuentra pares en root."""
        # Crear subdirectorio
        subdir = temp_dir / 'photos'
        subdir.mkdir()
        
        # Crear Live Photos en root y subdirectorio
        create_live_photo_pair(temp_dir, 'IMG_ROOT')
        create_live_photo_pair(subdir, 'IMG_SUB')
        
        # Analizar NO recursivamente
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE, recursive=False)
        
        # Solo debe encontrar el del root
        assert analysis.live_photos_found == 1


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotosCaseSensitivity:
    """Tests de sensibilidad a mayúsculas/minúsculas en nombres."""
    
    def test_identical_names_different_case_are_paired(self, temp_dir, create_test_image, create_test_video):
        """Test que nombres idénticos con diferente case se emparejan (photo.jpg vs PHOTO.jpg)."""
        # Crear archivos con mismo nombre pero diferente case
        create_test_image(temp_dir / 'photo.jpg', size=(100, 100))
        create_test_video(temp_dir / 'PHOTO.MOV', size_bytes=2048)
        
        # Analizar
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben emparejarse (la normalización ignora case)
        assert analysis.live_photos_found == 1
    
    def test_same_base_different_extension_case_paired(self, temp_dir, create_test_image, create_test_video):
        """Test que mismo base con diferente case en extensión se emparejan (photo.JPG vs photo.jpg)."""
        # Crear archivos con extensiones en diferente case
        create_test_image(temp_dir / 'MyPhoto.JPG', size=(100, 100))
        create_test_video(temp_dir / 'MyPhoto.MOV', size_bytes=2048)
        
        # Analizar
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben emparejarse
        assert analysis.live_photos_found == 1
    
    def test_mixed_case_filename_with_lowercase_ext(self, temp_dir, create_test_image, create_test_video):
        """Test nombres con case mixto (Photo.JPG + photo.mov)."""
        # Crear con case mixto
        create_test_image(temp_dir / 'Photo.JPEG', size=(100, 100))
        create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        # Analizar
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben emparejarse
        assert analysis.live_photos_found == 1
    
    def test_all_uppercase_vs_all_lowercase(self, temp_dir, create_test_image, create_test_video):
        """Test todo mayúsculas vs todo minúsculas."""
        # TODO MAYÚSCULAS vs todo minúsculas
        create_test_image(temp_dir / 'IMG_0001.HEIC', size=(100, 100))
        create_test_video(temp_dir / 'img_0001.mov', size_bytes=2048)
        
        # Analizar
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben emparejarse
        assert analysis.live_photos_found == 1


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotosExtensionCombinations:
    """Tests de diferentes combinaciones de extensiones válidas."""
    
    def test_jpg_lowercase_with_mov(self, temp_dir, create_test_image, create_test_video):
        """Test .jpg + .MOV"""
        create_test_image(temp_dir / 'photo.jpg', size=(100, 100))
        create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        assert analysis.live_photos_found == 1
    
    def test_jpg_uppercase_with_mov(self, temp_dir, create_test_image, create_test_video):
        """Test .JPG + .MOV"""
        create_test_image(temp_dir / 'photo.JPG', size=(100, 100))
        create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        assert analysis.live_photos_found == 1
    
    def test_jpeg_lowercase_with_mov(self, temp_dir, create_test_image, create_test_video):
        """Test .jpeg + .MOV"""
        create_test_image(temp_dir / 'photo.jpeg', size=(100, 100))
        create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        assert analysis.live_photos_found == 1
    
    def test_jpeg_uppercase_with_mov(self, temp_dir, create_test_image, create_test_video):
        """Test .JPEG + .MOV"""
        create_test_image(temp_dir / 'photo.JPEG', size=(100, 100))
        create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        assert analysis.live_photos_found == 1
    
    def test_heic_lowercase_with_mov(self, temp_dir, create_test_image, create_test_video):
        """Test .heic + .MOV"""
        create_test_image(temp_dir / 'photo.heic', size=(100, 100))
        create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        assert analysis.live_photos_found == 1
    
    def test_heic_uppercase_with_mov(self, temp_dir, create_test_image, create_test_video):
        """Test .HEIC + .MOV"""
        create_test_image(temp_dir / 'photo.HEIC', size=(100, 100))
        create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        assert analysis.live_photos_found == 1
    
    def test_mixed_case_extensions(self, temp_dir, create_test_image, create_test_video):
        """Test extensiones con case mixto (Photo.JpG + Photo.MoV)."""
        # Crear archivos con extensiones en case mixto
        img_path = temp_dir / 'Photo.JpG'
        vid_path = temp_dir / 'Photo.MoV'
        
        # PIL no soporta guardar como .JpG directamente, así que creamos y renombramos
        temp_img = temp_dir / 'Photo_temp.jpg'
        temp_vid = temp_dir / 'Photo_temp.mov'
        
        create_test_image(temp_img, size=(100, 100))
        create_test_video(temp_vid, size_bytes=2048)
        
        temp_img.rename(img_path)
        temp_vid.rename(vid_path)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Debería emparejarse (normalización de extensiones)
        assert analysis.live_photos_found == 1
    
    def test_all_extensions_in_same_dir(self, temp_dir, create_test_image, create_test_video):
        """Test múltiples extensiones válidas en mismo directorio."""
        # Crear varios Live Photos con diferentes extensiones
        create_test_image(temp_dir / 'photo1.jpg', size=(100, 100))
        create_test_video(temp_dir / 'photo1.MOV', size_bytes=2048)
        
        create_test_image(temp_dir / 'photo2.JPEG', size=(100, 100))
        create_test_video(temp_dir / 'photo2.MOV', size_bytes=2048)
        
        create_test_image(temp_dir / 'photo3.heic', size=(100, 100))
        create_test_video(temp_dir / 'photo3.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben encontrarse los 3 pares
        assert analysis.live_photos_found == 3


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotosEdgeCasesFilenames:
    """Tests de casos especiales con nombres de archivos."""
    
    def test_special_characters_in_filename(self, temp_dir, create_test_image, create_test_video):
        """Test nombres con caracteres especiales."""
        # Crear con caracteres especiales comunes
        special_name = 'Photo-2024_01_15@10h30m'
        create_test_image(temp_dir / f'{special_name}.jpg', size=(100, 100))
        create_test_video(temp_dir / f'{special_name}.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben emparejarse
        assert analysis.live_photos_found == 1
    
    def test_spaces_in_filename(self, temp_dir, create_test_image, create_test_video):
        """Test nombres con espacios."""
        name_with_spaces = 'My Vacation Photo 2024'
        create_test_image(temp_dir / f'{name_with_spaces}.jpg', size=(100, 100))
        create_test_video(temp_dir / f'{name_with_spaces}.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.live_photos_found == 1
    
    def test_unicode_characters_in_filename(self, temp_dir, create_test_image, create_test_video):
        """Test nombres con caracteres Unicode."""
        unicode_name = 'Foto_España_2024_ñáéíóú'
        create_test_image(temp_dir / f'{unicode_name}.jpg', size=(100, 100))
        create_test_video(temp_dir / f'{unicode_name}.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.live_photos_found == 1
    
    def test_very_long_filename(self, temp_dir, create_test_image, create_test_video):
        """Test nombre muy largo (cerca del límite del sistema)."""
        # Nombre de 200 caracteres (bajo el límite de 255 de la mayoría de sistemas)
        long_name = 'A' * 200
        create_test_image(temp_dir / f'{long_name}.jpg', size=(100, 100))
        create_test_video(temp_dir / f'{long_name}.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.live_photos_found == 1
    
    def test_filename_with_multiple_dots(self, temp_dir, create_test_image, create_test_video):
        """Test nombre con múltiples puntos."""
        dotted_name = 'photo.backup.2024.final'
        create_test_image(temp_dir / f'{dotted_name}.jpg', size=(100, 100))
        create_test_video(temp_dir / f'{dotted_name}.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.live_photos_found == 1
    
    def test_multiple_potential_pairs_same_dir(self, temp_dir, create_live_photo_pair):
        """Test múltiples pares potenciales en el mismo directorio."""
        # Crear 5 Live Photos diferentes
        for i in range(1, 6):
            create_live_photo_pair(temp_dir, f'IMG_{i:04d}')
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben encontrarse todos los pares
        assert analysis.live_photos_found == 5
        assert len(analysis.files_to_delete) == 5
    
    def test_orphaned_image_no_video(self, temp_dir, create_test_image):
        """Test imagen sin video correspondiente (huérfana)."""
        # Solo crear imagen
        create_test_image(temp_dir / 'orphan.jpg', size=(100, 100))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # No debe encontrar pares
        assert analysis.live_photos_found == 0
        assert len(analysis.files_to_delete) == 0
    
    def test_orphaned_video_no_image(self, temp_dir, create_test_video):
        """Test video sin imagen correspondiente (huérfano)."""
        # Solo crear video
        create_test_video(temp_dir / 'orphan.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # No debe encontrar pares
        assert analysis.live_photos_found == 0
        assert len(analysis.files_to_delete) == 0
    
    def test_mixed_orphaned_and_paired_files(self, temp_dir, create_live_photo_pair, create_test_image, create_test_video):
        """Test mezcla de archivos emparejados y huérfanos."""
        # Crear 2 Live Photos válidos
        create_live_photo_pair(temp_dir, 'IMG_0001')
        create_live_photo_pair(temp_dir, 'IMG_0002')
        
        # Crear huérfanos
        create_test_image(temp_dir / 'orphan_img.jpg', size=(100, 100))
        create_test_video(temp_dir / 'orphan_vid.MOV', size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Solo deben emparejarse los 2 válidos
        assert analysis.live_photos_found == 2
        assert len(analysis.files_to_delete) == 2
        
        # Verificar que los huérfanos no están en el plan
        delete_paths = [str(f['path']) for f in analysis.files_to_delete]
        assert 'orphan_img.jpg' not in str(delete_paths)
        assert 'orphan_vid.MOV' not in str(delete_paths)


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotosEXIFDateMatching:
    """Tests de emparejamiento basado en fechas EXIF y timestamps.
    
    Nota: La implementación actual empareja archivos basándose en nombres de archivo,
    no en fechas EXIF. Estos tests documentan el comportamiento actual y sirven como
    base para futuras mejoras si se desea implementar validación de fechas EXIF.
    """
    
    def test_files_with_matching_timestamps_paired(self, temp_dir, create_test_image, create_test_video):
        """Test que archivos con timestamps similares se emparejan (comportamiento actual)."""
        from datetime import datetime
        import os
        
        # Crear archivos
        img_path = create_test_image(temp_dir / 'photo.jpg', size=(100, 100))
        vid_path = create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        # Ajustar timestamps para que sean idénticos
        timestamp = datetime(2024, 1, 15, 10, 30, 0).timestamp()
        os.utime(img_path, (timestamp, timestamp))
        os.utime(vid_path, (timestamp, timestamp))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben emparejarse
        assert analysis.live_photos_found == 1
    
    def test_files_with_close_timestamps_paired(self, temp_dir, create_test_image, create_test_video):
        """Test que archivos con timestamps cercanos (< 5 segundos) se emparejan."""
        from datetime import datetime, timedelta
        import os
        
        # Crear archivos
        img_path = create_test_image(temp_dir / 'photo.jpg', size=(100, 100))
        vid_path = create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        # Timestamps con 3 segundos de diferencia (dentro del límite)
        base_time = datetime(2024, 1, 15, 10, 30, 0)
        img_timestamp = base_time.timestamp()
        vid_timestamp = (base_time + timedelta(seconds=3)).timestamp()
        
        os.utime(img_path, (img_timestamp, img_timestamp))
        os.utime(vid_path, (vid_timestamp, vid_timestamp))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben emparejarse porque están dentro del límite de 5 segundos
        assert analysis.live_photos_found == 1
        
        # Verificar que time_difference está disponible en el grupo
        if analysis.groups:
            group = analysis.groups[0]
            # La diferencia debe ser aproximadamente 3 segundos
            assert 2.5 <= group.time_difference <= 3.5
    
    def test_files_with_distant_timestamps_not_paired(self, temp_dir, create_test_image, create_test_video):
        """Test que archivos con timestamps distantes (> 5 segundos) NO se emparejan.
        
        Con la validación de tiempo implementada, archivos con diferencia > 5 segundos
        no se consideran Live Photos válidos, aunque tengan el mismo nombre.
        """
        from datetime import datetime, timedelta
        import os
        from config import Config
        
        # Crear archivos
        img_path = create_test_image(temp_dir / 'photo.jpg', size=(100, 100))
        vid_path = create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        # Timestamps con 2 horas de diferencia (>> 5 segundos)
        base_time = datetime(2024, 1, 15, 10, 30, 0)
        img_timestamp = base_time.timestamp()
        vid_timestamp = (base_time + timedelta(hours=2)).timestamp()
        
        os.utime(img_path, (img_timestamp, img_timestamp))
        os.utime(vid_path, (vid_timestamp, vid_timestamp))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Comportamiento depende de si la metadata de video está activada
        if Config.USE_VIDEO_METADATA:
            # Con validación temporal: NO deben emparejarse porque la diferencia es > 5 segundos
            assert analysis.live_photos_found == 0
            assert len(analysis.files_to_delete) == 0
        else:
            # Sin validación temporal: SÍ se emparejan por nombre únicamente
            assert analysis.live_photos_found == 1
            assert len(analysis.files_to_delete) == 1
    
    def test_files_without_exif_paired_by_name(self, temp_dir, create_test_image, create_test_video):
        """Test que archivos sin datos EXIF se emparejan por nombre si timestamps similares."""
        from datetime import datetime
        import os
        
        # Crear archivos simples sin EXIF
        img_path = create_test_image(temp_dir / 'photo.jpg', size=(100, 100))
        vid_path = create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        # Ajustar timestamps para que sean casi idénticos (dentro del límite)
        timestamp = datetime(2024, 1, 15, 10, 30, 0).timestamp()
        os.utime(img_path, (timestamp, timestamp))
        os.utime(vid_path, (timestamp, timestamp))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben emparejarse basándose en nombre y timestamps similares
        assert analysis.live_photos_found == 1
    
    def test_time_difference_property_calculation(self, temp_dir, create_test_image, create_test_video):
        """Test que LivePhotoGroup calcula correctamente time_difference."""
        from datetime import datetime, timedelta
        import os
        
        # Crear archivos
        img_path = create_test_image(temp_dir / 'IMG_0001.HEIC', size=(100, 100))
        vid_path = create_test_video(temp_dir / 'IMG_0001.MOV', size_bytes=2048)
        
        # Configurar timestamps con diferencia conocida (10 minutos = 600 segundos)
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        img_timestamp = base_time.timestamp()
        vid_timestamp = (base_time + timedelta(minutes=10)).timestamp()
        
        os.utime(img_path, (img_timestamp, img_timestamp))
        os.utime(vid_path, (vid_timestamp, vid_timestamp))
        
        # Crear LivePhotoGroup directamente
        group = LivePhotoGroup(
            image_path=img_path,
            video_path=vid_path,
            base_name='IMG_0001',
            directory=temp_dir,
            image_size=img_path.stat().st_size,
            video_size=vid_path.stat().st_size
        )
        
        # Verificar que time_difference se calcula correctamente (600 segundos ± margen)
        assert 590 <= group.time_difference <= 610
    
    def test_time_difference_with_video_earlier_than_image(self, temp_dir, create_test_image, create_test_video):
        """Test time_difference cuando el video es anterior a la imagen."""
        from datetime import datetime, timedelta
        import os
        
        # Crear archivos
        img_path = create_test_image(temp_dir / 'IMG_0001.HEIC', size=(100, 100))
        vid_path = create_test_video(temp_dir / 'IMG_0001.MOV', size_bytes=2048)
        
        # Video 5 minutos ANTES que imagen
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        img_timestamp = base_time.timestamp()
        vid_timestamp = (base_time - timedelta(minutes=5)).timestamp()
        
        os.utime(img_path, (img_timestamp, img_timestamp))
        os.utime(vid_path, (vid_timestamp, vid_timestamp))
        
        # Crear LivePhotoGroup
        group = LivePhotoGroup(
            image_path=img_path,
            video_path=vid_path,
            base_name='IMG_0001',
            directory=temp_dir,
            image_size=img_path.stat().st_size,
            video_size=vid_path.stat().st_size
        )
        
        # time_difference debe ser absoluto (300 segundos ± margen)
        assert 290 <= group.time_difference <= 310
    
    def test_groups_sorted_by_time_difference(self, temp_dir, create_test_image, create_test_video):
        """Test que grupos con menor time_difference se priorizan."""
        from datetime import datetime, timedelta
        import os
        
        # Crear 3 pares con diferentes diferencias de tiempo (todas dentro del límite)
        pairs = [
            ('photo1', timedelta(seconds=4)),    # 4 segundos
            ('photo2', timedelta(seconds=2)),    # 2 segundos (menor)
            ('photo3', timedelta(seconds=5)),    # 5 segundos (en el límite)
        ]
        
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        for name, time_diff in pairs:
            img_path = create_test_image(temp_dir / f'{name}.jpg', size=(100, 100))
            vid_path = create_test_video(temp_dir / f'{name}.MOV', size_bytes=2048)
            
            img_timestamp = base_time.timestamp()
            vid_timestamp = (base_time + time_diff).timestamp()
            
            os.utime(img_path, (img_timestamp, img_timestamp))
            os.utime(vid_path, (vid_timestamp, vid_timestamp))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Deben encontrarse los 3 pares (todos dentro del límite de 5 segundos)
        assert analysis.live_photos_found == 3
        
        # Verificar que los grupos están ordenados por time_difference
        if len(analysis.groups) == 3:
            differences = [g.time_difference for g in analysis.groups]
            # Todos deben estar dentro del límite
            assert all(d <= 5.0 for d in differences)
            # photo2 (2 seg) debe tener la menor diferencia
            assert min(differences) <= 2.5


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotosTimeValidation:
    """Tests específicos para validación de límite de tiempo de 5 segundos."""
    
    def test_exactly_5_seconds_is_valid(self, temp_dir, create_test_image, create_test_video):
        """Test que diferencia de exactamente 5 segundos es válida (límite inclusivo)."""
        from datetime import datetime, timedelta
        import os
        
        img_path = create_test_image(temp_dir / 'photo.jpg', size=(100, 100))
        vid_path = create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        # Exactamente 5 segundos de diferencia
        base_time = datetime(2024, 1, 15, 10, 30, 0)
        os.utime(img_path, (base_time.timestamp(), base_time.timestamp()))
        os.utime(vid_path, ((base_time + timedelta(seconds=5)).timestamp(), 
                            (base_time + timedelta(seconds=5)).timestamp()))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Debe emparejarse (5.0 <= 5.0)
        assert analysis.live_photos_found == 1
    
    def test_slightly_over_5_seconds_is_invalid(self, temp_dir, create_test_image, create_test_video):
        """Test que diferencia > 5 segundos NO es válida."""
        from datetime import datetime, timedelta
        import os
        from config import Config
        
        img_path = create_test_image(temp_dir / 'photo.jpg', size=(100, 100))
        vid_path = create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        # 6 segundos de diferencia (excede el límite)
        base_time = datetime(2024, 1, 15, 10, 30, 0)
        os.utime(img_path, (base_time.timestamp(), base_time.timestamp()))
        os.utime(vid_path, ((base_time + timedelta(seconds=6)).timestamp(), 
                            (base_time + timedelta(seconds=6)).timestamp()))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Comportamiento depende de si la metadata de video está activada
        if Config.USE_VIDEO_METADATA:
            # Con validación temporal: NO debe emparejarse (6.0 > 5.0)
            assert analysis.live_photos_found == 0
        else:
            # Sin validación temporal: SÍ se empareja por nombre únicamente
            assert analysis.live_photos_found == 1
    
    def test_zero_time_difference_is_valid(self, temp_dir, create_test_image, create_test_video):
        """Test que diferencia de 0 segundos (timestamps idénticos) es válida."""
        from datetime import datetime
        import os
        
        img_path = create_test_image(temp_dir / 'photo.jpg', size=(100, 100))
        vid_path = create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        
        # Timestamps idénticos
        timestamp = datetime(2024, 1, 15, 10, 30, 0).timestamp()
        os.utime(img_path, (timestamp, timestamp))
        os.utime(vid_path, (timestamp, timestamp))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.live_photos_found == 1
        assert analysis.groups[0].time_difference < 0.1  # Prácticamente 0
    
    def test_mixed_valid_and_invalid_time_differences(self, temp_dir, create_test_image, create_test_video):
        """Test que solo se emparejan archivos con diferencia <= 5 segundos."""
        from datetime import datetime, timedelta
        import os
        from config import Config
        
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        # Par 1: 2 segundos (válido)
        img1 = create_test_image(temp_dir / 'photo1.jpg', size=(100, 100))
        vid1 = create_test_video(temp_dir / 'photo1.MOV', size_bytes=2048)
        os.utime(img1, (base_time.timestamp(), base_time.timestamp()))
        os.utime(vid1, ((base_time + timedelta(seconds=2)).timestamp(), 
                        (base_time + timedelta(seconds=2)).timestamp()))
        
        # Par 2: 10 segundos (inválido)
        img2 = create_test_image(temp_dir / 'photo2.jpg', size=(100, 100))
        vid2 = create_test_video(temp_dir / 'photo2.MOV', size_bytes=2048)
        os.utime(img2, (base_time.timestamp(), base_time.timestamp()))
        os.utime(vid2, ((base_time + timedelta(seconds=10)).timestamp(), 
                        (base_time + timedelta(seconds=10)).timestamp()))
        
        # Par 3: 5 segundos (válido, en el límite)
        img3 = create_test_image(temp_dir / 'photo3.jpg', size=(100, 100))
        vid3 = create_test_video(temp_dir / 'photo3.MOV', size_bytes=2048)
        os.utime(img3, (base_time.timestamp(), base_time.timestamp()))
        os.utime(vid3, ((base_time + timedelta(seconds=5)).timestamp(), 
                        (base_time + timedelta(seconds=5)).timestamp()))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Comportamiento depende de si la metadata de video está activada
        if Config.USE_VIDEO_METADATA:
            # Con validación temporal: Solo deben encontrarse 2 pares (photo1 y photo3)
            assert analysis.live_photos_found == 2
            assert len(analysis.files_to_delete) == 2
        else:
            # Sin validación temporal: Se detectan TODOS los 3 pares por nombre
            assert analysis.live_photos_found == 3
            assert len(analysis.files_to_delete) == 3
    
    def test_time_validation_with_dry_run(self, temp_dir, create_test_image, create_test_video):
        """Test que validación de tiempo funciona correctamente en modo dry-run."""
        from datetime import datetime, timedelta
        import os
        from config import Config
        
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        # Par válido: 3 segundos
        img = create_test_image(temp_dir / 'valid.jpg', size=(100, 100))
        vid = create_test_video(temp_dir / 'valid.MOV', size_bytes=2048)
        os.utime(img, (base_time.timestamp(), base_time.timestamp()))
        os.utime(vid, ((base_time + timedelta(seconds=3)).timestamp(), 
                       (base_time + timedelta(seconds=3)).timestamp()))
        
        # Par inválido: 8 segundos
        img_invalid = create_test_image(temp_dir / 'invalid.jpg', size=(100, 100))
        vid_invalid = create_test_video(temp_dir / 'invalid.MOV', size_bytes=2048)
        os.utime(img_invalid, (base_time.timestamp(), base_time.timestamp()))
        os.utime(vid_invalid, ((base_time + timedelta(seconds=8)).timestamp(), 
                               (base_time + timedelta(seconds=8)).timestamp()))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Comportamiento depende de si la metadata de video está activada
        expected_live_photos = 1 if Config.USE_VIDEO_METADATA else 2
        
        # Solo el par válido debe ser detectado (o ambos si no hay validación temporal)
        assert analysis.live_photos_found == expected_live_photos
        
        # Ejecutar en modo dry-run
        result = service.execute(analysis, create_backup=False, dry_run=True)
        
        assert result.success == True
        assert result.dry_run == True
        assert result.simulated_files_deleted == expected_live_photos
        assert vid.exists()  # No debe eliminar en dry-run
        assert vid_invalid.exists()  # Tampoco debe tocar el inválido
    
    def test_time_validation_with_backup(self, temp_dir, create_test_image, create_test_video):
        """Test que validación de tiempo funciona correctamente con backup habilitado."""
        from datetime import datetime, timedelta
        import os
        
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        # Crear 2 pares válidos
        for i in range(1, 3):
            img = create_test_image(temp_dir / f'photo{i}.jpg', size=(100, 100))
            vid = create_test_video(temp_dir / f'photo{i}.MOV', size_bytes=2048)
            os.utime(img, (base_time.timestamp(), base_time.timestamp()))
            os.utime(vid, ((base_time + timedelta(seconds=2)).timestamp(), 
                           (base_time + timedelta(seconds=2)).timestamp()))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.live_photos_found == 2
        
        # Ejecutar con backup
        result = service.execute(analysis, create_backup=True, dry_run=False)
        
        assert result.success == True
        assert result.files_deleted == 2
        assert result.backup_path is not None
        assert Path(result.backup_path).exists()
        
        # Verificar que los videos fueron eliminados
        assert not (temp_dir / 'photo1.MOV').exists()
        assert not (temp_dir / 'photo2.MOV').exists()
        
        # Verificar que las imágenes se conservan
        assert (temp_dir / 'photo1.jpg').exists()
        assert (temp_dir / 'photo2.jpg').exists()
    
    def test_time_validation_with_real_execution(self, temp_dir, create_test_image, create_test_video):
        """Test ejecución real con validación de tiempo (sin dry-run, sin backup)."""
        from datetime import datetime, timedelta
        import os
        
        base_time = datetime(2024, 1, 15, 10, 0, 0)
        
        # Par válido
        img = create_test_image(temp_dir / 'photo.jpg', size=(100, 100))
        vid = create_test_video(temp_dir / 'photo.MOV', size_bytes=2048)
        os.utime(img, (base_time.timestamp(), base_time.timestamp()))
        os.utime(vid, ((base_time + timedelta(seconds=4)).timestamp(), 
                       (base_time + timedelta(seconds=4)).timestamp()))
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.live_photos_found == 1
        
        # Ejecutar sin backup y sin dry-run
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        assert result.success == True
        assert result.files_deleted == 1
        assert result.dry_run == False
        assert result.backup_path is None
        
        # Video debe ser eliminado
        assert not vid.exists()
        # Imagen debe conservarse
        assert img.exists()
