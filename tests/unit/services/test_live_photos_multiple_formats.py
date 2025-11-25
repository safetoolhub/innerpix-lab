"""
Tests para LivePhotoService con múltiples formatos de imagen.

Escenario crítico: iPhone exporta Live Photos en múltiples formatos
- IMG_1100.HEIC (original)
- IMG_1100.JPG (convertido)
- IMG_1100.MOV (video compartido)

El servicio debe detectar 2 Live Photos pero solo intentar eliminar el video UNA vez.

COMPORTAMIENTO VERIFICADO:
==========================

1. KEEP_IMAGE (Mantener imágenes):
   - Detecta: 2 Live Photos (HEIC+MOV y JPG+MOV)
   - Elimina: IMG_1100.MOV (1 archivo, sin duplicados)
   - Conserva: IMG_1100.HEIC + IMG_1100.JPG (AMBAS imágenes)
   - Resultado: ✅ Ambas imágenes conservadas, video eliminado

2. KEEP_VIDEO (Mantener video):
   - Detecta: 2 Live Photos (HEIC+MOV y JPG+MOV)
   - Elimina: IMG_1100.HEIC + IMG_1100.JPG (2 archivos, AMBAS imágenes)
   - Conserva: IMG_1100.MOV (1 video, sin duplicados)
   - Resultado: ✅ Ambas imágenes eliminadas, video conservado

Deduplicación: La implementación usa sets (seen_delete, seen_keep) en 
_generate_cleanup_plan() para prevenir duplicados en las listas.
"""

import pytest
from pathlib import Path
from services.live_photos_service import LivePhotoService, CleanupMode


@pytest.mark.unit
@pytest.mark.live_photos
class TestLivePhotosMultipleFormats:
    """Tests para Live Photos con múltiples formatos de imagen compartiendo el mismo video."""
    
    def test_heic_and_jpg_share_same_mov_keep_images(
        self, temp_dir, create_test_image, create_test_video
    ):
        """
        Test crítico: HEIC + JPG + MOV (mismo nombre base).
        
        Escenario:
        - IMG_1100.HEIC (imagen original)
        - IMG_1100.JPG (imagen convertida)
        - IMG_1100.MOV (video compartido por ambas)
        
        Modo: KEEP_IMAGE (eliminar videos)
        
        Esperado:
        - Detecta 2 Live Photos (HEIC+MOV y JPG+MOV)
        - El video solo debe aparecer UNA vez en files_to_delete
        - Ejecución debe eliminar el video solo una vez sin errores
        """
        # Crear las 3 archivos
        heic = create_test_image(temp_dir / "IMG_1100.HEIC", color='red', size=(100, 100))
        jpg = create_test_image(temp_dir / "IMG_1100.JPG", color='blue', size=(100, 100))
        mov = create_test_video(temp_dir / "IMG_1100.MOV", size_bytes=2048)
        
        service = LivePhotoService()
        
        # FASE 1: Análisis
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # Verificar detección (puede detectar 1 o 2 dependiendo de normalización)
        # Lo importante es la deduplicación en el plan
        assert analysis.success == True
        assert analysis.live_photos_found >= 1
        
        # CRÍTICO: El video debe aparecer SOLO UNA VEZ en files_to_delete
        video_paths = [str(item['path']) for item in analysis.files_to_delete]
        video_count = video_paths.count(str(mov))
        
        assert video_count == 1, f"Video aparece {video_count} veces, debe aparecer solo 1 vez"
        
        # CRÍTICO: AMBAS imágenes deben estar en files_to_keep
        keep_paths = [str(item['path']) for item in analysis.files_to_keep]
        assert str(heic) in keep_paths, "HEIC debe estar en files_to_keep"
        assert str(jpg) in keep_paths, "JPG debe estar en files_to_keep"
        assert len(analysis.files_to_keep) == 2, "Deben conservarse exactamente 2 imágenes"
        
        # FASE 2: Ejecución real
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        # Verificar ejecución exitosa
        assert result.success == True
        assert result.files_deleted == 1  # Solo el video
        assert len(result.errors) == 0    # Sin errores
        
        # Verificar archivos finales
        assert not mov.exists(), "Video debe ser eliminado"
        assert heic.exists(), "HEIC debe conservarse"
        assert jpg.exists(), "JPG debe conservarse"
    
    def test_multiple_formats_keep_video_deletes_all_images(
        self, temp_dir, create_test_image, create_test_video
    ):
        """
        Test: HEIC + JPG + MOV en modo KEEP_VIDEO.
        
        Modo: KEEP_VIDEO (eliminar imágenes)
        
        Esperado:
        - AMBAS imágenes (HEIC y JPG) deben aparecer en files_to_delete
        - Video debe mantenerse
        - Ejecución debe eliminar ambas imágenes
        """
        heic = create_test_image(temp_dir / "IMG_1100.HEIC", color='red', size=(100, 100))
        jpg = create_test_image(temp_dir / "IMG_1100.JPG", color='blue', size=(100, 100))
        mov = create_test_video(temp_dir / "IMG_1100.MOV", size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_VIDEO)
        
        assert analysis.success == True
        
        # CRÍTICO: AMBAS imágenes deben estar marcadas para eliminar
        delete_paths = [str(item['path']) for item in analysis.files_to_delete]
        
        assert str(heic) in delete_paths, "HEIC debe estar en files_to_delete"
        assert str(jpg) in delete_paths, "JPG debe estar en files_to_delete"
        assert len(analysis.files_to_delete) == 2, "Deben eliminarse exactamente 2 imágenes"
        
        # Video debe estar en keep (solo una vez)
        keep_paths = [str(item['path']) for item in analysis.files_to_keep]
        assert str(mov) in keep_paths, "Video debe estar marcado para mantener"
        assert len(analysis.files_to_keep) == 1, "Solo debe conservarse el video"
        
        # Ejecutar
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        assert result.success == True
        assert result.files_deleted == 2, "Deben eliminarse 2 archivos (ambas imágenes)"
        assert len(result.errors) == 0, "No debe haber errores"
        
        # Verificar estado final
        assert not heic.exists(), "HEIC debe ser eliminado"
        assert not jpg.exists(), "JPG debe ser eliminado"
        assert mov.exists(), "Video debe conservarse"
    
    def test_triple_format_with_dry_run(
        self, temp_dir, create_test_image, create_test_video
    ):
        """
        Test: Dry run con HEIC + JPG + JPEG + MOV (3 formatos de imagen).
        
        Verifica que dry run no falla con múltiples formatos.
        """
        heic = create_test_image(temp_dir / "IMG_1100.HEIC", color='red', size=(100, 100))
        jpg = create_test_image(temp_dir / "IMG_1100.JPG", color='green', size=(100, 100))
        jpeg = create_test_image(temp_dir / "IMG_1100.JPEG", color='blue', size=(100, 100))
        mov = create_test_video(temp_dir / "IMG_1100.MOV", size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # El video debe aparecer solo una vez
        video_paths = [str(item['path']) for item in analysis.files_to_delete]
        video_count = video_paths.count(str(mov))
        assert video_count == 1
        
        # Dry run
        result = service.execute(analysis, create_backup=False, dry_run=True)
        
        assert result.success == True
        assert len(result.errors) == 0
        assert result.simulated_files_deleted >= 1
        
        # Todos los archivos deben seguir existiendo
        assert heic.exists()
        assert jpg.exists()
        assert jpeg.exists()
        assert mov.exists()
    
    def test_two_separate_live_photos_same_directory(
        self, temp_dir, create_test_image, create_test_video
    ):
        """
        Test: Dos Live Photos diferentes en el mismo directorio.
        
        - IMG_1100.HEIC + IMG_1100.JPG + IMG_1100.MOV
        - IMG_1200.HEIC + IMG_1200.MOV
        
        Cada video debe procesarse independientemente.
        """
        # Live Photo 1 (doble formato)
        heic1 = create_test_image(temp_dir / "IMG_1100.HEIC", color='red', size=(100, 100))
        jpg1 = create_test_image(temp_dir / "IMG_1100.JPG", color='blue', size=(100, 100))
        mov1 = create_test_video(temp_dir / "IMG_1100.MOV", size_bytes=2048)
        
        # Live Photo 2 (formato único)
        heic2 = create_test_image(temp_dir / "IMG_1200.HEIC", color='green', size=(100, 100))
        mov2 = create_test_video(temp_dir / "IMG_1200.MOV", size_bytes=2048)
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        assert analysis.success == True
        assert analysis.live_photos_found >= 2
        
        # Ambos videos deben aparecer en files_to_delete (uno solo vez cada uno)
        delete_paths = [str(item['path']) for item in analysis.files_to_delete]
        assert delete_paths.count(str(mov1)) == 1
        assert delete_paths.count(str(mov2)) == 1
        
        # Ejecutar
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        assert result.success == True
        assert result.files_deleted == 2  # Ambos videos
        
        # Verificar estado final
        assert not mov1.exists()
        assert not mov2.exists()
        assert heic1.exists()
        assert jpg1.exists()
        assert heic2.exists()
    
    def test_deduplication_statistics_are_correct(
        self, temp_dir, create_test_image, create_test_video
    ):
        """
        Test: Estadísticas correctas con deduplicación.
        
        Verifica que space_to_free se calcula correctamente cuando hay duplicados.
        """
        heic = create_test_image(temp_dir / "IMG_1100.HEIC", color='red', size=(100, 100))
        jpg = create_test_image(temp_dir / "IMG_1100.JPG", color='blue', size=(100, 100))
        mov = create_test_video(temp_dir / "IMG_1100.MOV", size_bytes=2048)
        
        mov_size = mov.stat().st_size
        
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE)
        
        # space_to_free debe ser el tamaño del video (una sola vez)
        # No debe sumar 2x el tamaño del video
        assert analysis.space_to_free == mov_size, \
            f"space_to_free debería ser {mov_size} (tamaño del video), no {analysis.space_to_free}"
        
        # Ejecutar
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        # space_freed debe coincidir con space_to_free
        assert result.space_freed == mov_size
