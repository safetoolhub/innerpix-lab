"""
Tests unitarios para DuplicatesExactService

Batería completa de pruebas para el servicio de detección de copias exactas,
incluyendo casos edge, escenarios con diferentes metadatos/fechas, y validación
de detección de archivos con extensiones no estándar.
"""

import pytest
import time
from pathlib import Path
from datetime import datetime, timedelta
from PIL import Image
from services.duplicates_exact_service import DuplicatesExactService, _is_valid_image_file
from services.result_types import DuplicateAnalysisResult
from services.file_info_repository import FileInfoRepository


# ==================== TESTS BÁSICOS ====================

@pytest.mark.unit
class TestDuplicatesExactServiceBasics:
    """Tests básicos de inicialización y funcionalidad core"""
    
    def test_initialization(self):
        """Test que el detector se inicializa correctamente"""
        detector = DuplicatesExactService()
        assert detector is not None
        assert hasattr(detector, 'analyze')
        assert hasattr(detector, 'execute')
    
    def test_empty_directory(self, temp_dir):
        """Test con directorio vacío"""
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert isinstance(result, DuplicateAnalysisResult)
        assert result.success is True
        assert result.mode == 'exact'
        assert result.total_files == 0
        assert result.total_groups == 0
        assert result.total_duplicates == 0
        assert result.space_wasted == 0
        assert len(result.groups) == 0
    
    def test_directory_without_duplicates(self, temp_dir, create_test_image):
        """Test con directorio que contiene archivos únicos (sin duplicados)"""
        # Crear imágenes únicas (diferentes colores = diferentes hashes)
        create_test_image(temp_dir / "unique1.jpg", color='red')
        create_test_image(temp_dir / "unique2.jpg", color='blue')
        create_test_image(temp_dir / "unique3.jpg", color='green')
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert result.success is True
        assert result.total_files == 3
        assert result.total_groups == 0
        assert result.total_duplicates == 0
        assert result.space_wasted == 0


# ==================== TESTS DE DUPLICADOS SIMPLES ====================

@pytest.mark.unit
class TestDuplicatesExactServiceSimpleDuplicates:
    """Tests de detección de duplicados simples"""
    
    def test_single_duplicate_pair(self, temp_dir, create_test_image):
        """Test con un par de archivos duplicados"""
        # Crear imagen original
        original = create_test_image(temp_dir / "original.jpg", color='red')
        
        # Crear copia exacta
        import shutil
        duplicate = temp_dir / "duplicate.jpg"
        shutil.copy2(original, duplicate)
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert result.success is True
        assert result.total_files == 2
        assert result.total_groups == 1
        assert result.total_duplicates == 1
        assert len(result.groups) == 1
        assert len(result.groups[0].files) == 2
        assert result.groups[0].similarity_score == 100.0
    
    def test_multiple_duplicate_pairs(self, temp_dir, create_test_image):
        """Test con múltiples pares de duplicados"""
        import shutil
        
        # Grupo 1: red images
        red1 = create_test_image(temp_dir / "red1.jpg", color='red')
        red2 = temp_dir / "red2.jpg"
        shutil.copy2(red1, red2)
        
        # Grupo 2: blue images
        blue1 = create_test_image(temp_dir / "blue1.jpg", color='blue')
        blue2 = temp_dir / "blue2.jpg"
        shutil.copy2(blue1, blue2)
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert result.success is True
        assert result.total_files == 4
        assert result.total_groups == 2
        assert result.total_duplicates == 2
        assert all(len(g.files) == 2 for g in result.groups)
    
    def test_three_copies_same_file(self, temp_dir, create_test_image):
        """Test con tres copias del mismo archivo"""
        import shutil
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        copy1 = temp_dir / "copy1.jpg"
        copy2 = temp_dir / "copy2.jpg"
        
        shutil.copy2(original, copy1)
        shutil.copy2(original, copy2)
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert result.success is True
        assert result.total_files == 3
        assert result.total_groups == 1
        assert result.total_duplicates == 2  # 3 archivos - 1 original
        assert len(result.groups[0].files) == 3
    
    def test_large_duplicate_group(self, temp_dir, create_test_image):
        """Test con un grupo grande de duplicados (10 copias)"""
        import shutil
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        
        for i in range(1, 10):
            copy = temp_dir / f"copy{i}.jpg"
            shutil.copy2(original, copy)
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert result.success is True
        assert result.total_files == 10
        assert result.total_groups == 1
        assert result.total_duplicates == 9
        assert len(result.groups[0].files) == 10


# ==================== TESTS CON DIFERENTES FECHAS/METADATOS ====================

@pytest.mark.unit
class TestDuplicatesExactServiceDifferentMetadata:
    """Tests con archivos idénticos pero con metadatos/fechas diferentes"""
    
    def test_duplicates_with_different_modification_times(self, temp_dir, create_test_image):
        """Test: duplicados con diferentes fechas de modificación (deben detectarse)"""
        import shutil
        import os
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        duplicate = temp_dir / "duplicate.jpg"
        shutil.copy2(original, duplicate)
        
        # Modificar el mtime del duplicado
        old_time = time.time() - 86400  # 1 día atrás
        os.utime(duplicate, (old_time, old_time))
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # Deben detectarse como duplicados (mismo contenido bit a bit)
        assert result.success is True
        assert result.total_groups == 1
        assert len(result.groups[0].files) == 2
    
    def test_duplicates_with_different_access_times(self, temp_dir, create_test_image):
        """Test: duplicados con diferentes fechas de acceso (deben detectarse)"""
        import shutil
        import os
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        duplicate = temp_dir / "duplicate.jpg"
        shutil.copy2(original, duplicate)
        
        # Modificar solo el atime (tiempo de acceso)
        stat_info = os.stat(duplicate)
        new_atime = stat_info.st_atime - 86400  # 1 día atrás
        os.utime(duplicate, (new_atime, stat_info.st_mtime))
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert result.total_groups == 1
        assert len(result.groups[0].files) == 2
    
    def test_identical_images_different_names(self, temp_dir, create_test_image):
        """Test: imágenes idénticas con nombres completamente diferentes"""
        import shutil
        
        original = create_test_image(temp_dir / "IMG_001.jpg", color='red')
        
        # Copiar con nombres muy diferentes
        shutil.copy2(original, temp_dir / "vacation_photo.jpg")
        shutil.copy2(original, temp_dir / "20240101_153000.jpg")
        shutil.copy2(original, temp_dir / "family_picture_final_v2.jpg")
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert result.total_groups == 1
        assert result.total_duplicates == 3
        assert len(result.groups[0].files) == 4
    
    def test_images_with_different_permissions(self, temp_dir, create_test_image):
        """Test: archivos idénticos con diferentes permisos (deben detectarse)"""
        import shutil
        import os
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        duplicate = temp_dir / "duplicate.jpg"
        shutil.copy2(original, duplicate)
        
        # Cambiar permisos del duplicado
        os.chmod(duplicate, 0o644)
        os.chmod(original, 0o755)
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert result.total_groups == 1
        assert len(result.groups[0].files) == 2


# ==================== TESTS CON EXTENSIONES NO ESTÁNDAR ====================

@pytest.mark.unit
class TestDuplicatesExactServiceNonStandardExtensions:
    """Tests de detección de imágenes con extensiones no estándar"""
    
    def test_detect_image_with_nonstandard_extension(self, temp_dir, create_test_image):
        """Test: detectar imagen válida con extensión no estándar (.jpg_original)"""
        import shutil
        
        # Crear imagen con extensión estándar
        standard = create_test_image(temp_dir / "standard.jpg", color='red')
        
        # Copiar con extensión no estándar
        nonstandard = temp_dir / "image.jpg_original"
        shutil.copy2(standard, nonstandard)
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # Debe detectar ambos archivos como duplicados
        assert result.total_files == 2
        assert result.total_groups == 1
        assert len(result.groups[0].files) == 2
    
    def test_detect_image_with_backup_extension(self, temp_dir, create_test_image):
        """Test: detectar imagen con extensión de backup (.bak, .backup)"""
        import shutil
        
        original = create_test_image(temp_dir / "photo.jpg", color='blue')
        backup1 = temp_dir / "photo.jpg.bak"
        backup2 = temp_dir / "photo.jpg.backup"
        
        shutil.copy2(original, backup1)
        shutil.copy2(original, backup2)
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # Debe detectar los 3 archivos (incluyendo backups)
        assert result.total_files == 3
        assert result.total_groups == 1
        assert len(result.groups[0].files) == 3
    
    def test_ignore_non_image_files_with_image_extension(self, temp_dir):
        """Test: ignorar archivos de texto con extensión de imagen"""
        # Crear archivo de texto con extensión .jpg
        fake_image = temp_dir / "fake.jpg"
        fake_image.write_text("This is not a JPEG image")
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # El archivo se detecta por extensión estándar (.jpg), pero no generará duplicados
        # El comportamiento correcto es detectarlo pero no agrupar archivos corruptos
        assert result.success is True
        assert result.total_groups == 0  # No genera grupos de duplicados
    
    def test_skip_very_large_files_nonstandard_check(self, temp_dir):
        """Test: no verificar archivos muy grandes (>100MB) con extensiones no estándar"""
        # Crear archivo muy grande con extensión no estándar
        large_file = temp_dir / "large.dat"
        # Crear archivo que simule ser > 100MB escribiendo un archivo sparse
        with open(large_file, 'wb') as f:
            f.seek(150 * 1024 * 1024)  # 150MB
            f.write(b'\x00')
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # No debe procesar el archivo grande (>100MB con extensión no estándar)
        assert result.total_files == 0


# ==================== TESTS EN DIFERENTES DIRECTORIOS ====================

@pytest.mark.unit
class TestDuplicatesExactServiceCrossDirectory:
    """Tests de detección en diferentes subdirectorios"""
    
    def test_duplicates_in_subdirectories(self, temp_dir, create_test_image):
        """Test: detectar duplicados en subdirectorios diferentes"""
        import shutil
        
        # Crear estructura de directorios
        subdir1 = temp_dir / "photos"
        subdir2 = temp_dir / "backup"
        subdir1.mkdir()
        subdir2.mkdir()
        
        # Crear duplicados en diferentes directorios
        original = create_test_image(subdir1 / "photo.jpg", color='red')
        shutil.copy2(original, subdir2 / "photo_backup.jpg")
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert result.total_groups == 1
        assert len(result.groups[0].files) == 2
        # Verificar que están en diferentes directorios
        parents = [f.parent for f in result.groups[0].files]
        assert len(set(parents)) == 2
    
    def test_nested_subdirectories(self, temp_dir, create_test_image):
        """Test: detectar duplicados en subdirectorios anidados profundos"""
        import shutil
        
        # Crear estructura anidada
        deep_dir = temp_dir / "level1" / "level2" / "level3"
        deep_dir.mkdir(parents=True)
        
        original = create_test_image(temp_dir / "root.jpg", color='blue')
        shutil.copy2(original, deep_dir / "deep_copy.jpg")
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        assert result.total_groups == 1
        assert len(result.groups[0].files) == 2
    
    def test_duplicates_across_multiple_subdirs(self, temp_dir, create_test_image):
        """Test: duplicados distribuidos en múltiples subdirectorios"""
        import shutil
        
        # Crear 5 subdirectorios
        subdirs = []
        for i in range(5):
            subdir = temp_dir / f"folder{i}"
            subdir.mkdir()
            subdirs.append(subdir)
        
        # Crear original y copias en cada subdirectorio
        original = create_test_image(temp_dir / "original.jpg", color='green')
        for subdir in subdirs:
            shutil.copy2(original, subdir / f"copy_{subdir.name}.jpg")
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # Original + 5 copias = 6 archivos
        assert result.total_files == 6
        assert result.total_groups == 1
        assert len(result.groups[0].files) == 6


# ==================== TESTS DE ESTADÍSTICAS ====================

@pytest.mark.unit
class TestDuplicatesExactServiceStatistics:
    """Tests de cálculo de estadísticas"""
    
    def test_space_wasted_calculation(self, temp_dir, create_test_image):
        """Test: cálculo correcto del espacio desperdiciado"""
        import shutil
        
        # Crear imagen de tamaño conocido
        original = create_test_image(temp_dir / "original.jpg", size=(200, 200))
        original_size = original.stat().st_size
        
        # Crear 3 copias (space_wasted debe ser original_size * 3)
        for i in range(3):
            shutil.copy2(original, temp_dir / f"copy{i}.jpg")
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        expected_waste = original_size * 3  # 3 duplicados
        assert result.space_wasted == expected_waste
    
    def test_total_duplicates_count(self, temp_dir, create_test_image):
        """Test: conteo correcto de duplicados totales"""
        import shutil
        
        # Grupo 1: 4 archivos (3 duplicados)
        red = create_test_image(temp_dir / "red.jpg", color='red')
        for i in range(3):
            shutil.copy2(red, temp_dir / f"red_copy{i}.jpg")
        
        # Grupo 2: 3 archivos (2 duplicados)
        blue = create_test_image(temp_dir / "blue.jpg", color='blue')
        for i in range(2):
            shutil.copy2(blue, temp_dir / f"blue_copy{i}.jpg")
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # Total duplicados = (4-1) + (3-1) = 5
        assert result.total_duplicates == 5
        assert result.total_groups == 2


# ==================== TESTS DE PROGRESO Y CANCELACIÓN ====================

@pytest.mark.unit
class TestDuplicatesExactServiceProgress:
    """Tests de callbacks de progreso y cancelación"""
    
    def test_progress_callback_invoked(self, temp_dir, create_test_image):
        """Test: callback de progreso se invoca correctamente"""
        # Crear suficientes archivos para alcanzar el intervalo de progreso (UI_UPDATE_INTERVAL = 10)
        # Usamos múltiplo exacto para que el último callback sea con current==total
        for i in range(20):
            create_test_image(temp_dir / f"image{i}.jpg", color='red')
        
        progress_calls = []
        
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
            return True  # Continuar
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir, progress_callback=progress_callback)
        
        assert len(progress_calls) > 0, "Progress callback should be invoked with 20 files"
        # Verificar que el último progreso llegue al intervalo esperado
        last_call = progress_calls[-1]
        # Con 20 archivos y intervalo de 10, el último callback debe ser en 20
        assert last_call[0] == 20
        assert last_call[1] == 20
    
    def test_analysis_cancellation(self, temp_dir, create_test_image):
        """Test: cancelar análisis mediante callback"""
        # Crear suficientes archivos para permitir cancelación (más que UI_UPDATE_INTERVAL)
        for i in range(30):
            create_test_image(temp_dir / f"image{i}.jpg", color='red')
        
        cancel_at = 2  # Cancelar después de 2 llamadas al callback
        call_count = [0]
        
        def progress_callback(current, total, message):
            call_count[0] += 1
            if call_count[0] >= cancel_at:
                return False  # Cancelar
            return True  # Continuar
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir, progress_callback=progress_callback)
        
        # El callback debe haberse invocado y cancelado el análisis
        assert call_count[0] >= cancel_at, f"Expected at least {cancel_at} calls, got {call_count[0]}"
        assert result.success is True


# ==================== TESTS DE CACHÉ ====================

@pytest.mark.unit
class TestDuplicatesExactServiceCache:
    """Tests de uso de caché de metadatos"""
    
    def test_analyze_with_metadata_cache(self, temp_dir, create_test_image):
        """Test: usar caché de metadatos para reutilizar hashes"""
        import shutil
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        shutil.copy2(original, temp_dir / "duplicate.jpg")
        
        cache = FileInfoRepository()
        detector = DuplicatesExactService()
        
        # Primera ejecución: cachea hashes
        result1 = detector.analyze(temp_dir, metadata_cache=cache)
        
        # Segunda ejecución: debe reutilizar caché
        result2 = detector.analyze(temp_dir, metadata_cache=cache)
        
        assert result1.total_groups == result2.total_groups
        assert result1.total_duplicates == result2.total_duplicates
    
    def test_cache_invalidation_on_file_modification(self, temp_dir, create_test_image):
        """Test: caché se invalida si el archivo cambia"""
        import shutil
        import time
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        
        cache = FileInfoRepository()
        detector = DuplicatesExactService()
        
        # Primera ejecución
        result1 = detector.analyze(temp_dir, metadata_cache=cache)
        
        # Modificar el archivo
        time.sleep(0.1)
        create_test_image(temp_dir / "original.jpg", color='blue')  # Reescribir
        
        # Segunda ejecución: debe recalcular hash
        result2 = detector.analyze(temp_dir, metadata_cache=cache)
        
        # Los resultados pueden diferir porque el archivo cambió
        assert result2.success is True


# ==================== TESTS DE CASOS EDGE ====================

@pytest.mark.unit
class TestDuplicatesExactServiceEdgeCases:
    """Tests de casos edge y situaciones especiales"""
    
    def test_files_with_special_characters(self, temp_dir, create_test_image):
        """Test: archivos con caracteres especiales en el nombre"""
        import shutil
        
        special_names = [
            "photo with spaces.jpg",
            "photo-with-dashes.jpg",
            "photo_with_underscores.jpg",
            "photo(with)parentheses.jpg",
            "photo[with]brackets.jpg",
        ]
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        for name in special_names:
            shutil.copy2(original, temp_dir / name)
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # Original + copias = 6 archivos
        assert result.total_files == 6
        assert result.total_groups == 1
        assert len(result.groups[0].files) == 6
    
    def test_unicode_filenames(self, temp_dir, create_test_image):
        """Test: archivos con nombres unicode"""
        import shutil
        
        unicode_names = [
            "фото.jpg",  # Cirílico
            "照片.jpg",  # Chino
            "صورة.jpg",  # Árabe
            "写真.jpg",  # Japonés
        ]
        
        original = create_test_image(temp_dir / "original.jpg", color='blue')
        for name in unicode_names:
            try:
                shutil.copy2(original, temp_dir / name)
            except OSError:
                # Algunos sistemas de archivos no soportan ciertos caracteres
                pass
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # Al menos el original debe detectarse
        assert result.total_files >= 1
    
    def test_very_long_filenames(self, temp_dir, create_test_image):
        """Test: archivos con nombres muy largos (cerca del límite del sistema)"""
        import shutil
        
        # Nombre muy largo pero dentro del límite típico (255 caracteres)
        long_name = "a" * 240 + ".jpg"
        
        original = create_test_image(temp_dir / "original.jpg", color='green')
        try:
            shutil.copy2(original, temp_dir / long_name)
            
            detector = DuplicatesExactService()
            result = detector.analyze(temp_dir)
            
            assert result.total_groups == 1
            assert len(result.groups[0].files) == 2
        except OSError:
            # Sistema de archivos no soporta nombres tan largos
            pytest.skip("Sistema de archivos no soporta nombres largos")
    
    def test_symlinks_to_duplicates(self, temp_dir, create_test_image):
        """Test: enlaces simbólicos a archivos duplicados"""
        import os
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        
        try:
            # Crear symlink
            symlink = temp_dir / "symlink.jpg"
            os.symlink(original, symlink)
            
            detector = DuplicatesExactService()
            result = detector.analyze(temp_dir)
            
            # El symlink apunta al mismo archivo, no es un duplicado físico
            # Comportamiento depende de cómo se manejen symlinks
            assert result.success is True
        except OSError:
            # Sistema no soporta symlinks
            pytest.skip("Sistema no soporta enlaces simbólicos")
    
    def test_hidden_files(self, temp_dir, create_test_image):
        """Test: archivos ocultos (comienzan con punto en Unix)"""
        import shutil
        
        original = create_test_image(temp_dir / "visible.jpg", color='red')
        hidden = temp_dir / ".hidden.jpg"
        shutil.copy2(original, hidden)
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # Debe detectar archivos ocultos también
        assert result.total_files == 2
        assert result.total_groups == 1
    
    def test_files_with_no_extension(self, temp_dir, create_test_image):
        """Test: archivos de imagen sin extensión"""
        import shutil
        
        original = create_test_image(temp_dir / "with_ext.jpg", color='blue')
        no_ext = temp_dir / "no_extension"
        shutil.copy2(original, no_ext)
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # Debe detectar al menos el archivo con extensión
        assert result.total_files >= 1
    
    def test_mixed_image_and_video_duplicates(self, temp_dir, create_test_image, create_test_video):
        """Test: mezcla de imágenes y videos duplicados"""
        import shutil
        
        # Duplicados de imagen
        img1 = create_test_image(temp_dir / "img1.jpg", color='red')
        shutil.copy2(img1, temp_dir / "img2.jpg")
        
        # Duplicados de video (crear con fixture)
        vid1 = create_test_video(temp_dir / "vid1.MOV", size_bytes=2048)
        shutil.copy2(vid1, temp_dir / "vid2.MOV")
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # Debe detectar al menos las imágenes
        assert result.success is True
        assert result.total_files >= 2  # Al menos las imágenes
        assert result.total_groups >= 1  # Al menos un grupo de imágenes duplicadas
    
    def test_corrupted_file_handling(self, temp_dir):
        """Test: manejo de archivos corruptos o inaccesibles"""
        # Crear archivo corrupto (no es una imagen válida)
        corrupted = temp_dir / "corrupted.jpg"
        corrupted.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)  # JPEG header incompleto
        
        detector = DuplicatesExactService()
        result = detector.analyze(temp_dir)
        
        # No debe crashear, debe continuar
        assert result.success is True


# ==================== TESTS DE EJECUCIÓN ====================

@pytest.mark.unit
class TestDuplicatesExactServiceExecution:
    """Tests de ejecución (eliminación de duplicados)"""
    
    def test_execute_deletion_oldest_strategy(self, temp_dir, create_test_image):
        """Test: eliminar duplicados manteniendo el más antiguo"""
        import shutil
        import time
        import os
        
        # Crear original
        original = create_test_image(temp_dir / "old.jpg", color='red')
        old_time = time.time() - 86400  # 1 día atrás
        os.utime(original, (old_time, old_time))
        
        # Crear duplicado reciente
        time.sleep(0.1)
        duplicate = temp_dir / "new.jpg"
        shutil.copy2(original, duplicate)
        new_time = time.time()
        os.utime(duplicate, (new_time, new_time))
        
        detector = DuplicatesExactService()
        analysis = detector.analyze(temp_dir)
        
        result = detector.execute(
            groups=analysis.groups,
            keep_strategy='oldest',
            create_backup=False,
            dry_run=False
        )
        
        assert result.success is True
        assert result.files_deleted > 0
        assert original.exists()  # El antiguo debe permanecer
        assert not duplicate.exists()  # El nuevo debe eliminarse
    
    def test_execute_deletion_newest_strategy(self, temp_dir, create_test_image):
        """Test: eliminar duplicados manteniendo el más reciente"""
        import shutil
        import time
        import os
        
        original = create_test_image(temp_dir / "old.jpg", color='red')
        old_time = time.time() - 86400
        os.utime(original, (old_time, old_time))
        
        time.sleep(0.1)
        duplicate = temp_dir / "new.jpg"
        shutil.copy2(original, duplicate)
        new_time = time.time()
        os.utime(duplicate, (new_time, new_time))
        
        detector = DuplicatesExactService()
        analysis = detector.analyze(temp_dir)
        
        result = detector.execute(
            groups=analysis.groups,
            keep_strategy='newest',
            create_backup=False,
            dry_run=False
        )
        
        assert result.success is True
        assert not original.exists()  # El antiguo debe eliminarse
        assert duplicate.exists()  # El nuevo debe permanecer
    
    def test_execute_dry_run(self, temp_dir, create_test_image):
        """Test: dry run no elimina archivos"""
        import shutil
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        duplicate = temp_dir / "duplicate.jpg"
        shutil.copy2(original, duplicate)
        
        detector = DuplicatesExactService()
        analysis = detector.analyze(temp_dir)
        
        result = detector.execute(
            groups=analysis.groups,
            keep_strategy='oldest',
            create_backup=False,
            dry_run=True
        )
        
        # Ambos archivos deben existir
        assert original.exists()
        assert duplicate.exists()
        assert result.dry_run is True


# ==================== TESTS DE VALIDACIÓN ====================

@pytest.mark.unit
class TestDuplicatesExactServiceValidation:
    """Tests de validación de parámetros y errores"""
    
    def test_nonexistent_directory(self):
        """Test: directorio inexistente debe manejar error gracefully"""
        detector = DuplicatesExactService()
        nonexistent = Path("/path/that/does/not/exist/12345")
        
        result = detector.analyze(nonexistent)
        
        # Debe retornar resultado vacío, no crashear
        assert result.success is True
        assert result.total_files == 0
    
    def test_invalid_strategy(self, temp_dir, create_test_image):
        """Test: estrategia inválida debe registrar error en resultado"""
        import shutil
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        shutil.copy2(original, temp_dir / "duplicate.jpg")
        
        detector = DuplicatesExactService()
        analysis = detector.analyze(temp_dir)
        
        # Execute no lanza ValueError, retorna resultado con error
        result = detector.execute(
            groups=analysis.groups,
            keep_strategy='invalid_strategy',
            create_backup=False,
            dry_run=False
        )
        
        # Verificar que el resultado indica error
        assert result.success is False
        assert len(result.errors) > 0
        assert 'invalid_strategy' in str(result.errors[0])


# ==================== TESTS DE BACKUP ====================

@pytest.mark.unit
class TestDuplicatesExactServiceBackup:
    """Tests de creación de backups en exact copies detector."""
    
    def test_backup_created_when_enabled(self, temp_dir, create_test_image):
        """Test que se crea backup cuando está habilitado."""
        import shutil
        
        # Crear duplicados
        original = create_test_image(temp_dir / "original.jpg", color='red')
        shutil.copy2(original, temp_dir / "duplicate.jpg")
        
        detector = DuplicatesExactService()
        analysis = detector.analyze(temp_dir)
        
        result = detector.execute(
            groups=analysis.groups,
            keep_strategy='largest',
            create_backup=True,
            dry_run=False
        )
        
        assert result.success is True
        assert result.backup_path is not None
        assert Path(result.backup_path).exists()
        
        # Verificar que el backup contiene los archivos
        # Nota: El backup contiene TODOS los archivos del grupo (no solo el eliminado)
        backup_files = list(Path(result.backup_path).rglob('*.jpg'))
        assert len(backup_files) >= 1  # Al menos el archivo eliminado
    
    def test_no_backup_when_disabled(self, temp_dir, create_test_image):
        """Test que NO se crea backup cuando está deshabilitado."""
        import shutil
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        shutil.copy2(original, temp_dir / "duplicate.jpg")
        
        detector = DuplicatesExactService()
        analysis = detector.analyze(temp_dir)
        
        result = detector.execute(
            groups=analysis.groups,
            keep_strategy='largest',
            create_backup=False,
            dry_run=False
        )
        
        assert result.success is True
        assert result.backup_path is None
    
    def test_no_backup_in_dry_run(self, temp_dir, create_test_image):
        """Test que NO se crea backup en dry run mode."""
        import shutil
        
        original = create_test_image(temp_dir / "original.jpg", color='red')
        shutil.copy2(original, temp_dir / "duplicate.jpg")
        
        detector = DuplicatesExactService()
        analysis = detector.analyze(temp_dir)
        
        result = detector.execute(
            groups=analysis.groups,
            keep_strategy='largest',
            create_backup=True,
            dry_run=True
        )
        
        assert result.success is True
        assert result.dry_run is True
        assert result.backup_path is None
    
    def test_backup_with_same_filename_different_dirs(self, temp_dir, create_test_image):
        """
        Test CRÍTICO: Backup preserva estructura cuando hay duplicados con mismo nombre
        en diferentes subdirectorios.
        """
        import shutil
        
        # Crear estructura con "photo.jpg" duplicado en 3 subdirectorios
        dir1 = temp_dir / 'folder1'
        dir2 = temp_dir / 'folder2'
        dir3 = temp_dir / 'folder3'
        
        dir1.mkdir()
        dir2.mkdir()
        dir3.mkdir()
        
        # Crear imagen original
        original = create_test_image(temp_dir / 'original.jpg', color='red')
        
        # Copiar a cada subdirectorio con mismo nombre
        photo1 = dir1 / 'photo.jpg'
        photo2 = dir2 / 'photo.jpg'
        photo3 = dir3 / 'photo.jpg'
        
        shutil.copy2(original, photo1)
        shutil.copy2(original, photo2)
        shutil.copy2(original, photo3)
        
        # Modificar timestamps para diferenciarlos (keep_oldest)
        import time
        base_time = time.time()
        photo1.touch()
        time.sleep(0.01)
        photo2.touch()
        time.sleep(0.01)
        photo3.touch()
        
        detector = DuplicatesExactService()
        # DuplicatesExactService siempre hace búsqueda recursiva, no tiene parámetro recursive
        analysis = detector.analyze(temp_dir)
        
        # Debe encontrar 1 grupo con 4 archivos (original + 3 copias)
        assert analysis.total_groups == 1
        assert len(analysis.groups[0].files) == 4
        
        result = detector.execute(
            groups=analysis.groups,
            keep_strategy='oldest',
            create_backup=True,
            dry_run=False
        )
        
        assert result.success is True
        assert result.backup_path is not None
        assert result.files_deleted == 3  # Se eliminan las 3 copias más nuevas
        
        backup_path = Path(result.backup_path)
        
        # Verificar que se preservó la estructura de directorios en el backup
        # Los archivos eliminados deben estar en el backup con su estructura
        backup_files = list(backup_path.rglob('photo.jpg'))
        assert len(backup_files) >= 2  # Al menos 2 de los 3 eliminados tienen mismo nombre
        
        # Verificar que existen los subdirectorios en backup
        backup_dirs = [d for d in backup_path.rglob('*') if d.is_dir()]
        dir_names = [d.name for d in backup_dirs]
        
        # Al menos algunos de los folders deben estar presentes
        assert any(name in ['folder1', 'folder2', 'folder3'] for name in dir_names)
    
    def test_backup_with_nested_duplicates(self, temp_dir, create_test_image):
        """Test que backup preserva estructura anidada con duplicados."""
        import shutil
        
        # Crear estructura anidada
        level1 = temp_dir / 'level1'
        level2 = level1 / 'level2'
        level3 = level2 / 'level3'
        
        level1.mkdir()
        level2.mkdir()
        level3.mkdir()
        
        # Crear duplicados en diferentes niveles
        original = create_test_image(temp_dir / 'image.jpg', color='blue')
        dup1 = level1 / 'image.jpg'
        dup2 = level2 / 'image.jpg'
        dup3 = level3 / 'image.jpg'
        
        shutil.copy2(original, dup1)
        shutil.copy2(original, dup2)
        shutil.copy2(original, dup3)
        
        detector = DuplicatesExactService()
        # DuplicatesExactService siempre hace búsqueda recursiva
        analysis = detector.analyze(temp_dir)
        
        result = detector.execute(
            groups=analysis.groups,
            keep_strategy='largest',
            create_backup=True,
            dry_run=False
        )
        
        assert result.success is True
        backup_path = Path(result.backup_path)
        
        # Verificar estructura anidada en backup
        # Debe haber varios image.jpg en diferentes niveles
        backup_images = list(backup_path.rglob('image.jpg'))
        assert len(backup_images) >= 3  # Los 3 duplicados eliminados


# ==================== TESTS DE INTEGRACIÓN ====================

@pytest.mark.unit
class TestDuplicatesExactServiceIntegration:
    """Tests de integración con flujo completo"""
    
    def test_full_workflow_analyze_and_delete(self, temp_dir, create_test_image):
        """Test: flujo completo de análisis + eliminación"""
        import shutil
        
        # Crear estructura de duplicados
        img1 = create_test_image(temp_dir / "img1.jpg", color='red')
        shutil.copy2(img1, temp_dir / "img1_copy.jpg")
        
        img2 = create_test_image(temp_dir / "img2.jpg", color='blue')
        shutil.copy2(img2, temp_dir / "img2_copy.jpg")
        
        detector = DuplicatesExactService()
        
        # Analizar
        analysis = detector.analyze(temp_dir)
        assert analysis.total_groups == 2
        assert analysis.total_duplicates == 2
        
        # Ejecutar eliminación
        result = detector.execute(
            groups=analysis.groups,
            keep_strategy='largest',
            create_backup=True,
            dry_run=False
        )
        
        assert result.success is True
        assert result.files_deleted == 2
        assert result.backup_path is not None
        
        # Verificar que quedan 2 archivos (1 por grupo)
        remaining = list(temp_dir.glob("*.jpg"))
        assert len(remaining) == 2
