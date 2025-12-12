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
            'exif_date_time_original': datetime(2023, 5, 15, 10, 30, 40),
            'exif_create_date': datetime(2023, 5, 15, 10, 30, 45),
            'exif_offset_time': '+02:00',
            'filename_date': datetime(2023, 5, 15, 0, 0, 0),
            'modification_date': datetime(2023, 5, 16, 12, 0, 0)
        }
        
        cache.set_all_dates(file_path, test_dates)
        
        retrieved_dates = cache.get_all_dates(file_path)
        assert retrieved_dates is not None
        assert retrieved_dates['exif_date_time_original'] == test_dates['exif_date_time_original']
        assert retrieved_dates['exif_create_date'] == test_dates['exif_create_date']
        assert retrieved_dates['exif_offset_time'] == '+02:00'
        assert retrieved_dates['filename_date'] == test_dates['filename_date']
    
    def test_get_all_dates_not_cached(self, temp_dir):
        """Debe retornar None para fechas no cacheadas"""
        cache = FileInfoRepository()
        file_path = temp_dir / "photo.jpg"
        
        retrieved_dates = cache.get_all_dates(file_path)
        assert retrieved_dates is None
    
    def test_multiple_date_sources(self, temp_dir):
        """Debe cachear fechas de múltiples fuentes correctamente"""
        cache = FileInfoRepository()
        file_path = temp_dir / "photo.jpg"
        file_path.touch()
        
        dates = {
            'exif_date_time_original': datetime(2023, 5, 15, 10, 30, 45),
            'exif_create_date': datetime(2023, 5, 15, 10, 30, 40),
            'video_metadata_date': datetime(2023, 5, 15, 10, 30, 35),
            'filename_date': datetime(2023, 5, 15, 0, 0, 0)
        }
        
        cache.set_all_dates(file_path, dates)
        
        retrieved = cache.get_all_dates(file_path)
        assert retrieved is not None
        assert retrieved['exif_date_time_original'] == dates['exif_date_time_original']
        assert retrieved['exif_create_date'] == dates['exif_create_date']
        assert retrieved['video_metadata_date'] == dates['video_metadata_date']
        assert retrieved['filename_date'] == dates['filename_date']


@pytest.mark.unit
class TestFileMetadataCacheBasicMetadata:
    """Tests de caché de metadata básico"""
    
    def test_set_and_get_size(self, temp_dir):
        """Debe cachear y recuperar tamaño de archivo"""
        cache = FileInfoRepository()
        file_path = temp_dir / "file.bin"
        file_path.touch()
        
        test_size = 12345
        cache.set_basic_metadata(file_path, size=test_size)
        
        retrieved_size = cache.get_size(file_path)
        assert retrieved_size == test_size
    
    def test_set_all_basic_metadata(self, temp_dir):
        """Debe cachear todo el metadata básico"""
        cache = FileInfoRepository()
        file_path = temp_dir / "photo.jpg"
        file_path.touch()
        
        filesystem_modification_date = datetime(2023, 5, 15, 12, 0, 0)
        filesystem_creation_date = datetime(2023, 5, 15, 11, 0, 0)
        
        cache.set_basic_metadata(
            file_path,
            size=54321,
            file_type='image',
            filesystem_modification_date=filesystem_modification_date,
            filesystem_creation_date=filesystem_creation_date,
            filesystem_creation_source='ctime'
        )
        
        metadata = cache.get_or_create(file_path)
        assert metadata.size == 54321
        assert metadata.file_type == 'image'
        assert metadata.filesystem_modification_date == filesystem_modification_date
        assert metadata.filesystem_creation_date == filesystem_creation_date
        assert metadata.filesystem_creation_source == 'ctime'


@pytest.mark.unit
class TestFileMetadataCacheInvalidation:
    """Tests de invalidación de caché"""
    
    def test_invalidate_specific_file(self, temp_dir):
        """Debe invalidar caché de archivo específico"""
        cache = FileInfoRepository()
        file1 = temp_dir / "file1.jpg"
        file2 = temp_dir / "file2.jpg"
        file1.touch()
        file2.touch()
        
        cache.set_hash(file1, "hash1")
        cache.set_hash(file2, "hash2")
        
        assert len(cache) == 2
        
        cache.invalidate(file1)
        
        assert len(cache) == 1
        assert cache.get_hash(file1) is None
        assert cache.get_hash(file2) == "hash2"
    
    def test_invalidate_all(self, temp_dir):
        """Debe invalidar toda la caché"""
        cache = FileInfoRepository()
        
        for i in range(5):
            file_path = temp_dir / f"file{i}.jpg"
            file_path.touch()
            cache.set_hash(file_path, f"hash{i}")
        
        assert len(cache) == 5
        
        cache.invalidate()
        
        assert len(cache) == 0
    
    def test_invalidate_resets_stats(self, temp_dir):
        """Debe resetear estadísticas al invalidar todo"""
        cache = FileInfoRepository()
        file_path = temp_dir / "test.jpg"
        file_path.touch()
        
        # Generar hits y misses
        cache.set_hash(file_path, "hash1")
        cache.get_hash(file_path)  # hit
        cache.get_hash(temp_dir / "nonexistent.jpg")  # miss
        
        stats_before = cache.get_stats()
        assert stats_before['hits'] > 0
        assert stats_before['misses'] > 0
        
        cache.invalidate()
        
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
        
        # 1 miss (primera vez)
        cache.set_hash(file_path, "hash123")
        
        # 3 hits (ya está cacheado)
        for _ in range(3):
            cache.get_hash(file_path)
        
        # 1 miss (archivo no cacheado)
        cache.get_hash(temp_dir / "nonexistent.jpg")
        
        stats = cache.get_stats()
        # Total: 3 hits + 2 misses = 5 requests
        # Hit rate: 3/5 = 60%
        assert stats['hits'] == 3
        assert stats['misses'] == 2
        assert stats['hit_rate'] == 60.0
    
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
        metadata1.sha256_hash = "hash123"
        
        # Obtener de nuevo
        metadata2 = cache.get_or_create(file_path)
        
        # Debe ser la misma instancia
        assert metadata2.sha256_hash == "hash123"
        assert metadata1 is metadata2
