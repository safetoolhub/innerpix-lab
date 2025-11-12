"""
Tests unitarios para LivePhotoDetector.

Prueba la detección de Live Photos de iPhone, incluyendo:
- Detección de pares válidos (imagen + video)
- Manejo de archivos huérfanos
- Casos edge: nombres especiales, subdirectorios, etc.
"""

import pytest
from pathlib import Path
from datetime import datetime
from services.live_photo_detector import LivePhotoDetector, LivePhotoGroup


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoDetectorBasics:
    """Tests básicos de funcionalidad del detector."""
    
    def test_detector_initialization(self):
        """Test que el detector se inicializa correctamente."""
        detector = LivePhotoDetector()
        
        assert detector is not None
        assert detector.logger is not None
        assert hasattr(detector, 'photo_extensions')
        assert hasattr(detector, 'video_extensions')
        assert hasattr(detector, 'time_tolerance')
    
    def test_detector_has_correct_extensions(self):
        """Test que el detector tiene las extensiones correctas configuradas."""
        detector = LivePhotoDetector()
        
        # Live Photos usan HEIC/JPG para fotos y MOV para videos
        assert '.HEIC' in detector.photo_extensions
        assert '.JPG' in detector.photo_extensions
        assert '.MOV' in detector.video_extensions
    
    def test_detector_inherits_from_base_service(self):
        """Test que el detector hereda correctamente de BaseService."""
        detector = LivePhotoDetector()
        
        # Debe tener métodos de BaseService
        assert hasattr(detector, '_log_section_header')
        assert hasattr(detector, '_log_section_footer')
        assert hasattr(detector, 'backup_dir')


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoDetection:
    """Tests de detección de Live Photos."""
    
    def test_detect_single_live_photo_pair(self, temp_dir, create_live_photo_pair):
        """Test detección de un solo par de Live Photo."""
        # Crear un Live Photo
        img_path, vid_path = create_live_photo_pair(
            directory=temp_dir,
            base_name='IMG_0001'
        )
        
        # Detectar
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False)
        
        # Validar
        assert len(live_photos) == 1
        assert live_photos[0].image_path == img_path
        assert live_photos[0].video_path == vid_path
        assert live_photos[0].base_name == 'IMG_0001'
    
    def test_detect_multiple_live_photos(self, temp_dir, create_live_photo_pair):
        """Test detección de múltiples Live Photos."""
        # Crear 3 Live Photos
        pairs = []
        for i in range(1, 4):
            img, vid = create_live_photo_pair(
                directory=temp_dir,
                base_name=f'IMG_{i:04d}'
            )
            pairs.append((img, vid))
        
        # Detectar
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False)
        
        # Validar
        assert len(live_photos) == 3
        
        # Verificar que todos los pares fueron detectados
        detected_bases = {lp.base_name for lp in live_photos}
        expected_bases = {f'IMG_{i:04d}' for i in range(1, 4)}
        assert detected_bases == expected_bases
    
    def test_detect_with_renamed_files(self, temp_dir, create_renamed_file, create_test_video):
        """Test detección con archivos en formato renombrado (IMG_YYYYMMDD_HHMMSS)."""
        date = datetime(2023, 11, 12, 14, 30, 22)
        
        # Crear imagen renombrada
        img_path = create_renamed_file(
            directory=temp_dir,
            date=date,
            file_type='IMG',
            extension='.HEIC'
        )
        
        # Crear video correspondiente
        base_name = img_path.stem  # IMG_20231112_143022
        vid_path = create_test_video(
            path=temp_dir / f"{base_name}.MOV"
        )
        
        # Detectar
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False)
        
        # Validar
        assert len(live_photos) == 1
        assert live_photos[0].base_name == base_name
        assert live_photos[0].image_path == img_path
        assert live_photos[0].video_path == vid_path
    
    def test_detect_ignores_orphan_images(self, temp_dir, create_test_image):
        """Test que imágenes sin video no se detectan como Live Photos."""
        # Crear solo imagen (sin video)
        create_test_image(
            path=temp_dir / 'IMG_ORPHAN.HEIC',
            size=(100, 100)
        )
        
        # Detectar
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False)
        
        # No debe detectar nada
        assert len(live_photos) == 0
    
    def test_detect_ignores_orphan_videos(self, temp_dir, create_test_video):
        """Test que videos sin imagen no se detectan como Live Photos."""
        # Crear solo video (sin imagen)
        create_test_video(
            path=temp_dir / 'VID_ORPHAN.MOV',
            size_bytes=2048
        )
        
        # Detectar
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False)
        
        # No debe detectar nada
        assert len(live_photos) == 0
    
    def test_detect_mixed_valid_and_orphans(self, temp_dir, create_live_photo_pair, 
                                            create_test_image, create_test_video):
        """Test detección con mezcla de Live Photos válidos y archivos huérfanos."""
        # Crear 2 Live Photos válidos
        create_live_photo_pair(temp_dir, 'IMG_0001')
        create_live_photo_pair(temp_dir, 'IMG_0002')
        
        # Crear huérfanos
        create_test_image(path=temp_dir / 'IMG_ORPHAN.HEIC', size=(100, 100))
        create_test_video(path=temp_dir / 'VID_ORPHAN.MOV', size_bytes=1024)
        
        # Detectar
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False)
        
        # Solo debe detectar los 2 válidos
        assert len(live_photos) == 2


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoDetectionRecursive:
    """Tests de detección recursiva en subdirectorios."""
    
    def test_detect_recursive_in_subdirectories(self, nested_temp_dir, create_live_photo_pair):
        """Test detección recursiva encuentra Live Photos en subdirectorios."""
        root_dir, subdirs = nested_temp_dir
        
        # Crear Live Photos en diferentes subdirectorios
        create_live_photo_pair(subdirs['subdir1'], 'IMG_SUB1')
        create_live_photo_pair(subdirs['subdir2'], 'IMG_SUB2')
        create_live_photo_pair(subdirs['nested'], 'IMG_NESTED')
        
        # Detectar recursivamente
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(root_dir, recursive=True)
        
        # Debe encontrar los 3
        assert len(live_photos) == 3
        
        # Verificar que están en diferentes directorios
        directories = {lp.directory for lp in live_photos}
        assert len(directories) == 3
    
    def test_detect_non_recursive_only_root(self, nested_temp_dir, create_live_photo_pair):
        """Test detección no recursiva solo busca en raíz."""
        root_dir, subdirs = nested_temp_dir
        
        # Crear Live Photos en raíz y subdirectorio
        create_live_photo_pair(root_dir, 'IMG_ROOT')
        create_live_photo_pair(subdirs['subdir1'], 'IMG_SUB')
        
        # Detectar NO recursivamente
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(root_dir, recursive=False)
        
        # Solo debe encontrar el de la raíz
        assert len(live_photos) == 1
        assert live_photos[0].base_name == 'IMG_ROOT'


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoGroup:
    """Tests de la clase LivePhotoGroup."""
    
    def test_live_photo_group_creation(self, temp_dir, create_live_photo_pair):
        """Test creación de LivePhotoGroup."""
        img_path, vid_path = create_live_photo_pair(temp_dir, 'IMG_TEST')
        
        # Crear grupo
        group = LivePhotoGroup(
            image_path=img_path,
            video_path=vid_path,
            base_name='IMG_TEST',
            directory=temp_dir,
            image_size=img_path.stat().st_size,
            video_size=vid_path.stat().st_size
        )
        
        assert group.image_path == img_path
        assert group.video_path == vid_path
        assert group.base_name == 'IMG_TEST'
        assert group.directory == temp_dir
        assert group.image_size > 0
        assert group.video_size > 0
    
    def test_live_photo_group_total_size(self, temp_dir, create_live_photo_pair):
        """Test que total_size suma imagen + video."""
        img_path, vid_path = create_live_photo_pair(temp_dir, 'IMG_TEST')
        
        group = LivePhotoGroup(
            image_path=img_path,
            video_path=vid_path,
            base_name='IMG_TEST',
            directory=temp_dir,
            image_size=img_path.stat().st_size,
            video_size=vid_path.stat().st_size
        )
        
        expected_total = img_path.stat().st_size + vid_path.stat().st_size
        assert group.total_size == expected_total
    
    def test_live_photo_group_time_difference(self, temp_dir, create_live_photo_pair):
        """Test que time_difference calcula la diferencia correctamente."""
        img_path, vid_path = create_live_photo_pair(temp_dir, 'IMG_TEST')
        
        # Crear grupo con fechas específicas
        date1 = datetime(2023, 1, 1, 12, 0, 0)
        date2 = datetime(2023, 1, 1, 12, 0, 2)  # 2 segundos después
        
        group = LivePhotoGroup(
            image_path=img_path,
            video_path=vid_path,
            base_name='IMG_TEST',
            directory=temp_dir,
            image_size=100,
            video_size=200,
            image_date=date1,
            video_date=date2
        )
        
        assert group.time_difference == 2.0
    
    def test_live_photo_group_validation_missing_image(self, temp_dir, create_test_video):
        """Test que LivePhotoGroup valida que la imagen existe."""
        vid_path = create_test_video(temp_dir / 'VID_TEST.MOV')
        fake_img_path = temp_dir / 'NONEXISTENT.HEIC'
        
        with pytest.raises(ValueError, match="Imagen no existe"):
            LivePhotoGroup(
                image_path=fake_img_path,
                video_path=vid_path,
                base_name='TEST',
                directory=temp_dir,
                image_size=100,
                video_size=200
            )
    
    def test_live_photo_group_validation_missing_video(self, temp_dir, create_test_image):
        """Test que LivePhotoGroup valida que el video existe."""
        img_path = create_test_image(temp_dir / 'IMG_TEST.HEIC', size=(100, 100))
        fake_vid_path = temp_dir / 'NONEXISTENT.MOV'
        
        with pytest.raises(ValueError, match="Video no existe"):
            LivePhotoGroup(
                image_path=img_path,
                video_path=fake_vid_path,
                base_name='TEST',
                directory=temp_dir,
                image_size=100,
                video_size=200
            )


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoDetectionEdgeCases:
    """Tests de casos edge y situaciones especiales."""
    
    def test_detect_empty_directory(self, temp_dir):
        """Test detección en directorio vacío."""
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False)
        
        assert len(live_photos) == 0
        assert live_photos == []
    
    def test_detect_with_different_extensions(self, temp_dir, create_test_image, create_test_video):
        """Test detección con diferentes extensiones válidas."""
        # Crear con .JPG en vez de .HEIC
        img_path = create_test_image(
            path=temp_dir / 'IMG_0001.JPG',
            size=(100, 100)
        )
        
        vid_path = create_test_video(
            path=temp_dir / 'IMG_0001.MOV'
        )
        
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False)
        
        assert len(live_photos) == 1
        assert live_photos[0].image_path == img_path
        assert live_photos[0].video_path == vid_path
    
    def test_detect_case_insensitive_extensions(self, temp_dir, create_test_image, create_test_video):
        """Test que extensiones son case-insensitive."""
        # Crear con extensiones en minúsculas
        img_path = create_test_image(
            path=temp_dir / 'IMG_0001.heic',
            size=(100, 100)
        )
        
        vid_path = create_test_video(
            path=temp_dir / 'IMG_0001.mov'
        )
        
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False)
        
        # Debe detectar incluso con extensiones en minúsculas
        assert len(live_photos) == 1
    
    def test_detect_with_special_characters_in_name(self, temp_dir, create_test_image, create_test_video):
        """Test detección con caracteres especiales en nombres."""
        base_name = 'IMG_test-photo_001'
        
        img_path = create_test_image(
            path=temp_dir / f'{base_name}.HEIC',
            size=(100, 100)
        )
        
        vid_path = create_test_video(
            path=temp_dir / f'{base_name}.MOV'
        )
        
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False)
        
        assert len(live_photos) == 1
        assert live_photos[0].base_name == base_name
    
    def test_detect_with_progress_callback(self, temp_dir, create_live_photo_pair):
        """Test que progress_callback funciona correctamente."""
        # Crear varios Live Photos
        for i in range(3):
            create_live_photo_pair(temp_dir, f'IMG_{i:04d}')
        
        # Callback para capturar progreso
        progress_calls = []
        
        def callback(current, total, message):
            progress_calls.append((current, total, message))
            return True  # Continuar
        
        # Detectar con callback
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(temp_dir, recursive=False, progress_callback=callback)
        
        # Debe haber llamadas al callback
        assert len(progress_calls) > 0
        assert len(live_photos) == 3
    
    def test_detect_nonexistent_directory(self):
        """Test que detectar en directorio inexistente lanza error."""
        detector = LivePhotoDetector()
        fake_dir = Path('/nonexistent/directory')
        
        with pytest.raises(ValueError, match="Directorio no existe"):
            detector.detect_in_directory(fake_dir, recursive=False)


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoDetectionSampleDirectory:
    """Tests usando el fixture de directorio de muestra."""
    
    def test_sample_directory_structure(self, sample_live_photos_directory):
        """Test la estructura del directorio de muestra."""
        directory, metadata = sample_live_photos_directory
        
        assert directory.exists()
        assert len(metadata['valid_pairs']) == 3
        assert len(metadata['orphan_images']) == 1
        assert len(metadata['orphan_videos']) == 1
    
    def test_detect_in_sample_directory(self, sample_live_photos_directory):
        """Test detección en el directorio de muestra."""
        directory, metadata = sample_live_photos_directory
        
        detector = LivePhotoDetector()
        live_photos = detector.detect_in_directory(directory, recursive=False)
        
        # Debe detectar solo los 3 pares válidos, no los huérfanos
        assert len(live_photos) == 3
        
        # Verificar que detectó los correctos
        detected_bases = {lp.base_name for lp in live_photos}
        expected_bases = {pair['base_name'] for pair in metadata['valid_pairs']}
        assert detected_bases == expected_bases
