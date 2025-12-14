"""
Tests unitarios para FileInfoRepository

Valida funcionalidad de caché compartida de metadatos entre fases del análisis:
- Hashes SHA256
- Fechas EXIF
- Metadata básico (tamaño, tipo)
- Invalidación de caché
- Estadísticas de uso
"""

import pytest
import time
from pathlib import Path
from datetime import datetime
from services.file_info_repository import FileInfoRepository, FileMetadata


@pytest.mark.unit
class TestFileMetadataCacheBasics:
    """Tests básicos de creación y estado inicial"""
    
    def test_cache_creation(self):
        """Debe crear caché con configuración por defecto"""
        cache = FileInfoRepository()
        assert cache is not None
        assert len(cache) == 0
        assert cache._enabled is True
    
    @pytest.mark.skip(reason="max_age_seconds removido en refactor - funcionalidad obsoleta")
    def test_cache_creation_with_custom_max_age(self):
        """Debe crear caché con max_age personalizado"""
        pass
    
    @pytest.mark.skip(reason="enable/disable removido en refactor - funcionalidad obsoleta")
    def test_cache_enable_disable(self):
        """Debe permitir habilitar/deshabilitar caché"""
        pass


@pytest.mark.unit
class TestFileMetadataCacheHashes:
    """Tests de caché de hashes SHA256"""
    
    def test_set_and_get_hash(self, temp_dir):
        """Debe cachear y recuperar hashes SHA256"""
        cache = FileInfoRepository()
        file_path = temp_dir / "test.jpg"
        file_path.touch()
        
        test_hash = "abc123def456"
        cache.set_hash(file_path, test_hash)
        
        retrieved_hash = cache.get_hash(file_path)
        assert retrieved_hash == test_hash
    
    def test_get_hash_not_cached_calculates_it(self, temp_dir):
        """Debe calcular hash si no está cacheado"""
        cache = FileInfoRepository()
        file_path = temp_dir / "test.jpg"
        file_path.write_text("test content")
        
        # Primera llamada calcula y cachea
        retrieved_hash = cache.get_hash(file_path)
        assert retrieved_hash is not None
        assert len(retrieved_hash) == 64  # SHA256 hex length
        
        # Segunda llamada usa caché
        cached_hash = cache.get_hash(file_path)
        assert cached_hash == retrieved_hash
    
    @pytest.mark.skip(reason="disable() removido en refactor - funcionalidad obsoleta")
    def test_hash_cache_disabled(self, temp_dir):
        """No debe cachear cuando está deshabilitado"""
        pass


@pytest.mark.unit
class TestFileMetadataCacheExifDates:
    """Tests de caché de fechas EXIF"""
    
    def test_set_and_get_all_dates(self, temp_dir):
        """Debe cachear y recuperar todas las fechas"""
        cache = FileInfoRepository()
        file_path = temp_dir / "photo.jpg"
        file_path.touch()
        
        test_dates = {
            'DateTimeOriginal': '2023:05:15 10:30:40',
            'DateTime': '2023:05:15 10:30:45',
            'DateTimeDigitized': '2023:05:15 10:30:35',
            'GPSTimeStamp': '10:30:40',
            'GPSDateStamp': '2023:05:15'
        }
        
        cache.set_all_dates(file_path, test_dates)
        
        retrieved_dates = cache.get_all_dates(file_path)
        assert retrieved_dates is not None
        assert retrieved_dates['DateTimeOriginal'] == test_dates['DateTimeOriginal']
        assert retrieved_dates['DateTime'] == test_dates['DateTime']
        assert retrieved_dates['DateTimeDigitized'] == test_dates['DateTimeDigitized']
        assert retrieved_dates['GPSTimeStamp'] == test_dates['GPSTimeStamp']
        assert retrieved_dates['GPSDateStamp'] == test_dates['GPSDateStamp']
    
    def test_get_all_dates_not_cached(self, temp_dir):
        """Debe retornar dict vacío para fechas no cacheadas"""
        cache = FileInfoRepository()
        file_path = temp_dir / "photo.jpg"
        
        retrieved_dates = cache.get_all_dates(file_path)
        assert retrieved_dates == {}
    
    def test_multiple_date_sources(self, temp_dir):
        """Debe cachear fechas de múltiples fuentes correctamente"""
        cache = FileInfoRepository()
        file_path = temp_dir / "photo.jpg"
        file_path.touch()
        
        dates = {
            'DateTimeOriginal': '2023:05:15 10:30:45',
            'DateTime': '2023:05:15 10:30:40',
            'DateTimeDigitized': '2023:05:15 10:30:35',
            'GPSDateStamp': '2023:05:15'
        }
        
        cache.set_all_dates(file_path, dates)
        
        retrieved = cache.get_all_dates(file_path)
        assert retrieved is not None
        assert retrieved['DateTimeOriginal'] == dates['DateTimeOriginal']
        assert retrieved['DateTime'] == dates['DateTime']
        assert retrieved['DateTimeDigitized'] == dates['DateTimeDigitized']
        assert retrieved['GPSDateStamp'] == dates['GPSDateStamp']


@pytest.mark.unit
class TestFileMetadataCacheBasicMetadata:
    """Tests de caché de metadata básico"""
    
    def test_set_and_get_size(self, temp_dir):
        """Debe cachear y recuperar tamaño de archivo"""
        cache = FileInfoRepository()
        file_path = temp_dir / "file.bin"
        file_path.touch()
        
        test_size = 12345
        test_time = 1234567890.0
        cache.set_basic_metadata(file_path, size=test_size, ctime=test_time, mtime=test_time, atime=test_time)
        
        meta = cache.get_metadata(file_path)
        assert meta is not None
        assert meta.size == test_size
    
    def test_set_all_basic_metadata(self, temp_dir):
        """Debe cachear todo el metadata básico"""
        cache = FileInfoRepository()
        file_path = temp_dir / "photo.jpg"
        file_path.touch()
        
        mtime_timestamp = datetime(2023, 5, 15, 12, 0, 0).timestamp()
        ctime_timestamp = datetime(2023, 5, 15, 11, 0, 0).timestamp()
        atime_timestamp = datetime(2023, 5, 15, 10, 0, 0).timestamp()
        
        cache.set_basic_metadata(
            file_path,
            size=54321,
            ctime=ctime_timestamp,
            mtime=mtime_timestamp,
            atime=atime_timestamp
        )
        
        metadata = cache.get_or_create(file_path)
        assert metadata.size == 54321
        assert metadata.fs_mtime == mtime_timestamp
        assert metadata.fs_ctime == ctime_timestamp
        assert metadata.fs_atime == atime_timestamp


@pytest.mark.unit
class TestFileMetadataCacheInvalidation:
    """Tests de invalidación de caché"""
    
    def test_invalidate_specific_file(self, temp_dir):
        """Debe limpiar caché completa (API no soporta invalidación selectiva)"""
        cache = FileInfoRepository()
        file1 = temp_dir / "file1.jpg"
        file2 = temp_dir / "file2.jpg"
        file1.touch()
        file2.touch()
        
        cache.set_hash(file1, "hash1")
        cache.set_hash(file2, "hash2")
        
        assert len(cache) == 2
        
        # API solo soporta clear() completo
        cache.clear()
        
        assert len(cache) == 0
    
    def test_invalidate_all(self, temp_dir):
        """Debe invalidar toda la caché"""
        cache = FileInfoRepository()
        
        for i in range(5):
            file_path = temp_dir / f"file{i}.jpg"
            file_path.touch()
            cache.set_hash(file_path, f"hash{i}")
        
        assert len(cache) == 5
        
        cache.clear()
        
        assert len(cache) == 0
    
    def test_invalidate_resets_stats(self, temp_dir):
        """Debe resetear estadísticas al invalidar todo"""
        cache = FileInfoRepository()
        file_path = temp_dir / "test.jpg"
        file_path.touch()
        file_path2 = temp_dir / "test2.jpg"
        file_path2.touch()
        
        # Generar hits y misses
        cache.set_hash(file_path, "hash1")
        cache.get_hash(file_path)  # hit
        # Para miss, consultar metadata sin añadir
        cache.get_metadata(file_path2)  # miss
        
        stats_before = cache.get_stats()
        assert stats_before['hits'] > 0
        assert stats_before['misses'] > 0
        
        cache.clear()
        
        stats_after = cache.get_stats()
        assert stats_after['hits'] == 0
        assert stats_after['misses'] == 0


@pytest.mark.unit
class TestFileMetadataCacheExpiration:
    """Tests de expiración de caché"""
    
    @pytest.mark.skip(reason="Expiración automática removida en refactor - funcionalidad obsoleta")
    def test_expired_entry_removed(self, temp_dir):
        """Debe remover entradas expiradas automáticamente"""
        pass
    
    @pytest.mark.skip(reason="is_valid() removido en refactor - funcionalidad obsoleta")
    def test_metadata_is_valid(self):
        """Debe validar metadata por edad"""
        pass


@pytest.mark.unit
class TestFileMetadataCacheStatistics:
    """Tests de estadísticas de uso"""
    
    def test_hit_rate_calculation(self, temp_dir):
        """Debe calcular hit rate correctamente"""
        cache = FileInfoRepository()
        file_path = temp_dir / "test.jpg"
        file_path.touch()
        file_path2 = temp_dir / "test2.jpg"
        file_path2.touch()
        
        # Añadir archivo directamente
        cache.add_file(file_path)
        
        # Múltiples hits consecutivos
        for _ in range(5):
            cache.get_metadata(file_path)  # hit
        
        # 2 misses (archivos no cacheados)
        cache.get_metadata(file_path2)  # miss
        cache.get_metadata(temp_dir / "test3.jpg")  # miss
        
        stats = cache.get_stats()
        # Total: 5 hits + 2 misses = 7 requests
        # Hit rate: 5/7 = 71.43%
        assert stats['hits'] == 5
        assert stats['misses'] == 2
        assert round(stats['hit_rate'], 1) == 71.4
    
    def test_stats_structure(self, temp_dir):
        """Debe retornar estructura de estadísticas correcta"""
        cache = FileInfoRepository()
        
        stats = cache.get_stats()
        
        assert 'size' in stats
        assert 'max_entries' in stats
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'hit_rate' in stats
        
        assert stats['size'] == 0
        assert stats['hit_rate'] == 0.0
    
    def test_log_stats_no_error(self, temp_dir):
        """log_stats no debe generar errores"""
        cache = FileInfoRepository()
        file_path = temp_dir / "test.jpg"
        file_path.touch()
        
        cache.set_hash(file_path, "hash123")
        cache.get_hash(file_path)
        
        # No debe lanzar excepciones
        cache.log_stats()


@pytest.mark.unit
class TestFileMetadataCacheContains:
    """Tests de verificación de existencia"""
    
    def test_contains_operator(self, temp_dir):
        """Debe soportar operador 'in'"""
        cache = FileInfoRepository()
        file_path = temp_dir / "test.jpg"
        file_path.touch()
        
        assert file_path not in cache
        
        cache.set_hash(file_path, "hash123")
        
        assert file_path in cache
    
    def test_len_operator(self, temp_dir):
        """Debe soportar función len()"""
        cache = FileInfoRepository()
        
        assert len(cache) == 0
        
        for i in range(3):
            file_path = temp_dir / f"file{i}.jpg"
            file_path.touch()
            cache.set_hash(file_path, f"hash{i}")
        
        assert len(cache) == 3


@pytest.mark.unit
class TestFileMetadataCacheGetOrCreate:
    """Tests de get_or_create"""
    
    def test_get_or_create_new(self, temp_dir):
        """Debe crear nueva entrada si no existe"""
        cache = FileInfoRepository()
        file_path = temp_dir / "new.jpg"
        file_path.touch()
        
        metadata = cache.get_or_create(file_path)
        
        assert metadata is not None
        assert metadata.path == file_path.resolve()
        assert file_path in cache
    
    def test_get_or_create_existing(self, temp_dir):
        """Debe retornar entrada existente si ya está cacheada"""
        cache = FileInfoRepository()
        file_path = temp_dir / "existing.jpg"
        file_path.touch()
        
        # Crear y modificar metadata
        metadata1 = cache.get_or_create(file_path)
        metadata1.sha256 = "hash123"
        
        # Obtener de nuevo
        metadata2 = cache.get_or_create(file_path)
        
        # Debe ser la misma instancia
        assert metadata2.sha256 == "hash123"
        assert metadata1 is metadata2
