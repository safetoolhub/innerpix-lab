"""
Tests unitarios para FileMetadataCache

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
from services.metadata_cache import FileMetadataCache, FileMetadata


@pytest.mark.unit
class TestFileMetadataCacheBasics:
    """Tests básicos de creación y estado inicial"""
    
    def test_cache_creation(self):
        """Debe crear caché con configuración por defecto"""
        cache = FileMetadataCache()
        assert cache is not None
        assert len(cache) == 0
        assert cache._enabled is True
    
    def test_cache_creation_with_custom_max_age(self):
        """Debe crear caché con max_age personalizado"""
        cache = FileMetadataCache(max_age_seconds=7200)
        assert cache._max_age_seconds == 7200
    
    def test_cache_enable_disable(self):
        """Debe permitir habilitar/deshabilitar caché"""
        cache = FileMetadataCache()
        assert cache._enabled is True
        
        cache.disable()
        assert cache._enabled is False
        assert len(cache) == 0
        
        cache.enable()
        assert cache._enabled is True


@pytest.mark.unit
class TestFileMetadataCacheHashes:
    """Tests de caché de hashes SHA256"""
    
    def test_set_and_get_hash(self, temp_dir):
        """Debe cachear y recuperar hashes SHA256"""
        cache = FileMetadataCache()
        file_path = temp_dir / "test.jpg"
        file_path.touch()
        
        test_hash = "abc123def456"
        cache.set_hash(file_path, test_hash)
        
        retrieved_hash = cache.get_hash(file_path)
        assert retrieved_hash == test_hash
    
    def test_get_hash_not_cached(self, temp_dir):
        """Debe retornar None para hash no cacheado"""
        cache = FileMetadataCache()
        file_path = temp_dir / "nonexistent.jpg"
        
        retrieved_hash = cache.get_hash(file_path)
        assert retrieved_hash is None
    
    def test_hash_cache_disabled(self, temp_dir):
        """No debe cachear cuando está deshabilitado"""
        cache = FileMetadataCache()
        cache.disable()
        
        file_path = temp_dir / "test.jpg"
        file_path.touch()
        
        cache.set_hash(file_path, "hash123")
        retrieved = cache.get_hash(file_path)
        
        assert retrieved is None


@pytest.mark.unit
class TestFileMetadataCacheExifDates:
    """Tests de caché de fechas EXIF"""
    
    def test_set_and_get_exif_dates(self, temp_dir):
        """Debe cachear y recuperar fechas EXIF"""
        cache = FileMetadataCache()
        file_path = temp_dir / "photo.jpg"
        file_path.touch()
        
        test_date = datetime(2023, 5, 15, 10, 30, 45)
        test_date_original = datetime(2023, 5, 15, 10, 30, 40)
        
        cache.set_exif_dates(
            file_path,
            exif_date=test_date,
            exif_date_original=test_date_original
        )
        
        retrieved_date = cache.get_exif_date(file_path)
        assert retrieved_date == test_date
    
    def test_get_exif_date_not_cached(self, temp_dir):
        """Debe retornar None para fecha no cacheada"""
        cache = FileMetadataCache()
        file_path = temp_dir / "photo.jpg"
        
        retrieved_date = cache.get_exif_date(file_path)
        assert retrieved_date is None
    
    def test_exif_date_priority(self, temp_dir):
        """Debe retornar exif_date sobre exif_date_original"""
        cache = FileMetadataCache()
        file_path = temp_dir / "photo.jpg"
        file_path.touch()
        
        date1 = datetime(2023, 5, 15, 10, 30, 45)
        date2 = datetime(2023, 5, 15, 10, 30, 40)
        
        cache.set_exif_dates(
            file_path,
            exif_date=date1,
            exif_date_original=date2
        )
        
        retrieved = cache.get_exif_date(file_path)
        assert retrieved == date1


@pytest.mark.unit
class TestFileMetadataCacheBasicMetadata:
    """Tests de caché de metadata básico"""
    
    def test_set_and_get_size(self, temp_dir):
        """Debe cachear y recuperar tamaño de archivo"""
        cache = FileMetadataCache()
        file_path = temp_dir / "file.bin"
        file_path.touch()
        
        test_size = 12345
        cache.set_basic_metadata(file_path, size=test_size)
        
        retrieved_size = cache.get_size(file_path)
        assert retrieved_size == test_size
    
    def test_set_all_basic_metadata(self, temp_dir):
        """Debe cachear todo el metadata básico"""
        cache = FileMetadataCache()
        file_path = temp_dir / "photo.jpg"
        file_path.touch()
        
        cache.set_basic_metadata(
            file_path,
            size=54321,
            file_type='image',
            modified_time=1234567890.0,
            created_time=1234567800.0
        )
        
        metadata = cache.get_or_create(file_path)
        assert metadata.size == 54321
        assert metadata.file_type == 'image'
        assert metadata.modified_time == 1234567890.0
        assert metadata.created_time == 1234567800.0


@pytest.mark.unit
class TestFileMetadataCacheInvalidation:
    """Tests de invalidación de caché"""
    
    def test_invalidate_specific_file(self, temp_dir):
        """Debe invalidar caché de archivo específico"""
        cache = FileMetadataCache()
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
        cache = FileMetadataCache()
        
        for i in range(5):
            file_path = temp_dir / f"file{i}.jpg"
            file_path.touch()
            cache.set_hash(file_path, f"hash{i}")
        
        assert len(cache) == 5
        
        cache.invalidate()
        
        assert len(cache) == 0
    
    def test_invalidate_resets_stats(self, temp_dir):
        """Debe resetear estadísticas al invalidar todo"""
        cache = FileMetadataCache()
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
    
    def test_expired_entry_removed(self, temp_dir):
        """Debe remover entradas expiradas automáticamente"""
        cache = FileMetadataCache(max_age_seconds=1)
        file_path = temp_dir / "test.jpg"
        file_path.touch()
        
        cache.set_hash(file_path, "hash123")
        assert cache.get_hash(file_path) == "hash123"
        
        # Esperar a que expire
        time.sleep(1.1)
        
        # Debe retornar None y remover entrada
        assert cache.get_hash(file_path) is None
        assert file_path.resolve() not in cache._cache
    
    def test_metadata_is_valid(self):
        """Debe validar metadata por edad"""
        metadata = FileMetadata(path=Path("test.jpg"))
        
        # Recién creado, debe ser válido
        assert metadata.is_valid(max_age_seconds=3600)
        
        # Simular metadata antiguo
        metadata.cached_at = time.time() - 7200  # 2 horas atrás
        
        # Debe ser inválido con max_age de 1 hora
        assert not metadata.is_valid(max_age_seconds=3600)


@pytest.mark.unit
class TestFileMetadataCacheStatistics:
    """Tests de estadísticas de uso"""
    
    def test_hit_rate_calculation(self, temp_dir):
        """Debe calcular hit rate correctamente"""
        cache = FileMetadataCache()
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
        cache = FileMetadataCache()
        
        stats = cache.get_stats()
        
        assert 'enabled' in stats
        assert 'size' in stats
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'hit_rate' in stats
        assert 'max_age_seconds' in stats
        
        assert stats['enabled'] is True
        assert stats['size'] == 0
        assert stats['hit_rate'] == 0.0
    
    def test_log_stats_no_error(self, temp_dir):
        """log_stats no debe generar errores"""
        cache = FileMetadataCache()
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
        cache = FileMetadataCache()
        file_path = temp_dir / "test.jpg"
        file_path.touch()
        
        assert file_path not in cache
        
        cache.set_hash(file_path, "hash123")
        
        assert file_path in cache
    
    def test_len_operator(self, temp_dir):
        """Debe soportar función len()"""
        cache = FileMetadataCache()
        
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
        cache = FileMetadataCache()
        file_path = temp_dir / "new.jpg"
        file_path.touch()
        
        metadata = cache.get_or_create(file_path)
        
        assert metadata is not None
        assert metadata.path == file_path.resolve()
        assert file_path in cache
    
    def test_get_or_create_existing(self, temp_dir):
        """Debe retornar entrada existente si ya está cacheada"""
        cache = FileMetadataCache()
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
