"""
Tests para verificar la deduplicación en LivePhotoService.

Estos tests verifican que el servicio maneja correctamente casos donde:
- Un mismo video aparece emparejado con múltiples imágenes
- Un mismo archivo aparecería múltiples veces en el plan de limpieza
- Se evitan errores de "archivo no encontrado" por eliminaciones duplicadas
"""

import pytest
from pathlib import Path
from services.live_photos_service import LivePhotoService, CleanupMode


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotoDuplicateHandling:
    """Tests para manejo de duplicados en planes de limpieza."""
    
    def test_same_video_multiple_images_no_duplicate_deletion(
        self, temp_dir, create_test_image, create_test_video
    ):
        """
        Test: Un video emparejado con múltiples imágenes no genera eliminación duplicada.
        
        Escenario:
        - IMG_0001.HEIC + IMG_0001.MOV (par válido)
        - IMG_0001_edit.HEIC + IMG_0001.MOV (mismo video, diferente imagen)
        
        El video solo debe intentar eliminarse UNA vez.
        """
        # Crear imágenes
        img1 = create_test_image(temp_dir / "IMG_0001.HEIC", color='red')
        img2 = create_test_image(temp_dir / "IMG_0001_edit.HEIC", color='blue')
        
        # Crear video compartido
        vid = create_test_video(temp_dir / "IMG_0001.MOV", size_bytes=2048)
        
        service = LivePhotoService()
        
        # Analizar en modo KEEP_IMAGE
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Verificar que detectó ambos pares
        # (dependiendo de la lógica de detección, podría detectar 1 o 2)
        assert analysis.success == True
        
        # Lo importante: el video solo debe aparecer UNA vez en files_to_delete
        video_paths = [item['path'] for item in analysis.files_to_delete]
        video_count = video_paths.count(vid)
        
        assert video_count == 1, f"Video aparece {video_count} veces, debería ser 1"
    
    def test_execution_handles_missing_files_gracefully(
        self, temp_dir, create_test_image, create_test_video
    ):
        """
        Test: Si un archivo ya no existe durante ejecución, se maneja correctamente.
        
        Simula el caso donde:
        1. Análisis detecta archivos
        2. Entre análisis y ejecución, un archivo desaparece
        3. Ejecución debe continuar sin fallar
        """
        # Crear Live Photo
        img = create_test_image(temp_dir / "IMG_0001.HEIC", color='red')
        vid = create_test_video(temp_dir / "IMG_0001.MOV", size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.live_photos_found == 1
        
        # Eliminar el video manualmente (simula desaparición entre análisis y ejecución)
        vid.unlink()
        
        # Ejecutar limpieza
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        # Con el nuevo manejo robusto, esto completa exitosamente
        # (el archivo faltante solo genera WARNING, no error)
        assert result.success == True
        
        # No debe haber errores reportados
        assert len(result.errors) == 0
        
        # files_deleted debe ser 0 (porque el archivo ya no existía)
        assert result.files_deleted == 0
    
    def test_deduplication_in_keep_video_mode(
        self, temp_dir, create_test_image, create_test_video
    ):
        """
        Test: Deduplicación funciona en modo KEEP_VIDEO.
        
        Verifica que si múltiples videos comparten una imagen (caso raro),
        la imagen solo aparece una vez en files_to_delete.
        """
        # Crear imagen compartida
        img = create_test_image(temp_dir / "IMG_0001.HEIC", color='red')
        
        # Crear videos
        vid1 = create_test_video(temp_dir / "IMG_0001.MOV", size_bytes=2048)
        vid2 = create_test_video(temp_dir / "IMG_0001_2.MOV", size_bytes=2048)
        
        service = LivePhotoService()
        
        # Analizar en modo KEEP_VIDEO
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_VIDEO)
        
        # Verificar deduplicación de imagen
        image_paths = [item['path'] for item in analysis.files_to_delete]
        image_count = image_paths.count(img)
        
        assert image_count == 1, f"Imagen aparece {image_count} veces, debería ser 1"
    
    def test_dry_run_with_potential_duplicates(
        self, temp_dir, create_test_image, create_test_video
    ):
        """
        Test: Dry run no debe fallar con archivos que aparecen múltiples veces.
        """
        # Crear archivos
        img1 = create_test_image(temp_dir / "IMG_0001.HEIC", color='red')
        img2 = create_test_image(temp_dir / "IMG_0001_edit.HEIC", color='blue')
        vid = create_test_video(temp_dir / "IMG_0001.MOV", size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Ejecutar en dry run
        result = service.execute(analysis, create_backup=False, dry_run=True)
        
        # No debe haber errores en dry run
        assert result.success == True
        assert len(result.errors) == 0
        
        # Todos los archivos deben seguir existiendo
        assert img1.exists()
        assert img2.exists()
        assert vid.exists()
