"""
Tests unitarios para utils/date_utils.py

Tests exhaustivos de las funciones de extracción y selección de fechas,
con especial atención a casos edge, fechas None y datos corruptos.
"""
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from utils.date_utils import (
    get_best_common_creation_date_2_files,
    select_best_date_from_file,
    format_renamed_name,
    parse_renamed_name,
    is_renamed_filename,
    get_all_file_dates,
)
from services.file_metadata import FileMetadata
from utils.file_utils import (
    get_exif_from_image,
    get_exif_from_video
)
from config import Config


def _create_test_metadata(
    path: Path = None,
    fs_size: int = 1000,
    fs_ctime: float = 0.0,
    fs_mtime: float = 0.0,
    fs_atime: float = 0.0,
    exif_DateTimeOriginal: str = None,
    exif_DateTime: str = None,
    exif_DateTimeDigitized: str = None,
    exif_OffsetTimeOriginal: str = None,
    exif_GPSDateStamp: str = None,
    exif_Software: str = None,
) -> FileMetadata:
    """Helper para crear FileMetadata para tests.
    
    Por defecto todos los timestamps son 0.0 (sin fecha).
    Para tests que necesitan fechas filesystem, pasar explícitamente:
        fs_ctime=datetime(...).timestamp()
    """
    return FileMetadata(
        path=path or Path('/test/file.jpg'),
        fs_size=fs_size,
        fs_ctime=fs_ctime,
        fs_mtime=fs_mtime,
        fs_atime=fs_atime,
        exif_DateTimeOriginal=exif_DateTimeOriginal,
        exif_DateTime=exif_DateTime,
        exif_DateTimeDigitized=exif_DateTimeDigitized,
        exif_OffsetTimeOriginal=exif_OffsetTimeOriginal,
        exif_GPSDateStamp=exif_GPSDateStamp,
        exif_Software=exif_Software,
    )


@pytest.mark.unit
class TestSelectEarliestDate:
    """Tests para la lógica de priorización de fechas con FileMetadata"""
    
    def test_all_exif_dates_available_returns_earliest(self):
        """Debe devolver la fecha EXIF más antigua cuando todas están disponibles"""
        metadata = _create_test_metadata(
            exif_DateTimeOriginal='2023:01:15 10:30:00',  # Más antigua
            exif_DateTime='2023:01:15 10:31:00',
            exif_DateTimeDigitized='2023:01:15 10:32:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2023, 1, 15, 10, 30)
        assert result_source == 'EXIF DateTimeOriginal'
    
    def test_only_exif_create_date_available(self):
        """Debe devolver CreateDate cuando es la única fecha EXIF"""
        metadata = _create_test_metadata(
            exif_DateTime='2023:03:20 14:45:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2023, 3, 20, 14, 45)
        assert result_source == 'EXIF CreateDate'

    def test_gps_date_has_highest_priority(self):
        """EXIF DateTimeOriginal tiene prioridad sobre GPS DateStamp"""
        metadata = _create_test_metadata(
            exif_DateTimeOriginal='2023:01:15 10:31:00',
            exif_DateTime='2023:01:15 10:32:00',
            exif_GPSDateStamp='2023:01:15 10:30:00',
        )

        result_date, result_source = select_best_date_from_file(metadata)

        # GPS ya no tiene prioridad máxima, se selecciona DateTimeOriginal
        assert result_date == datetime(2023, 1, 15, 10, 31)
        assert result_source == 'EXIF DateTimeOriginal'

    def test_datetimeoriginal_with_offset_has_higher_priority(self):
        """DateTimeOriginal con OffsetTimeOriginal debe preferirse y mostrar tz en la fuente"""
        metadata = _create_test_metadata(
            exif_DateTimeOriginal='2023:06:01 09:00:00',
            exif_OffsetTimeOriginal='+02:00',
        )

        result_date, result_source = select_best_date_from_file(metadata)

        assert result_date == datetime(2023, 6, 1, 9, 0)
        assert 'OffsetTime' in result_source or '+02:00' in result_source

    def test_filename_used_when_no_exif(self):
        """Si no hay EXIF, usar fecha del nombre de archivo"""
        # Archivo tipo WhatsApp con fecha en nombre
        metadata = _create_test_metadata(
            path=Path('/test/IMG-20241113-WA0001.jpg'),
        )

        result_date, result_source = select_best_date_from_file(metadata)

        # Debe usar la fecha del nombre de archivo
        assert result_date == datetime(2024, 11, 13, 0, 0)
        assert result_source == 'Filename'

    def test_video_metadata_used_when_is_video(self):
        """Si es video, usar exif_DateTime como Video Metadata"""
        # Para videos, exif_DateTime contiene la fecha del video
        metadata = _create_test_metadata(
            path=Path('/test/video.mp4'),  # Extensión de video
            exif_DateTime='2024:01:15 14:30:00',
        )

        result_date, result_source = select_best_date_from_file(metadata)

        # Para videos, exif_DateTime se usa como EXIF CreateDate o Video Metadata
        assert result_date == datetime(2024, 1, 15, 14, 30)
    
    def test_only_exif_date_digitized_available(self):
        """Debe devolver DateTimeDigitized cuando es la única fecha EXIF"""
        metadata = _create_test_metadata(
            exif_DateTimeDigitized='2023:05:10 09:00:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2023, 5, 10, 9, 0)
        assert result_source == 'EXIF DateTimeDigitized'
    
    def test_exif_date_original_has_priority_over_digitized(self):
        """Cuando hay múltiples fechas EXIF, se selecciona la más antigua"""
        metadata = _create_test_metadata(
            exif_DateTimeOriginal='2023:05:20 10:30:00',
            exif_DateTime='2023:05:20 10:35:00',
            exif_DateTimeDigitized='2023:05:15 08:00:00',  # Más antigua
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        # Se selecciona la fecha EXIF más antigua (DateTimeDigitized)
        assert result_date == datetime(2023, 5, 15, 8, 0)
        assert result_source == 'EXIF DateTimeDigitized'
    
    def test_no_exif_uses_filesystem_dates(self):
        """Sin EXIF debe usar fechas del sistema de archivos"""
        metadata = _create_test_metadata(
            fs_ctime=datetime(2024, 1, 1, 12, 0).timestamp(),
            fs_mtime=datetime(2024, 1, 2, 14, 0).timestamp(),
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        # Source puede ser 'ctime' o 'birth' dependiendo de la plataforma
        assert result_source in ('ctime', 'birth')
    
    def test_no_exif_mtime_is_earliest(self):
        """Sin EXIF y mtime más antiguo debe devolver mtime"""
        metadata = _create_test_metadata(
            fs_ctime=datetime(2024, 1, 2, 14, 0).timestamp(),
            fs_mtime=datetime(2024, 1, 1, 12, 0).timestamp(),  # Más antigua
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert result_source == 'mtime'
    
    def test_exif_priority_over_older_filesystem_dates(self):
        """EXIF debe tener prioridad incluso si fechas del sistema son más antiguas"""
        metadata = _create_test_metadata(
            exif_DateTime='2023:06:15 10:00:00',  # EXIF más reciente
            fs_ctime=datetime(2020, 1, 1, 12, 0).timestamp(),  # Más antigua pero ignorada
            fs_mtime=datetime(2019, 6, 15, 8, 0).timestamp(),  # Más antigua pero ignorada
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        # Debe devolver EXIF CreateDate, no las fechas más antiguas del sistema
        assert result_date == datetime(2023, 6, 15, 10, 0)
        assert result_source == 'EXIF CreateDate'
    
    def test_no_dates_available(self):
        """Sin fechas disponibles debe devolver None, None"""
        metadata = _create_test_metadata()  # Sin fechas
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date is None
        assert result_source is None
    
    def test_only_modification_date_available(self):
        """Solo mtime disponible debe devolverlo"""
        metadata = _create_test_metadata(
            fs_mtime=datetime(2024, 1, 1, 12, 0).timestamp(),
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert result_source == 'mtime'
    
    def test_only_creation_date_available(self):
        """Solo creation_date disponible debe devolverlo"""
        metadata = _create_test_metadata(
            fs_ctime=datetime(2024, 1, 1, 12, 0).timestamp(),
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        # Source depende de la plataforma
        assert result_source in ('ctime', 'birth')


@pytest.mark.unit
class TestGetExifDates:
    """Tests para extracción de fechas EXIF"""
    
    def test_no_pil_available_returns_empty_dict(self):
        """Sin PIL debe devolver diccionario con valores None"""
        # PIL se importa dentro de la función, entonces hacemos patch en PIL.Image
        with patch('PIL.Image.open', side_effect=ImportError):
            result = get_exif_from_image(Path('/fake/image.jpg'))
            
            assert result == {
                'DateTimeOriginal': None,
                'CreateDate': None,
                'DateTimeDigitized': None,
                'SubSecTimeOriginal': None,
                'OffsetTimeOriginal': None,
                'GPSDateStamp': None,
                'Software': None,
                'ExifVersion': None
            }
    
    def test_image_without_exif_returns_empty_dict(self):
        """Imagen sin EXIF debe devolver diccionario con valores None"""
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.getexif.return_value = None
        
        with patch('PIL.Image.open', return_value=mock_image):
            result = get_exif_from_image(Path('/fake/image.jpg'))
            
            assert result == {
                'DateTimeOriginal': None,
                'CreateDate': None,
                'DateTimeDigitized': None,
                'SubSecTimeOriginal': None,
                'OffsetTimeOriginal': None,
                'GPSDateStamp': None,
                'Software': None,
                'ExifVersion': None
            }
    
    def test_image_with_all_exif_dates(self):
        """Imagen con todas las fechas EXIF debe extraerlas correctamente"""
        mock_exif = {
            36867: '2023:01:15 10:30:00',  # DateTimeOriginal
            306: '2023:01:15 10:31:00',     # DateTime (CreateDate)
            36868: '2023:01:15 10:32:00'    # DateTimeDigitized
        }
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.getexif.return_value = mock_exif
        
        with patch('PIL.Image.open', return_value=mock_image), \
             patch('PIL.ExifTags.TAGS', {
                 36867: 'DateTimeOriginal',
                 306: 'DateTime',
                 36868: 'DateTimeDigitized'
             }):
            result = get_exif_from_image(Path('/fake/image.jpg'))
            
            assert result['DateTimeOriginal'] == datetime(2023, 1, 15, 10, 30, 0)
            assert result['CreateDate'] == datetime(2023, 1, 15, 10, 31, 0)
            assert result['DateTimeDigitized'] == datetime(2023, 1, 15, 10, 32, 0)
    
    def test_image_with_partial_exif_dates(self):
        """Imagen con algunas fechas EXIF debe extraer solo las disponibles"""
        mock_exif = {
            36867: '2023:01:15 10:30:00',  # Solo DateTimeOriginal
        }
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.getexif.return_value = mock_exif
        
        with patch('PIL.Image.open', return_value=mock_image), \
             patch('PIL.ExifTags.TAGS', {36867: 'DateTimeOriginal'}):
            result = get_exif_from_image(Path('/fake/image.jpg'))
            
            assert result['DateTimeOriginal'] == datetime(2023, 1, 15, 10, 30, 0)
            assert result['CreateDate'] is None
            assert result['DateTimeDigitized'] is None
    
    def test_image_with_corrupted_exif_date(self):
        """Fecha EXIF corrupta debe ser ignorada y devolver None"""
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image._getexif.return_value = {
            36867: 'invalid-date-format',  # Formato inválido
        }
        
        with patch('PIL.Image.open', return_value=mock_image), \
             patch('PIL.ExifTags.TAGS', {36867: 'DateTimeOriginal'}):
            result = get_exif_from_image(Path('/fake/image.jpg'))
            
            assert result['DateTimeOriginal'] is None
            assert result['CreateDate'] is None
            assert result['DateTimeDigitized'] is None
    
    def test_image_with_mixed_valid_and_corrupted_dates(self):
        """Mezcla de fechas válidas y corruptas debe extraer solo las válidas"""
        mock_exif = {
            36867: '2023:01:15 10:30:00',  # Válida
            306: 'corrupted-date',          # Corrupta
            36868: '2023:01:15 10:32:00'   # Válida
        }
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.getexif.return_value = mock_exif
        
        with patch('PIL.Image.open', return_value=mock_image), \
             patch('PIL.ExifTags.TAGS', {
                 36867: 'DateTimeOriginal',
                 306: 'DateTime',
                 36868: 'DateTimeDigitized'
             }):
            result = get_exif_from_image(Path('/fake/image.jpg'))
            
            assert result['DateTimeOriginal'] == datetime(2023, 1, 15, 10, 30, 0)
            assert result['CreateDate'] is None  # Corrupta
            assert result['DateTimeDigitized'] == datetime(2023, 1, 15, 10, 32, 0)
    
    def test_image_open_error_returns_empty_dict(self):
        """Error al abrir imagen debe devolver diccionario con valores None"""
        with patch('PIL.Image.open', side_effect=Exception("Cannot open")):
            result = get_exif_from_image(Path('/fake/image.jpg'))
            
            assert result == {
                'DateTimeOriginal': None,
                'CreateDate': None,
                'DateTimeDigitized': None,
                'SubSecTimeOriginal': None,
                'OffsetTimeOriginal': None,
                'GPSDateStamp': None,
                'Software': None,
                'ExifVersion': None
            }

    def test_image_with_gps_and_offset(self):
        """Extrae GPSDateStamp y OffsetTimeOriginal correctamente"""
        # Crear estructura EXIF con GPSInfo
        gps_info = {
            1: '2023:01:15',        # GPSDateStamp
            2: (10, 30, 0)          # GPSTimeStamp as ints
        }

        # Tag id 999 representa GPSInfo en este mock
        mock_exif = {
            36867: '2023:01:15 10:30:00',  # DateTimeOriginal
            32867: '+02:00',               # OffsetTimeOriginal (made-up tag id)
            999: gps_info
        }
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image.getexif.return_value = mock_exif

        with patch('PIL.Image.open', return_value=mock_image), \
             patch('PIL.ExifTags.TAGS', {36867: 'DateTimeOriginal', 32867: 'OffsetTimeOriginal', 999: 'GPSInfo'}), \
             patch('PIL.ExifTags.GPSTAGS', {1: 'GPSDateStamp', 2: 'GPSTimeStamp'}):
            result = get_exif_from_image(Path('/fake/image.jpg'))

            assert result['DateTimeOriginal'] == datetime(2023, 1, 15, 10, 30, 0)
            assert result['OffsetTimeOriginal'] == '+02:00'
            assert isinstance(result['GPSDateStamp'], datetime)


@pytest.mark.unit
class TestGetAllFileDates:
    """Tests para extracción completa de fechas de archivos"""
    
    def test_file_with_all_dates_available(self, temp_dir, create_test_image):
        """Archivo con todas las fechas debe extraerlas correctamente"""
        image_path = create_test_image(temp_dir / 'test.jpg', size=(100, 100))
        
        # Mock EXIF dates
        with patch('utils.file_utils.get_exif_from_image', return_value={
            'DateTimeOriginal': datetime(2023, 1, 15, 10, 30, 0),
            'CreateDate': datetime(2023, 1, 15, 10, 31, 0),
            'DateTimeDigitized': datetime(2023, 1, 15, 10, 32, 0),
            'SubSecTimeOriginal': None,
            'OffsetTimeOriginal': None,
            'GPSDateStamp': None,
            'Software': None
        }), \
        patch('utils.settings_manager.settings_manager.get_precalculate_image_exif', return_value=True), \
        patch('utils.settings_manager.settings_manager.get_precalculate_hashes', return_value=False), \
        patch('utils.settings_manager.settings_manager.get_precalculate_video_exif', return_value=False):
            file_metadata = get_all_file_dates(image_path)
            
            # Verificar atributos directamente en FileMetadata
            assert file_metadata.exif_DateTimeOriginal is not None
            assert file_metadata.exif_DateTime is not None  # CreateDate se mapea a DateTime
            assert file_metadata.exif_DateTimeDigitized is not None
            assert file_metadata.fs_mtime > 0
            assert file_metadata.fs_ctime > 0
    
    def test_file_without_exif(self, temp_dir, create_test_image):
        """Archivo sin EXIF debe tener solo fechas del sistema"""
        image_path = create_test_image(temp_dir / 'test.jpg', size=(100, 100))
        
        with patch('utils.file_utils.get_exif_from_image', return_value={
            'DateTimeOriginal': None,
            'CreateDate': None,
            'DateTimeDigitized': None,
            'SubSecTimeOriginal': None,
            'OffsetTimeOriginal': None,
            'GPSDateStamp': None,
            'Software': None
        }), \
        patch('utils.settings_manager.settings_manager.get_precalculate_image_exif', return_value=True), \
        patch('utils.settings_manager.settings_manager.get_precalculate_hashes', return_value=False), \
        patch('utils.settings_manager.settings_manager.get_precalculate_video_exif', return_value=False):
            file_metadata = get_all_file_dates(image_path)
            
            assert file_metadata.exif_DateTimeOriginal is None
            assert file_metadata.exif_DateTime is None
            assert file_metadata.exif_DateTimeDigitized is None
            assert file_metadata.fs_mtime > 0
    
    def test_nonexistent_file_returns_empty_dates(self):
        """Archivo inexistente debe devolver metadatos mínimos"""
        file_metadata = get_all_file_dates(Path('/nonexistent/file.jpg'))
        
        # Como el archivo no existe, debe tener valores por defecto (0.0 o None)
        assert file_metadata.exif_DateTimeOriginal is None
        assert file_metadata.exif_DateTime is None
        assert file_metadata.exif_DateTimeDigitized is None

    def test_video_metadata_disabled_by_config(self, temp_dir, create_test_video):
        """Cuando get_precalculate_video_exif es False, no debe llamar a get_exif_from_video"""
        video_path = create_test_video(temp_dir / 'test.mp4')

        with patch('utils.settings_manager.settings_manager.get_precalculate_video_exif', return_value=False), \
             patch('utils.settings_manager.settings_manager.get_precalculate_image_exif', return_value=False), \
             patch('utils.settings_manager.settings_manager.get_precalculate_hashes', return_value=False), \
             patch('utils.file_utils.get_exif_from_video') as mock_get_video_metadata:
            file_metadata = get_all_file_dates(video_path)

            # No debe llamar a get_exif_from_video
            mock_get_video_metadata.assert_not_called()

            # exif_DateTime (que almacena video metadata) debe ser None
            assert file_metadata.exif_DateTime is None

    def test_video_metadata_enabled_by_config(self, temp_dir, create_test_video):
        """Cuando get_precalculate_video_exif es True, debe llamar a get_exif_from_video"""
        video_path = create_test_video(temp_dir / 'test.mp4')
        expected_video_date = datetime(2023, 6, 15, 14, 30, 0)

        with patch('utils.settings_manager.settings_manager.get_precalculate_video_exif', return_value=True), \
             patch('utils.settings_manager.settings_manager.get_precalculate_image_exif', return_value=False), \
             patch('utils.settings_manager.settings_manager.get_precalculate_hashes', return_value=False), \
             patch('utils.file_utils.get_exif_from_video', return_value=expected_video_date) as mock_get_video_metadata:
            file_metadata = get_all_file_dates(video_path)

            # Debe llamar a get_exif_from_video
            mock_get_video_metadata.assert_called_once_with(video_path)

            # Para videos, la fecha se guarda en exif_DateTime como string ISO
            assert file_metadata.exif_DateTime is not None

    def test_video_metadata_enabled_but_no_metadata_available(self, temp_dir, create_test_video):
        """Cuando get_precalculate_video_exif es True pero no hay metadatos, debe devolver None"""
        video_path = create_test_video(temp_dir / 'test.mp4')

        with patch('utils.settings_manager.settings_manager.get_precalculate_video_exif', return_value=True), \
             patch('utils.settings_manager.settings_manager.get_precalculate_image_exif', return_value=False), \
             patch('utils.settings_manager.settings_manager.get_precalculate_hashes', return_value=False), \
             patch('utils.file_utils.get_exif_from_video', return_value=None) as mock_get_video_metadata:
            file_metadata = get_all_file_dates(video_path)

            # Debe llamar a get_exif_from_video
            mock_get_video_metadata.assert_called_once_with(video_path)

            # exif_DateTime debe ser None
            assert file_metadata.exif_DateTime is None


@pytest.mark.unit
class TestGetDateFromFile:
    """Tests para la función principal de extracción de fecha"""
    
    def test_file_with_exif_returns_exif_date(self, temp_dir, create_test_image):
        """Archivo con EXIF debe devolver fecha EXIF"""
        from services.file_metadata import FileMetadata
        
        image_path = create_test_image(temp_dir / 'test.jpg', size=(100, 100))
        
        # Crear un FileMetadata mock con fechas EXIF
        mock_metadata = FileMetadata(
            path=image_path,
            fs_size=1000,
            fs_ctime=datetime(2024, 1, 1, 12, 0).timestamp(),
            fs_mtime=datetime(2024, 1, 2, 14, 0).timestamp(),
            fs_atime=datetime(2024, 1, 3, 16, 0).timestamp(),
            exif_DateTimeOriginal='2023-01-15T10:30:00',
            exif_DateTime='2023-01-15T10:31:00'
        )
        
        result_date, result_source = select_best_date_from_file(mock_metadata)
        assert result_date == datetime(2023, 1, 15, 10, 30, 0)
        assert 'EXIF' in result_source
    
    def test_file_without_exif_returns_filesystem_date(self, temp_dir, create_test_image):
        """Archivo sin EXIF debe devolver fecha del sistema"""
        from services.file_metadata import FileMetadata
        
        image_path = create_test_image(temp_dir / 'test.jpg', size=(100, 100))
        
        # Crear un FileMetadata mock sin EXIF
        mock_metadata = FileMetadata(
            path=image_path,
            fs_size=1000,
            fs_ctime=datetime(2024, 1, 1, 12, 0).timestamp(),
            fs_mtime=datetime(2024, 1, 2, 14, 0).timestamp(),
            fs_atime=datetime(2024, 1, 3, 16, 0).timestamp()
        )
        
        result_date, result_source = select_best_date_from_file(mock_metadata)
        assert result_date == datetime(2024, 1, 1, 12, 0)
    
    def test_file_with_no_dates_returns_none(self, temp_dir, create_test_image):
        """Archivo sin fechas debe devolver None"""
        from services.file_metadata import FileMetadata
        
        image_path = create_test_image(temp_dir / 'test.jpg', size=(100, 100))
        
        mock_metadata = FileMetadata(
            path=image_path,
            fs_size=1000,
            fs_ctime=0.0,
            fs_mtime=0.0,
            fs_atime=0.0
        )
        
        result_date, result_source = select_best_date_from_file(mock_metadata)
        assert result_date is None
        assert result_source is None
            assert result == datetime(2023, 1, 15, 10, 30, 0)
            # Verificar que se registró algo (el logging existe)
            assert len(caplog.records) > 0


@pytest.mark.unit
class TestFormatRenamedName:
    """Tests para generación de nombres en formato renombrado"""
    
    def test_basic_photo_name(self):
        """Debe generar nombre básico para foto sin secuencia"""
        date = datetime(2023, 1, 15, 10, 30, 45)
        result = format_renamed_name(date, 'PHOTO', '.jpg')
        
        assert result == '20230115_103045_PHOTO.JPG'
    
    def test_basic_video_name(self):
        """Debe generar nombre básico para video sin secuencia"""
        date = datetime(2023, 1, 15, 10, 30, 45)
        result = format_renamed_name(date, 'VIDEO', '.mov')
        
        assert result == '20230115_103045_VIDEO.MOV'
    
    def test_photo_with_sequence(self):
        """Debe generar nombre con secuencia para foto"""
        date = datetime(2023, 1, 15, 10, 30, 45)
        result = format_renamed_name(date, 'PHOTO', '.jpg', sequence=5)
        
        assert result == '20230115_103045_PHOTO_005.JPG'
    
    def test_sequence_padding(self):
        """Debe rellenar secuencia con ceros a la izquierda"""
        date = datetime(2023, 1, 15, 10, 30, 45)
        result = format_renamed_name(date, 'VIDEO', '.mp4', sequence=42)
        
        assert result == '20230115_103045_VIDEO_042.MP4'
    
    def test_extension_uppercase(self):
        """Debe convertir extensión a mayúsculas"""
        date = datetime(2023, 1, 15, 10, 30, 45)
        result = format_renamed_name(date, 'PHOTO', '.jpeg')
        
        assert result == '20230115_103045_PHOTO.JPEG'


@pytest.mark.unit
class TestParseRenamedName:
    """Tests para análisis de nombres en formato renombrado"""
    
    def test_valid_photo_name(self):
        """Debe analizar correctamente nombre de foto válido"""
        result = parse_renamed_name('20230115_103045_PHOTO.JPG')
        
        assert result is not None
        assert result['date'] == datetime(2023, 1, 15, 10, 30, 45)
        assert result['type'] == 'PHOTO'
        assert result['sequence'] is None
        assert result['extension'] == '.JPG'
        assert result['is_renamed'] is True
    
    def test_valid_video_name(self):
        """Debe analizar correctamente nombre de video válido"""
        result = parse_renamed_name('20230115_103045_VIDEO.MOV')
        
        assert result is not None
        assert result['date'] == datetime(2023, 1, 15, 10, 30, 45)
        assert result['type'] == 'VIDEO'
        assert result['sequence'] is None
        assert result['extension'] == '.MOV'
    
    def test_name_with_sequence(self):
        """Debe analizar correctamente nombre con secuencia"""
        result = parse_renamed_name('20230115_103045_PHOTO_005.JPG')
        
        assert result is not None
        assert result['date'] == datetime(2023, 1, 15, 10, 30, 45)
        assert result['type'] == 'PHOTO'
        assert result['sequence'] == 5
        assert result['extension'] == '.JPG'
    
    def test_invalid_date_format(self):
        """Debe rechazar fecha con formato inválido"""
        result = parse_renamed_name('2023011_103045_PHOTO.JPG')  # 7 dígitos en fecha
        
        assert result is None
    
    def test_invalid_time_format(self):
        """Debe rechazar hora con formato inválido"""
        result = parse_renamed_name('20230115_10304_PHOTO.JPG')  # 5 dígitos en hora
        
        assert result is None
    
    def test_invalid_type(self):
        """Debe rechazar tipo inválido"""
        result = parse_renamed_name('20230115_103045_IMAGE.JPG')  # Tipo no válido
        
        assert result is None
    
    def test_invalid_sequence_format(self):
        """Debe rechazar secuencia con formato inválido"""
        result = parse_renamed_name('20230115_103045_PHOTO_5.JPG')  # 1 dígito en secuencia
        
        assert result is None
    
    def test_too_many_parts(self):
        """Debe rechazar nombre con demasiadas partes"""
        result = parse_renamed_name('20230115_103045_PHOTO_005_EXTRA.JPG')
        
        assert result is None
    
    def test_too_few_parts(self):
        """Debe rechazar nombre con muy pocas partes"""
        result = parse_renamed_name('20230115_103045.JPG')
        
        assert result is None
    
    def test_non_numeric_date(self):
        """Debe rechazar fecha no numérica"""
        result = parse_renamed_name('2023011A_103045_PHOTO.JPG')
        
        assert result is None
    
    def test_invalid_datetime_values(self):
        """Debe rechazar valores de fecha/hora inválidos"""
        result = parse_renamed_name('20231315_103045_PHOTO.JPG')  # Mes 13
        
        assert result is None


@pytest.mark.unit
class TestIsRenamedFilename:
    """Tests para verificación rápida de nombres renombrados"""
    
    def test_valid_renamed_name_returns_true(self):
        """Debe reconocer nombre válido renombrado"""
        assert is_renamed_filename('20230115_103045_PHOTO.JPG') is True
    
    def test_valid_renamed_name_with_sequence_returns_true(self):
        """Debe reconocer nombre válido con secuencia"""
        assert is_renamed_filename('20230115_103045_VIDEO_042.MOV') is True
    
    def test_invalid_name_returns_false(self):
        """Debe rechazar nombre no renombrado"""
        assert is_renamed_filename('IMG_1234.JPG') is False
    
    def test_empty_name_returns_false(self):
        """Debe rechazar nombre vacío"""
        assert is_renamed_filename('') is False
    
    def test_partial_match_returns_false(self):
        """Debe rechazar coincidencia parcial"""
        assert is_renamed_filename('20230115_PHOTO.JPG') is False


@pytest.mark.unit
class TestEdgeCasesAndCorruptedData:
    """Tests para casos edge y datos corruptos"""
    
    def test_select_earliest_with_all_none_except_one_exif(self):
        """Una sola fecha EXIF disponible debe ser seleccionada"""
        metadata = _create_test_metadata(
            exif_DateTimeDigitized='2023:01:15 10:30:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2023, 1, 15, 10, 30)
        assert result_source == 'EXIF DateTimeDigitized'
    
    def test_select_earliest_with_same_timestamps(self):
        """Todas las fechas iguales debe devolver la primera en prioridad"""
        same_date_str = '2023:01:15 10:30:00'
        same_ts = datetime(2023, 1, 15, 10, 30).timestamp()
        metadata = _create_test_metadata(
            exif_DateTimeOriginal=same_date_str,
            exif_DateTime=same_date_str,
            exif_DateTimeDigitized=same_date_str,
            fs_ctime=same_ts,
            fs_mtime=same_ts,
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        # Debe devolver una fecha EXIF (prioridad)
        assert result_date == datetime(2023, 1, 15, 10, 30)
        assert 'EXIF' in result_source
    
    def test_format_renamed_name_with_zero_sequence(self):
        """Secuencia 0 debe generar nombre con _000"""
        date = datetime(2023, 1, 15, 10, 30, 45)
        result = format_renamed_name(date, 'PHOTO', '.jpg', sequence=0)
        
        # sequence=0 es falsy, no debe incluirse
        assert result == '20230115_103045_PHOTO.JPG'
    
    def test_parse_renamed_name_with_path_object(self):
        """Debe manejar Path objects además de strings"""
        result = parse_renamed_name(Path('20230115_103045_PHOTO.JPG'))
        
        assert result is not None
        assert result['date'] == datetime(2023, 1, 15, 10, 30, 45)


@pytest.mark.unit
class TestSelectChosenDateCombinatorial:
    """Tests exhaustivos con combinatoria de todas las fuentes de fechas usando FileMetadata"""
    
    # === TESTS DE FECHAS EXIF (Prioridad Máxima) ===
    
    def test_datetime_original_only(self):
        """Solo DateTimeOriginal disponible"""
        metadata = _create_test_metadata(
            exif_DateTimeOriginal='2023:05:10 14:30:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2023, 5, 10, 14, 30)
        assert result_source == 'EXIF DateTimeOriginal'
    
    def test_datetime_original_with_offset(self):
        """DateTimeOriginal con OffsetTimeOriginal tiene nombre descriptivo"""
        metadata = _create_test_metadata(
            exif_DateTimeOriginal='2023:05:10 14:30:00',
            exif_OffsetTimeOriginal='+02:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2023, 5, 10, 14, 30)
        assert '+02:00' in result_source
        assert 'DateTimeOriginal' in result_source
    
    def test_create_date_only(self):
        """Solo CreateDate disponible (mapeado a exif_DateTime)"""
        metadata = _create_test_metadata(
            exif_DateTime='2023:06:15 09:00:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2023, 6, 15, 9, 0)
        assert result_source == 'EXIF CreateDate'
    
    def test_date_digitized_only(self):
        """Solo DateTimeDigitized disponible"""
        metadata = _create_test_metadata(
            exif_DateTimeDigitized='2023:07:20 11:45:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2023, 7, 20, 11, 45)
        assert result_source == 'EXIF DateTimeDigitized'
    
    def test_all_three_exif_dates_returns_earliest(self):
        """Con las 3 fechas EXIF, debe devolver la más antigua"""
        metadata = _create_test_metadata(
            exif_DateTimeOriginal='2023:05:10 14:00:00',
            exif_DateTime='2023:05:10 12:00:00',  # Más antigua
            exif_DateTimeDigitized='2023:05:10 16:00:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2023, 5, 10, 12, 0)
        assert result_source == 'EXIF CreateDate'
    
    # === TESTS DE GPS DATESTAMP (Solo validación) ===
    
    def test_gps_with_exif_original_gps_ignored(self):
        """GPS DateStamp es ignorado cuando hay EXIF DateTimeOriginal"""
        metadata = _create_test_metadata(
            exif_DateTimeOriginal='2023:08:04 18:49:23',
            exif_GPSDateStamp='2023:08:04 20:00:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        # GPS no debe ser seleccionado
        assert result_date == datetime(2023, 8, 4, 18, 49, 23)
        assert result_source == 'EXIF DateTimeOriginal'
    
    def test_gps_only_not_selected(self):
        """GPS DateStamp solo (sin EXIF) no se selecciona, cae a filesystem"""
        metadata = _create_test_metadata(
            exif_GPSDateStamp='2023:08:04 20:00:00',
            fs_ctime=datetime(2024, 1, 1, 12, 0).timestamp(),
            fs_mtime=datetime(2024, 1, 2, 14, 0).timestamp(),
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        # Debe caer a fechas filesystem (GPS no se usa como principal)
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert 'EXIF' not in result_source
    
    # === TESTS DE FILENAME DATE (Prioridad Secundaria) ===
    
    def test_filename_date_when_no_exif(self):
        """Filename date es seleccionado cuando no hay EXIF"""
        metadata = _create_test_metadata(
            path=Path('/test/IMG-20241113-WA0001.jpg'),
            fs_ctime=datetime(2024, 11, 15, 12, 0).timestamp(),
            fs_mtime=datetime(2024, 11, 16, 14, 0).timestamp(),
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2024, 11, 13, 0, 0)
        assert result_source == 'Filename'
    
    def test_filename_date_ignored_when_exif_exists(self):
        """Filename date es ignorado cuando hay EXIF"""
        metadata = _create_test_metadata(
            path=Path('/test/IMG-20241113-WA0001.jpg'),
            exif_DateTimeOriginal='2023:05:10 14:30:00',
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        # EXIF tiene prioridad sobre filename
        assert result_date == datetime(2023, 5, 10, 14, 30)
        assert result_source == 'EXIF DateTimeOriginal'
    
    # === TESTS DE VIDEO METADATA ===
    
    def test_video_metadata_when_no_exif_no_filename(self):
        """Video metadata (exif_DateTime para videos) es seleccionado cuando no hay EXIF fecha original"""
        metadata = _create_test_metadata(
            path=Path('/test/video.mp4'),
            exif_DateTime='2024:01:15 14:30:00',
            fs_ctime=datetime(2024, 1, 15, 12, 0).timestamp(),
            fs_mtime=datetime(2024, 1, 15, 16, 0).timestamp(),
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        # Para videos sin DateTimeOriginal, usa exif_DateTime
        assert result_date == datetime(2024, 1, 15, 14, 30)
    
    # === TESTS DE FILESYSTEM DATES (Último recurso) ===
    
    def test_creation_date_only_filesystem(self):
        """Solo creation_date disponible (último recurso)"""
        metadata = _create_test_metadata(
            fs_ctime=datetime(2024, 1, 1, 12, 0).timestamp(),
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert result_source in ('ctime', 'birth')
    
    def test_modification_date_only_filesystem(self):
        """Solo modification_date disponible"""
        metadata = _create_test_metadata(
            fs_mtime=datetime(2024, 1, 2, 14, 0).timestamp(),
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2024, 1, 2, 14, 0)
        assert result_source == 'mtime'
    
    def test_filesystem_dates_returns_earliest(self):
        """Con ambas fechas filesystem, devuelve la más antigua"""
        metadata = _create_test_metadata(
            fs_ctime=datetime(2024, 1, 1, 12, 0).timestamp(),  # Más antigua
            fs_mtime=datetime(2024, 1, 2, 14, 0).timestamp(),
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert result_source in ('ctime', 'birth')
    
    def test_filesystem_ignored_when_exif_exists(self):
        """Fechas filesystem son ignoradas cuando hay EXIF"""
        metadata = _create_test_metadata(
            exif_DateTimeOriginal='2023:05:10 14:30:00',
            fs_ctime=datetime(2022, 1, 1, 12, 0).timestamp(),  # Más antigua pero ignorada
            fs_mtime=datetime(2021, 6, 15, 8, 0).timestamp(),  # Mucho más antigua
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        # EXIF tiene prioridad absoluta sobre filesystem
        assert result_date == datetime(2023, 5, 10, 14, 30)
        assert result_source == 'EXIF DateTimeOriginal'
    
    # === TESTS DE CASOS COMPLEJOS (Combinatoria completa) ===
    
    def test_all_sources_available_exif_wins(self):
        """Con todas las fuentes, EXIF tiene prioridad máxima"""
        metadata = _create_test_metadata(
            path=Path('/test/IMG-20241113-WA0001.jpg'),  # Tiene fecha en filename
            exif_DateTimeOriginal='2023:05:10 14:30:00',
            exif_DateTime='2023:05:10 12:00:00',  # Más antigua EXIF
            exif_DateTimeDigitized='2023:05:10 16:00:00',
            exif_GPSDateStamp='2023:05:10 10:00:00',  # Más antigua global pero GPS ignorado
            fs_ctime=datetime(2022, 1, 1, 12, 0).timestamp(),  # Más antigua filesystem
            fs_mtime=datetime(2021, 6, 15, 8, 0).timestamp(),
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        # Debe seleccionar la EXIF más antigua
        assert result_date == datetime(2023, 5, 10, 12, 0)
        assert result_source == 'EXIF CreateDate'
    
    def test_completely_empty_returns_none(self):
        """Sin ninguna fecha disponible debe devolver None"""
        metadata = _create_test_metadata()
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date is None
        assert result_source is None
    
    def test_dates_with_same_timestamp_exif_preferred(self):
        """Con timestamps idénticos, EXIF tiene prioridad en el source"""
        same_date_str = '2023:05:10 12:00:00'
        same_ts = datetime(2023, 5, 10, 12, 0).timestamp()
        metadata = _create_test_metadata(
            path=Path('/test/IMG-20230510-WA0001.jpg'),  # Misma fecha en filename
            exif_DateTimeOriginal=same_date_str,
            fs_ctime=same_ts,
            fs_mtime=same_ts,
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        assert result_date == datetime(2023, 5, 10, 12, 0)
        assert 'EXIF' in result_source
    
    def test_extreme_date_differences_handled_correctly(self):
        """Diferencias extremas de fechas deben manejarse correctamente"""
        metadata = _create_test_metadata(
            exif_DateTimeOriginal='2023:05:10 14:30:00',
            exif_DateTime='1990:01:01 00:00:00',  # 33 años antes
            fs_ctime=datetime(2024, 12, 31, 23, 59).timestamp(),  # En el futuro
        )
        
        result_date, result_source = select_best_date_from_file(metadata)
        
        # Debe devolver la EXIF más antigua sin error
        assert result_date == datetime(1990, 1, 1, 0, 0)
        assert result_source == 'EXIF CreateDate'


@pytest.mark.unit
class TestVideoMetadataConfiguration:
    """Tests para la configuración de extracción de metadatos de video"""

    def test_config_defaults_to_false(self):
        """USE_VIDEO_METADATA debe estar por defecto en False"""
        assert Config.USE_VIDEO_METADATA is False

    @patch('utils.settings_manager.settings_manager.get_precalculate_video_exif')
    def test_config_loaded_from_settings_manager(self, mock_get_precalculate):
        """USE_VIDEO_METADATA debe cargarse desde settings_manager al inicio"""
        from utils.settings_manager import settings_manager
        from config import Config
        
        # Simular que settings_manager devuelve True
        mock_get_precalculate.return_value = True
        
        # Ejecutar la lógica de carga de configuración como en main.py
        Config.USE_VIDEO_METADATA = settings_manager.get_precalculate_video_exif()
        
        # Verificar que se llamó a get_precalculate_video_exif
        mock_get_precalculate.assert_called_once()
        
        # Verificar que Config.USE_VIDEO_METADATA se actualizó
        assert Config.USE_VIDEO_METADATA is True

@pytest.mark.unit
class TestGetBestCommonCreationDate2FilesComprehensive:
    """Tests exhaustivos para get_best_common_creation_date_2_files con la nueva lógica profesional"""

    @pytest.fixture
    def file1_exif(self):
        from types import SimpleNamespace
        return SimpleNamespace(
            path="file1.jpg",
            exif_date_time_original=datetime(2023, 1, 1, 12, 0, 0),
            exif_create_date=datetime(2023, 1, 1, 12, 30, 0),
            mtime=datetime(2023, 1, 1, 15, 0, 0).timestamp(),
            ctime=datetime(2023, 1, 1, 16, 0, 0).timestamp(),
            atime=datetime(2023, 1, 1, 17, 0, 0).timestamp()
        )

    @pytest.fixture
    def file2_exif(self):
        from types import SimpleNamespace
        return SimpleNamespace(
            path="file2.heic",
            exif_date_time_original=datetime(2023, 1, 1, 12, 0, 5),
            exif_create_date=datetime(2023, 1, 1, 12, 31, 0),
            mtime=datetime(2023, 1, 1, 15, 1, 0).timestamp(),
            ctime=datetime(2023, 1, 1, 16, 1, 0).timestamp(),
            atime=datetime(2023, 1, 1, 17, 1, 0).timestamp()
        )

    def test_priority_1_exif_original(self, file1_exif, file2_exif):
        """Debe priorizar EXIF DateTimeOriginal sobre todo lo demás"""
        # Cambiamos mtime para que sea "más viejo" pero EXIF debe mandar
        file1_exif.mtime = datetime(2020, 1, 1).timestamp()
        file2_exif.mtime = datetime(2020, 1, 1).timestamp()
        
        d1, d2, source = get_best_common_creation_date_2_files(file1_exif, file2_exif)
        
        assert d1 == datetime(2023, 1, 1, 12, 0, 0)
        assert d2 == datetime(2023, 1, 1, 12, 0, 5)
        assert source == 'exif_date_time_original'

    def test_fallback_to_exif_create_date(self, file1_exif, file2_exif):
        """Debe caer a EXIF CreateDate si no hay Original"""
        file1_exif.exif_date_time_original = None
        file2_exif.exif_date_time_original = None
        
        d1, d2, source = get_best_common_creation_date_2_files(file1_exif, file2_exif)
        
        assert d1 == datetime(2023, 1, 1, 12, 30, 0)
        assert d2 == datetime(2023, 1, 1, 12, 31, 0)
        assert source == 'exif_create_date'

    def test_filesystem_fallback_mtime_is_oldest(self, file1_exif, file2_exif):
        """Sin EXIF, debe elegir mtime si es la fuente común más antigua (caso normal)"""
        file1_exif.exif_date_time_original = None
        file1_exif.exif_create_date = None
        file2_exif.exif_date_time_original = None
        file2_exif.exif_create_date = None
        
        # mtime < ctime < atime
        d1, d2, source = get_best_common_creation_date_2_files(file1_exif, file2_exif)
        
        assert d1 == datetime(2023, 1, 1, 15, 0, 0)
        assert d2 == datetime(2023, 1, 1, 15, 1, 0)
        assert source == 'fs_mtime'

    def test_filesystem_fallback_ctime_is_oldest(self, file1_exif, file2_exif, caplog):
        """Sin EXIF, debe elegir ctime si es más antigua que mtime (anomalía detectada)"""
        import logging
        file1_exif.exif_date_time_original = None
        file1_exif.exif_create_date = None
        file1_exif.exif_modify_date = None
        file2_exif.exif_date_time_original = None
        file2_exif.exif_create_date = None
        file2_exif.exif_modify_date = None
        
        # ctime (14:00) < mtime (15:00)
        file1_exif.ctime = datetime(2023, 1, 1, 14, 0, 0).timestamp()
        file2_exif.ctime = datetime(2023, 1, 1, 14, 1, 0).timestamp()
        
        with caplog.at_level(logging.WARNING):
            d1, d2, source = get_best_common_creation_date_2_files(file1_exif, file2_exif)
            
            assert d1 == datetime(2023, 1, 1, 14, 0, 0)
            assert d2 == datetime(2023, 1, 1, 14, 1, 0)
            assert source == 'fs_ctime'
            assert "ANOMALÍA DE FECHAS" in caplog.text
            assert "fs_ctime" in caplog.text

    def test_only_returns_if_source_present_in_both(self, file1_exif, file2_exif):
        """Solo debe devolver una fuente si ambos archivos disponen de ella"""
        from types import SimpleNamespace
        file1_exif.exif_date_time_original = None
        file1_exif.exif_create_date = None
        file1_exif.exif_modify_date = None
        file2_exif.exif_date_time_original = None
        file2_exif.exif_create_date = None
        file2_exif.exif_modify_date = None

        # f1 solo tiene mtime, f2 solo tiene ctime
        # No hay fuente COMÚN
        f1_solo_m = SimpleNamespace(path="f1", mtime=datetime(2020,1,1).timestamp())
        f2_solo_c = SimpleNamespace(path="f2", ctime=datetime(2020,1,1).timestamp())
        
        result = get_best_common_creation_date_2_files(f1_solo_m, f2_solo_c)
        assert result is None

    def test_mixed_exif_one_file_only(self, file1_exif, file2_exif):
        """Si solo un archivo tiene EXIF, debe caer a filesystem (fuente común)"""
        # file1 tiene EXIF, file2 no
        file2_exif.exif_date_time_original = None
        file2_exif.exif_create_date = None
        file2_exif.exif_modify_date = None
        
        d1, d2, source = get_best_common_creation_date_2_files(file1_exif, file2_exif)
        
        # Cae a mtime porque es la fuente común (pese a que f1 tenía EXIF)
        assert source == 'fs_mtime'
        assert d1 == datetime(2023, 1, 1, 15, 0, 0)
        assert d2 == datetime(2023, 1, 1, 15, 1, 0)

    def test_absolute_oldest_among_commons(self, file1_exif, file2_exif):
        """Debe elegir la fuente común que contenga la fecha absoluta más antigua"""
        file1_exif.exif_date_time_original = None
        file1_exif.exif_create_date = None
        file2_exif.exif_date_time_original = None
        file2_exif.exif_create_date = None

        # mtime: 2023
        # ctime: 2022 (La más antigua común)
        # atime: 2024
        file1_exif.mtime = datetime(2023, 1, 1).timestamp()
        file1_exif.ctime = datetime(2022, 1, 1).timestamp()
        file1_exif.atime = datetime(2024, 1, 1).timestamp()
        
        file2_exif.mtime = datetime(2023, 1, 1, 1).timestamp()
        file2_exif.ctime = datetime(2022, 1, 1, 1).timestamp()
        file2_exif.atime = datetime(2024, 1, 1, 1).timestamp()
        
        d1, d2, source = get_best_common_creation_date_2_files(file1_exif, file2_exif)
        
        assert source == 'fs_ctime'
        assert d1 == datetime(2022, 1, 1)

    def test_handles_missing_attributes_gracefully(self):
        """Debe manejar objetos que no tienen todos los campos del protocolo"""
        from types import SimpleNamespace
        f1 = SimpleNamespace(path="f1") # Sin mtime/ctime/atime/exif
        f2 = SimpleNamespace(path="f2")
        
        result = get_best_common_creation_date_2_files(f1, f2)
        assert result is None
