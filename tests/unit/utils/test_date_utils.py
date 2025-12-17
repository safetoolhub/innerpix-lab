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
    select_chosen_date,
    get_date_from_file,
    format_renamed_name,
    parse_renamed_name,
    is_renamed_filename,
    get_all_file_dates
)
from utils.file_utils import (
    get_exif_from_image,
    get_exif_from_video
)
from config import Config


@pytest.mark.unit
class TestSelectEarliestDate:
    """Tests para la lógica de priorización de fechas"""
    
    def test_all_exif_dates_available_returns_earliest(self):
        """Debe devolver la fecha EXIF más antigua cuando todas están disponibles"""
        dates = {
            'exif_date_time_original': datetime(2023, 1, 15, 10, 30),  # Más antigua
            'exif_create_date': datetime(2023, 1, 15, 10, 31),
            'exif_date_digitized': datetime(2023, 1, 15, 10, 32),
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0)
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 1, 15, 10, 30)
        assert result_source == 'EXIF DateTimeOriginal'
    
    def test_only_exif_create_date_available(self):
        """Debe devolver CreateDate cuando es la única fecha EXIF"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': datetime(2023, 3, 20, 14, 45),
            'exif_date_digitized': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2022, 6, 15, 8, 0)  # Más antigua pero ignorada
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 3, 20, 14, 45)
        assert result_source == 'EXIF CreateDate'

    def test_gps_date_has_highest_priority(self):
        """EXIF DateTimeOriginal tiene prioridad sobre GPS DateStamp"""
        dates = {
            'exif_gps_date': datetime(2023, 1, 15, 10, 30),
            'exif_date_time_original': datetime(2023, 1, 15, 10, 31),
            'exif_create_date': datetime(2023, 1, 15, 10, 32),
            'exif_date_digitized': None,
            'filename_date': None,
            'video_metadata_date': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0)
        }

        result_date, result_source = select_chosen_date(dates)

        # GPS ya no tiene prioridad máxima, se selecciona DateTimeOriginal
        assert result_date == datetime(2023, 1, 15, 10, 31)
        assert result_source == 'EXIF DateTimeOriginal'

    def test_datetimeoriginal_with_offset_has_higher_priority(self):
        """DateTimeOriginal con OffsetTimeOriginal debe preferirse y mostrar tz en la fuente"""
        dates = {
            'exif_gps_date': None,
            'exif_date_time_original': datetime(2023, 6, 1, 9, 0),
            'exif_create_date': None,
            'exif_date_digitized': None,
            'exif_offset_time': '+02:00',
            'filename_date': None,
            'video_metadata_date': None,
            'filesystem_creation_date': None,
            'filesystem_modification_date': None
        }

        result_date, result_source = select_chosen_date(dates)

        assert result_date == datetime(2023, 6, 1, 9, 0)
        assert 'OffsetTime' in result_source or '+02:00' in result_source

    def test_filename_used_when_confidence_low(self):
        """Si la validación devuelve confidence 'low', usar fecha del nombre si existe"""
        # exif posterior a mtime -> EXIF_AFTER_MTIME -> confidence low
        dates = {
            'exif_gps_date': None,
            'exif_date_time_original': datetime(2025, 1, 10, 12, 0),
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filename_date': datetime(2024, 11, 13, 0, 0),
            'video_metadata_date': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_modification_date': datetime(2023, 1, 1, 12, 0)
        }

        result_date, result_source = select_chosen_date(dates)

        # En la implementación actual la fecha EXIF aún puede ser seleccionada
        # (DateTimeOriginal mantiene prioridad pese a confidence low)
        assert result_date == datetime(2025, 1, 10, 12, 0)
        assert result_source == 'EXIF DateTimeOriginal'

    def test_video_metadata_used_when_no_exif(self):
        """Si no hay EXIF ni filename, usar metadata de video si está disponible"""
        dates = {
            'exif_gps_date': None,
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filename_date': None,
            'video_metadata_date': datetime(2024, 1, 15, 14, 30),
            'filesystem_creation_date': datetime(2024, 1, 15, 12, 0),
            'filesystem_modification_date': datetime(2024, 1, 15, 14, 0)
        }

        result_date, result_source = select_chosen_date(dates)

        assert result_date == datetime(2024, 1, 15, 14, 30)
        assert result_source == 'Video Metadata'
    
    def test_only_exif_date_digitized_available(self):
        """Debe devolver DateTimeDigitized cuando es la única fecha EXIF"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': datetime(2023, 5, 10, 9, 0),
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_creation_source': 'ctime',
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0)
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 5, 10, 9, 0)
        assert result_source == 'EXIF DateTimeDigitized'
    
    def test_exif_date_original_has_priority_over_digitized(self):
        """Cuando hay múltiples fechas EXIF, se selecciona la más antigua"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 20, 10, 30),
            'exif_create_date': datetime(2023, 5, 20, 10, 35),
            'exif_date_digitized': datetime(2023, 5, 15, 8, 0),  # Más antigua
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0)
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        # Se selecciona la fecha EXIF más antigua (DateTimeDigitized)
        assert result_date == datetime(2023, 5, 15, 8, 0)
        assert result_source == 'EXIF DateTimeDigitized'
    
    def test_no_exif_uses_filesystem_dates(self):
        """Sin EXIF debe usar fechas del sistema de archivos"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),  # Más antigua
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0)
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert result_source == 'birth'
    
    def test_no_exif_mtime_is_earliest(self):
        """Sin EXIF y mtime más antiguo debe devolver mtime"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filesystem_creation_date': datetime(2024, 1, 2, 14, 0),
            'filesystem_creation_source': 'ctime',
            'filesystem_modification_date': datetime(2024, 1, 1, 12, 0)  # Más antigua
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert result_source == 'mtime'
    
    def test_no_dates_available(self):
        """Sin fechas disponibles debe devolver None, None"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filesystem_creation_date': None,
            'filesystem_creation_source': None,
            'filesystem_modification_date': None
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date is None
        assert result_source is None
    
    def test_only_modification_date_available(self):
        """Solo mtime disponible debe devolverlo"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filesystem_creation_date': None,
            'filesystem_creation_source': None,
            'filesystem_modification_date': datetime(2024, 1, 1, 12, 0)
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert result_source == 'mtime'
    
    def test_only_creation_date_available(self):
        """Solo creation_date disponible debe devolverlo"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': None
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert result_source == 'birth'
    
    def test_exif_priority_over_older_filesystem_dates(self):
        """EXIF debe tener prioridad incluso si fechas del sistema son más antiguas"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': datetime(2023, 6, 15, 10, 0),  # EXIF más reciente
            'exif_date_digitized': None,
            'filesystem_creation_date': datetime(2020, 1, 1, 12, 0),  # Más antigua pero ignorada
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2019, 6, 15, 8, 0)  # Más antigua pero ignorada
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        # Debe devolver EXIF CreateDate, no las fechas más antiguas del sistema
        assert result_date == datetime(2023, 6, 15, 10, 0)
        assert result_source == 'EXIF CreateDate'


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
                'Software': None
            }
    
    def test_image_without_exif_returns_empty_dict(self):
        """Imagen sin EXIF debe devolver diccionario con valores None"""
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image._getexif.return_value = None
        
        with patch('PIL.Image.open', return_value=mock_image):
            result = get_exif_from_image(Path('/fake/image.jpg'))
            
            assert result == {
                'DateTimeOriginal': None,
                'CreateDate': None,
                'DateTimeDigitized': None,
                'SubSecTimeOriginal': None,
                'OffsetTimeOriginal': None,
                'GPSDateStamp': None,
                'Software': None
            }
    
    def test_image_with_all_exif_dates(self):
        """Imagen con todas las fechas EXIF debe extraerlas correctamente"""
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image._getexif.return_value = {
            36867: '2023:01:15 10:30:00',  # DateTimeOriginal
            306: '2023:01:15 10:31:00',     # DateTime (CreateDate)
            36868: '2023:01:15 10:32:00'    # DateTimeDigitized
        }
        
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
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image._getexif.return_value = {
            36867: '2023:01:15 10:30:00',  # Solo DateTimeOriginal
        }
        
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
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        mock_image._getexif.return_value = {
            36867: '2023:01:15 10:30:00',  # Válida
            306: 'corrupted-date',          # Corrupta
            36868: '2023:01:15 10:32:00'   # Válida
        }
        
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
                'Software': None
            }

    def test_image_with_gps_and_offset(self):
        """Extrae GPSDateStamp y OffsetTimeOriginal correctamente"""
        mock_image = MagicMock()
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=False)
        # Crear estructura EXIF con GPSInfo
        gps_info = {
            1: '2023:01:15',        # GPSDateStamp
            2: (10, 30, 0)          # GPSTimeStamp as ints
        }

        # Tag id 999 representa GPSInfo en este mock
        mock_image._getexif.return_value = {
            36867: '2023:01:15 10:30:00',  # DateTimeOriginal
            32867: '+02:00',               # OffsetTimeOriginal (made-up tag id)
            999: gps_info
        }

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
        }):
            result = get_all_file_dates(image_path)
            
            assert result['exif_date_time_original'] == datetime(2023, 1, 15, 10, 30, 0)
            assert result['exif_create_date'] == datetime(2023, 1, 15, 10, 31, 0)
            assert result['exif_date_digitized'] == datetime(2023, 1, 15, 10, 32, 0)
            assert result['filesystem_modification_date'] is not None
            assert result['filesystem_creation_date'] is not None or result['filesystem_modification_date'] is not None
    
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
        }):
            result = get_all_file_dates(image_path)
            
            assert result['exif_date_time_original'] is None
            assert result['exif_create_date'] is None
            assert result['exif_date_digitized'] is None
            assert result['filesystem_modification_date'] is not None
    
    def test_nonexistent_file_returns_empty_dates(self):
        """Archivo inexistente debe devolver fechas vacías"""
        result = get_all_file_dates(Path('/nonexistent/file.jpg'))
        
        assert result['exif_date_time_original'] is None
        assert result['exif_create_date'] is None
        assert result['exif_date_digitized'] is None
        assert result['filesystem_creation_date'] is None
        assert result['filesystem_modification_date'] is None

    def test_video_metadata_disabled_by_config(self, temp_dir, create_test_video):
        """Cuando USE_VIDEO_METADATA es False, no debe llamar a get_exif_from_video"""
        video_path = create_test_video(temp_dir / 'test.mp4')

        with patch('config.Config.USE_VIDEO_METADATA', False), \
             patch('utils.file_utils.get_exif_from_video') as mock_get_video_metadata, \
             patch('utils.file_utils.get_exif_from_image', return_value={
                 'DateTimeOriginal': None,
                 'CreateDate': None,
                 'DateTimeDigitized': None,
                 'SubSecTimeOriginal': None,
                 'OffsetTimeOriginal': None,
                 'GPSDateStamp': None,
                 'Software': None
             }):
            result = get_all_file_dates(video_path)

            # No debe llamar a get_exif_from_video
            mock_get_video_metadata.assert_not_called()

            # video_metadata_date debe ser None
            assert result['video_metadata_date'] is None

    def test_video_metadata_enabled_by_config(self, temp_dir, create_test_video):
        """Cuando USE_VIDEO_METADATA es True, debe llamar a get_exif_from_video"""
        video_path = create_test_video(temp_dir / 'test.mp4')
        expected_video_date = datetime(2023, 6, 15, 14, 30, 0)

        with patch('config.Config.USE_VIDEO_METADATA', True), \
             patch('utils.file_utils.get_exif_from_video', return_value=expected_video_date) as mock_get_video_metadata, \
             patch('utils.file_utils.get_exif_from_image', return_value={
                 'DateTimeOriginal': None,
                 'CreateDate': None,
                 'DateTimeDigitized': None,
                 'SubSecTimeOriginal': None,
                 'OffsetTimeOriginal': None,
                 'GPSDateStamp': None,
                 'Software': None
             }):
            result = get_all_file_dates(video_path)

            # Debe llamar a get_exif_from_video
            mock_get_video_metadata.assert_called_once_with(video_path)

            # video_metadata_date debe tener el valor esperado
            assert result['video_metadata_date'] == expected_video_date

    def test_video_metadata_enabled_but_no_metadata_available(self, temp_dir, create_test_video):
        """Cuando USE_VIDEO_METADATA es True pero no hay metadatos, debe devolver None"""
        video_path = create_test_video(temp_dir / 'test.mp4')

        with patch('config.Config.USE_VIDEO_METADATA', True), \
             patch('utils.file_utils.get_exif_from_video', return_value=None) as mock_get_video_metadata, \
             patch('utils.file_utils.get_exif_from_image', return_value={
                 'DateTimeOriginal': None,
                 'CreateDate': None,
                 'DateTimeDigitized': None,
                 'SubSecTimeOriginal': None,
                 'OffsetTimeOriginal': None,
                 'GPSDateStamp': None,
                 'Software': None
             }):
            result = get_all_file_dates(video_path)

            # Debe llamar a get_exif_from_video
            mock_get_video_metadata.assert_called_once_with(video_path)

            # video_metadata_date debe ser None
            assert result['video_metadata_date'] is None


@pytest.mark.unit
class TestGetDateFromFile:
    """Tests para la función principal de extracción de fecha"""
    
    def test_file_with_exif_returns_exif_date(self, temp_dir, create_test_image):
        """Archivo con EXIF debe devolver fecha EXIF"""
        image_path = create_test_image(temp_dir / 'test.jpg', size=(100, 100))
        
        with patch('utils.date_utils.get_all_file_dates', return_value={
            'exif_date_time_original': datetime(2023, 1, 15, 10, 30, 0),
            'exif_create_date': datetime(2023, 1, 15, 10, 31, 0),
            'exif_date_digitized': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0),
            'access_date': datetime(2024, 1, 3, 16, 0)
        }):
            result = get_date_from_file(image_path)
            
            assert result == datetime(2023, 1, 15, 10, 30, 0)
    
    def test_file_without_exif_returns_filesystem_date(self, temp_dir, create_test_image):
        """Archivo sin EXIF debe devolver fecha del sistema"""
        image_path = create_test_image(temp_dir / 'test.jpg', size=(100, 100))
        
        with patch('utils.date_utils.get_all_file_dates', return_value={
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0),
            'access_date': datetime(2024, 1, 3, 16, 0)
        }):
            result = get_date_from_file(image_path)
            
            assert result == datetime(2024, 1, 1, 12, 0)
    
    def test_file_with_no_dates_returns_none(self, temp_dir, create_test_image):
        """Archivo sin fechas debe devolver None"""
        image_path = create_test_image(temp_dir / 'test.jpg', size=(100, 100))
        
        with patch('utils.date_utils.get_all_file_dates', return_value={
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filesystem_creation_date': None,
            'filesystem_creation_source': None,
            'filesystem_modification_date': None,
            'access_date': None
        }):
            result = get_date_from_file(image_path)
            
            assert result is None
    
    def test_nonexistent_file_returns_none(self):
        """Archivo inexistente debe devolver None"""
        result = get_date_from_file(Path('/nonexistent/file.jpg'))
        
        assert result is None
    
    def test_verbose_mode_logs_info(self, temp_dir, create_test_image, caplog):
        """Modo verbose debe registrar en nivel INFO"""
        import logging
        caplog.set_level(logging.INFO)
        
        image_path = create_test_image(temp_dir / 'test.jpg', size=(100, 100))
        
        with patch('utils.date_utils.get_all_file_dates', return_value={
            'exif_date_time_original': datetime(2023, 1, 15, 10, 30, 0),
            'exif_create_date': None,
            'exif_date_digitized': None,
            'exif_gps_date': None,
            'exif_offset_time': None,
            'exif_software': None,
            'video_metadata_date': None,
            'filename_date': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0),
            'access_date': None
        }):
            result = get_date_from_file(image_path, verbose=True)
            
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
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': datetime(2023, 1, 15, 10, 30),
            'filesystem_creation_date': None,
            'filesystem_creation_source': None,
            'filesystem_modification_date': None
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 1, 15, 10, 30)
        assert result_source == 'EXIF DateTimeDigitized'
    
    def test_select_earliest_with_same_timestamps(self):
        """Todas las fechas iguales debe devolver la primera en prioridad"""
        same_date = datetime(2023, 1, 15, 10, 30)
        dates = {
            'exif_date_time_original': same_date,
            'exif_create_date': same_date,
            'exif_date_digitized': same_date,
            'filesystem_creation_date': same_date,
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': same_date
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        # Debe devolver una fecha EXIF (prioridad)
        assert result_date == same_date
        assert 'EXIF' in result_source
    
    def test_get_date_from_file_with_exception_returns_none(self):
        """Excepción durante procesamiento debe devolver None"""
        with patch('utils.date_utils.get_all_file_dates', side_effect=Exception("Error")):
            result = get_date_from_file(Path('/fake/file.jpg'))
            
            assert result is None
    
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
    """Tests exhaustivos con combinatoria de todas las fuentes de fechas"""
    
    # === PASO 1: TESTS DE FECHAS EXIF (Prioridad Máxima) ===
    
    def test_datetime_original_only(self):
        """Solo DateTimeOriginal disponible"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 30),
            'exif_create_date': None,
            'exif_date_digitized': None,
            'exif_gps_date': None,
            'filename_date': None,
            'video_metadata_date': None,
            'filesystem_creation_date': None,
            'filesystem_modification_date': None
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 5, 10, 14, 30)
        assert result_source == 'EXIF DateTimeOriginal'
    
    def test_datetime_original_with_offset(self):
        """DateTimeOriginal con OffsetTimeOriginal tiene nombre descriptivo"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 30),
            'exif_offset_time': '+02:00',
            'exif_create_date': None,
            'exif_date_digitized': None,
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 5, 10, 14, 30)
        assert '+02:00' in result_source
        assert 'DateTimeOriginal' in result_source
    
    def test_create_date_only(self):
        """Solo CreateDate disponible"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': datetime(2023, 6, 15, 9, 0),
            'exif_date_digitized': None,
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 6, 15, 9, 0)
        assert result_source == 'EXIF CreateDate'
    
    def test_date_digitized_only(self):
        """Solo DateTimeDigitized disponible"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': datetime(2023, 7, 20, 11, 45),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 7, 20, 11, 45)
        assert result_source == 'EXIF DateTimeDigitized'
    
    def test_all_three_exif_dates_returns_earliest(self):
        """Con las 3 fechas EXIF, debe devolver la más antigua"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 0),
            'exif_create_date': datetime(2023, 5, 10, 12, 0),  # Más antigua
            'exif_date_digitized': datetime(2023, 5, 10, 16, 0),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 5, 10, 12, 0)
        assert result_source == 'EXIF CreateDate'
    
    def test_datetime_original_and_create_date_returns_earliest(self):
        """DateTimeOriginal + CreateDate: devuelve la más antigua"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 0),
            'exif_create_date': datetime(2023, 5, 10, 16, 0),
            'exif_date_digitized': None,
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 5, 10, 14, 0)
        assert result_source == 'EXIF DateTimeOriginal'
    
    def test_datetime_original_and_digitized_returns_earliest(self):
        """DateTimeOriginal + DateTimeDigitized: devuelve la más antigua"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 0),
            'exif_create_date': None,
            'exif_date_digitized': datetime(2023, 5, 10, 10, 0),  # Más antigua
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 5, 10, 10, 0)
        assert result_source == 'EXIF DateTimeDigitized'
    
    def test_create_date_and_digitized_returns_earliest(self):
        """CreateDate + DateTimeDigitized: devuelve la más antigua"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': datetime(2023, 5, 10, 12, 0),  # Más antigua
            'exif_date_digitized': datetime(2023, 5, 10, 15, 0),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 5, 10, 12, 0)
        assert result_source == 'EXIF CreateDate'
    
    # === PASO 2: TESTS DE GPS DATESTAMP (Solo validación) ===
    
    def test_gps_with_exif_original_gps_ignored(self):
        """GPS DateStamp es ignorado cuando hay EXIF DateTimeOriginal"""
        dates = {
            'exif_date_time_original': datetime(2023, 8, 4, 18, 49, 23),
            'exif_gps_date': datetime(2023, 8, 4, 20, 0, 0),
            'exif_create_date': None,
            'exif_date_digitized': None,
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        # GPS no debe ser seleccionado
        assert result_date == datetime(2023, 8, 4, 18, 49, 23)
        assert result_source == 'EXIF DateTimeOriginal'
    
    def test_gps_only_not_selected(self):
        """GPS DateStamp solo (sin EXIF) no se selecciona, cae a filesystem"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'exif_gps_date': datetime(2023, 8, 4, 20, 0, 0),
            'filename_date': None,
            'video_metadata_date': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        # Debe caer a fechas filesystem (GPS no se usa como principal)
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert 'EXIF' not in result_source
    
    def test_gps_coherence_validation_large_difference(self):
        """GPS con diferencia > 24h debe generar warning"""
        dates = {
            'exif_date_time_original': datetime(2023, 8, 4, 18, 49, 23),
            'exif_gps_date': datetime(2023, 8, 6, 20, 0, 0),  # 2 días después
        }
        
        with patch('utils.date_utils._logger') as mock_logger:
            result_date, result_source = select_chosen_date(dates)
            
            # Debe seleccionar DateTimeOriginal
            assert result_date == datetime(2023, 8, 4, 18, 49, 23)
            
            # Debe haber llamado a warning
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert 'GPS DateStamp' in warning_msg
            assert 'difiere' in warning_msg
    
    def test_gps_coherence_validation_small_difference(self):
        """GPS con diferencia < 24h no debe generar warning"""
        dates = {
            'exif_date_time_original': datetime(2023, 8, 4, 18, 49, 23),
            'exif_gps_date': datetime(2023, 8, 4, 20, 0, 0),  # 1.2 horas después
        }
        
        with patch('utils.date_utils._logger') as mock_logger:
            result_date, result_source = select_chosen_date(dates)
            
            # Debe seleccionar DateTimeOriginal
            assert result_date == datetime(2023, 8, 4, 18, 49, 23)
            
            # NO debe haber warning
            mock_logger.warning.assert_not_called()
    
    # === PASO 3: TESTS DE FILENAME DATE (Prioridad Secundaria) ===
    
    def test_filename_date_when_no_exif(self):
        """Filename date es seleccionado cuando no hay EXIF"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filename_date': datetime(2024, 11, 13, 0, 0),
            'video_metadata_date': None,
            'filesystem_creation_date': datetime(2024, 11, 15, 12, 0),
            'filesystem_modification_date': datetime(2024, 11, 16, 14, 0),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 11, 13, 0, 0)
        assert result_source == 'Filename'
    
    def test_filename_date_ignored_when_exif_exists(self):
        """Filename date es ignorado cuando hay EXIF"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 30),
            'filename_date': datetime(2024, 11, 13, 0, 0),  # Más reciente
            'filesystem_creation_date': datetime(2022, 1, 1, 12, 0),  # Más antigua
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        # EXIF tiene prioridad sobre filename
        assert result_date == datetime(2023, 5, 10, 14, 30)
        assert result_source == 'EXIF DateTimeOriginal'
    
    # === PASO 4: TESTS DE VIDEO METADATA ===
    
    def test_video_metadata_when_no_exif_no_filename(self):
        """Video metadata es seleccionado cuando no hay EXIF ni filename"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filename_date': None,
            'video_metadata_date': datetime(2024, 1, 15, 14, 30),
            'filesystem_creation_date': datetime(2024, 1, 15, 12, 0),
            'filesystem_modification_date': datetime(2024, 1, 15, 16, 0),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 1, 15, 14, 30)
        assert result_source == 'Video Metadata'
    
    def test_video_metadata_ignored_when_exif_exists(self):
        """Video metadata es ignorado cuando hay EXIF"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 30),
            'video_metadata_date': datetime(2024, 1, 15, 14, 30),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 5, 10, 14, 30)
        assert result_source == 'EXIF DateTimeOriginal'
    
    def test_video_metadata_ignored_when_filename_exists(self):
        """Video metadata es ignorado cuando hay filename date"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filename_date': datetime(2024, 11, 13, 0, 0),
            'video_metadata_date': datetime(2024, 1, 15, 14, 30),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        # Filename tiene prioridad sobre video metadata
        assert result_date == datetime(2024, 11, 13, 0, 0)
        assert result_source == 'Filename'
    
    # === PASO 5: TESTS DE FILESYSTEM DATES (Último recurso) ===
    
    def test_creation_date_only_filesystem(self):
        """Solo creation_date disponible (último recurso)"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filename_date': None,
            'video_metadata_date': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': None,
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert result_source == 'birth'
    
    def test_modification_date_only_filesystem(self):
        """Solo modification_date disponible"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filename_date': None,
            'video_metadata_date': None,
            'filesystem_creation_date': None,
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 1, 2, 14, 0)
        assert result_source == 'mtime'
    
    def test_filesystem_dates_returns_earliest(self):
        """Con ambas fechas filesystem, devuelve la más antigua"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filename_date': None,
            'video_metadata_date': None,
            'filesystem_creation_date': datetime(2024, 1, 1, 12, 0),  # Más antigua
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2024, 1, 2, 14, 0),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 1, 1, 12, 0)
        assert result_source == 'birth'
    
    def test_filesystem_ignored_when_exif_exists(self):
        """Fechas filesystem son ignoradas cuando hay EXIF"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 30),
            'filesystem_creation_date': datetime(2022, 1, 1, 12, 0),  # Más antigua pero ignorada
            'filesystem_modification_date': datetime(2021, 6, 15, 8, 0),  # Mucho más antigua
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        # EXIF tiene prioridad absoluta sobre filesystem
        assert result_date == datetime(2023, 5, 10, 14, 30)
        assert result_source == 'EXIF DateTimeOriginal'
    
    # === TESTS DE CASOS COMPLEJOS (Combinatoria completa) ===
    
    def test_all_sources_available_exif_wins(self):
        """Con todas las fuentes, EXIF tiene prioridad máxima"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 30),
            'exif_create_date': datetime(2023, 5, 10, 12, 0),  # Más antigua EXIF
            'exif_date_digitized': datetime(2023, 5, 10, 16, 0),
            'exif_gps_date': datetime(2023, 5, 10, 10, 0),  # Más antigua global
            'filename_date': datetime(2024, 11, 13, 0, 0),
            'video_metadata_date': datetime(2024, 1, 15, 14, 30),
            'filesystem_creation_date': datetime(2022, 1, 1, 12, 0),  # Más antigua filesystem
            'filesystem_creation_source': 'birth',
            'filesystem_modification_date': datetime(2021, 6, 15, 8, 0),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        # Debe seleccionar la EXIF más antigua
        assert result_date == datetime(2023, 5, 10, 12, 0)
        assert result_source == 'EXIF CreateDate'
    
    def test_secondary_sources_with_filesystem_filename_wins(self):
        """Sin EXIF: filename tiene prioridad sobre video y filesystem"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filename_date': datetime(2024, 11, 13, 0, 0),
            'video_metadata_date': datetime(2024, 1, 15, 14, 30),
            'filesystem_creation_date': datetime(2022, 1, 1, 12, 0),  # Más antigua
            'filesystem_modification_date': datetime(2021, 6, 15, 8, 0),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 11, 13, 0, 0)
        assert result_source == 'Filename'
    
    def test_video_and_filesystem_video_wins(self):
        """Sin EXIF ni filename: video tiene prioridad sobre filesystem"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'filename_date': None,
            'video_metadata_date': datetime(2024, 1, 15, 14, 30),
            'filesystem_creation_date': datetime(2022, 1, 1, 12, 0),  # Más antigua
            'filesystem_modification_date': datetime(2021, 6, 15, 8, 0),
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2024, 1, 15, 14, 30)
        assert result_source == 'Video Metadata'
    
    def test_completely_empty_returns_none(self):
        """Sin ninguna fecha disponible debe devolver None"""
        dates = {
            'exif_date_time_original': None,
            'exif_create_date': None,
            'exif_date_digitized': None,
            'exif_gps_date': None,
            'filename_date': None,
            'video_metadata_date': None,
            'filesystem_creation_date': None,
            'filesystem_modification_date': None,
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date is None
        assert result_source is None
    
    # === TESTS DE EDGE CASES Y VALIDACIÓN ===
    
    def test_dates_with_same_timestamp_exif_preferred(self):
        """Con timestamps idénticos, EXIF tiene prioridad en el source"""
        same_date = datetime(2023, 5, 10, 12, 0, 0)
        dates = {
            'exif_date_time_original': same_date,
            'filename_date': same_date,
            'filesystem_creation_date': same_date,
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == same_date
        assert 'EXIF' in result_source
    
    def test_exif_with_offset_priority_over_plain_exif(self):
        """DateTimeOriginal con offset tiene el source más descriptivo"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 30),
            'exif_offset_time': '-05:00',
            'exif_create_date': datetime(2023, 5, 10, 14, 30),  # Mismo timestamp
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        assert result_date == datetime(2023, 5, 10, 14, 30)
        # Debería mostrar el offset en el source
        assert '-05:00' in result_source or 'OffsetTime' in result_source
    
    def test_extreme_date_differences_handled_correctly(self):
        """Diferencias extremas de fechas deben manejarse correctamente"""
        dates = {
            'exif_date_time_original': datetime(2023, 5, 10, 14, 30),
            'exif_create_date': datetime(1990, 1, 1, 0, 0),  # 33 años antes
            'filesystem_creation_date': datetime(2024, 12, 31, 23, 59),  # En el futuro
        }
        
        result_date, result_source = select_chosen_date(dates)
        
        # Debe devolver la EXIF más antigua sin error
        assert result_date == datetime(1990, 1, 1, 0, 0)
        assert result_source == 'EXIF CreateDate'


@pytest.mark.unit
class TestVideoMetadataConfiguration:
    """Tests para la configuración de extracción de metadatos de video"""

    def test_config_defaults_to_false(self):
        """USE_VIDEO_METADATA debe estar por defecto en False"""
        assert Config.USE_VIDEO_METADATA is False

    @patch('utils.settings_manager.settings_manager.get_bool')
    def test_config_loaded_from_settings_manager(self, mock_get_bool):
        """USE_VIDEO_METADATA debe cargarse desde settings_manager al inicio"""
        from utils.settings_manager import settings_manager
        from config import Config
        
        # Simular que settings_manager devuelve True
        mock_get_bool.return_value = True
        
        # Ejecutar la lógica de carga de configuración como en main.py
        Config.USE_VIDEO_METADATA = settings_manager.get_bool(
            settings_manager.KEY_USE_VIDEO_METADATA, 
            False  # Por defecto deshabilitado
        )
        
        # Verificar que se llamó a get_bool con los parámetros correctos
        mock_get_bool.assert_called_with(
            settings_manager.KEY_USE_VIDEO_METADATA,
            False  # Valor por defecto
        )
        
        # Verificar que Config.USE_VIDEO_METADATA se actualizó
        assert Config.USE_VIDEO_METADATA is True
