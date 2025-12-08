"""
Test específico para verificar el comportamiento de Live Photos
con múltiples imágenes compartiendo el mismo video.
"""

import pytest
from pathlib import Path
from datetime import datetime
from services.live_photos_service import LivePhotoService, CleanupMode
from PIL import Image
import io


@pytest.fixture
def live_photo_service():
    """Crea una instancia de LivePhotoService para tests."""
    return LivePhotoService()


class TestMultipleImagesOneVideo:
    """Tests críticos: múltiples imágenes compartiendo el mismo video."""
    
    def test_multiple_images_one_video_keep_image_mode(self, live_photo_service, temp_dir):
        """
        Test CRÍTICO: Verificar que con KEEP_IMAGE:
        - Se conservan TODAS las imágenes (HEIC, JPG, jpeg, etc.)
        - Se elimina el video .MOV UNA SOLA VEZ
        """
        # Crear estructura de archivos con mismo nombre base
        base_name = "IMG_1234"
        directory = temp_dir / "photos"
        directory.mkdir()
        
        # Crear múltiples imágenes con diferentes extensiones
        heic_file = directory / f"{base_name}.HEIC"
        jpg_file = directory / f"{base_name}.JPG"
        jpeg_file = directory / f"{base_name}.jpeg"  # Minúsculas
        mov_file = directory / f"{base_name}.MOV"
        
        # Crear imágenes reales simples
        for img_path in [heic_file, jpg_file, jpeg_file]:
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(img_path, 'JPEG')
        
        # Crear video ficticio
        mov_file.write_bytes(b'FAKE VIDEO DATA' * 1000)
        
        # Ajustar fechas para que coincidan (importante para validación temporal)
        now_ts = datetime.now().timestamp()
        for f in [heic_file, jpg_file, jpeg_file, mov_file]:
            import os
            os.utime(f, (now_ts, now_ts))
        
        # Analizar con modo KEEP_IMAGE
        result = live_photo_service.analyze(
            directory,
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            recursive=False
        )
        
        # Verificaciones
        assert result.success, "El análisis debe ser exitoso"
        assert result.live_photos_found >= 1, f"Debe detectar al menos 1 Live Photo, encontró {result.live_photos_found}"
        
        # CRÍTICO: Verificar que TODAS las imágenes se conservan
        kept_paths = {str(item['path']) for item in result.files_to_keep}
        assert str(heic_file) in kept_paths, f"HEIC debe conservarse. Kept: {kept_paths}"
        assert str(jpg_file) in kept_paths, f"JPG debe conservarse. Kept: {kept_paths}"
        assert str(jpeg_file) in kept_paths, f"jpeg debe conservarse. Kept: {kept_paths}"
        
        # CRÍTICO: Verificar que el video se elimina UNA sola vez
        deleted_paths = [str(item['path']) for item in result.files_to_delete]
        video_delete_count = deleted_paths.count(str(mov_file))
        assert video_delete_count == 1, f"El video debe aparecer UNA sola vez en files_to_delete, apareció {video_delete_count} veces"
        
        # Verificar que solo hay 1 archivo a eliminar (el video)
        assert len(result.files_to_delete) == 1, f"Solo debe haber 1 archivo a eliminar (el video), pero hay {len(result.files_to_delete)}"
        assert result.files_to_delete[0]['type'] == 'video', "El archivo a eliminar debe ser el video"
        
        # Verificar que hay 3 archivos a conservar (las 3 imágenes)
        assert len(result.files_to_keep) == 3, f"Debe haber 3 archivos a conservar (las imágenes), pero hay {len(result.files_to_keep)}"
        
        print(f"\n✅ Test pasado:")
        print(f"  - Imágenes a conservar: {len(result.files_to_keep)}")
        print(f"  - Videos a eliminar: {len(result.files_to_delete)}")
        print(f"  - Space to free: {result.space_to_free} bytes")
    
    def test_execution_keeps_all_images_deletes_video_once(self, live_photo_service, temp_dir):
        """
        Test de ejecución: Verificar que la ejecución real conserva todas las imágenes
        y elimina el video una sola vez.
        """
        # Crear estructura
        base_name = "IMG_5678"
        directory = temp_dir / "photos"
        directory.mkdir()
        
        heic_file = directory / f"{base_name}.HEIC"
        jpg_file = directory / f"{base_name}.jpg"  # Minúsculas
        mov_file = directory / f"{base_name}.MOV"
        
        # Crear archivos
        for img_path in [heic_file, jpg_file]:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(img_path, 'JPEG')
        mov_file.write_bytes(b'VIDEO' * 500)
        
        # Ajustar fechas
        now_ts = datetime.now().timestamp()
        for f in [heic_file, jpg_file, mov_file]:
            import os
            os.utime(f, (now_ts, now_ts))
        
        # Analizar
        analysis = live_photo_service.analyze(
            directory,
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            recursive=False
        )
        
        # Verificar que todos los archivos existen antes de ejecutar
        assert heic_file.exists()
        assert jpg_file.exists()
        assert mov_file.exists()
        
        # Ejecutar sin backup ni dry_run
        execution_result = live_photo_service.execute(
            analysis,
            create_backup=False,
            dry_run=False
        )
        
        # Verificaciones post-ejecución
        assert execution_result.success, "La ejecución debe ser exitosa"
        assert execution_result.files_deleted == 1, f"Debe eliminar 1 archivo (el video), eliminó {execution_result.files_deleted}"
        
        # CRÍTICO: Verificar que las imágenes siguen existiendo
        assert heic_file.exists(), "HEIC debe seguir existiendo"
        assert jpg_file.exists(), "JPG debe seguir existiendo"
        
        # CRÍTICO: Verificar que el video fue eliminado
        assert not mov_file.exists(), "El video MOV debe haber sido eliminado"
        
        print(f"\n✅ Ejecución correcta:")
        print(f"  - Files deleted: {execution_result.files_deleted}")
        print(f"  - Space freed: {execution_result.space_freed} bytes")
        print(f"  - HEIC existe: {heic_file.exists()}")
        print(f"  - JPG existe: {jpg_file.exists()}")
        print(f"  - MOV existe: {mov_file.exists()}")
    
    def test_case_insensitive_extensions(self, live_photo_service, temp_dir):
        """
        Test: Las extensiones deben ser case-insensitive (.JPG, .jpg, .JpG deben funcionar).
        """
        base_name = "IMG_9999"
        directory = temp_dir / "photos"
        directory.mkdir()
        
        # Usar diferentes combinaciones de mayúsculas/minúsculas
        heic_file = directory / f"{base_name}.HeIc"  # Mixto
        jpg_file = directory / f"{base_name}.jpg"    # Minúsculas
        mov_file = directory / f"{base_name}.Mov"    # Mixto
        
        # Crear archivos
        for img_path in [heic_file, jpg_file]:
            img = Image.new('RGB', (50, 50), color='green')
            img.save(img_path, 'JPEG')
        mov_file.write_bytes(b'V' * 1000)
        
        # Ajustar fechas
        now_ts = datetime.now().timestamp()
        for f in [heic_file, jpg_file, mov_file]:
            import os
            os.utime(f, (now_ts, now_ts))
        
        # Analizar
        result = live_photo_service.analyze(
            directory,
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            recursive=False
        )
        
        # Debe detectar los Live Photos independientemente del case
        assert result.live_photos_found >= 1, "Debe detectar Live Photos con extensiones en cualquier combinación de mayús/minús"
        assert len(result.files_to_keep) == 2, "Debe conservar ambas imágenes"
        assert len(result.files_to_delete) == 1, "Debe eliminar el video una vez"
        
        print(f"\n✅ Case insensitive test pasado:")
        print(f"  - Live Photos found: {result.live_photos_found}")
        print(f"  - Files to keep: {len(result.files_to_keep)}")
        print(f"  - Files to delete: {len(result.files_to_delete)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
