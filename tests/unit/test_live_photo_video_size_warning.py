"""
Test para la funcionalidad de warning de tamaño de video en Live Photos.

Verifica que el sistema emite warnings apropiados cuando se eliminan
videos que exceden el tamaño típico de Live Photos.
"""
import pytest
from pathlib import Path
from services.live_photos_service import LivePhotoService, CleanupMode
from config import Config
from datetime import datetime


@pytest.mark.unit
class TestLivePhotoVideoSizeWarning:
    """Tests para el warning de tamaño de video en Live Photos"""
    
    def test_config_has_live_photo_max_video_size(self):
        """Verifica que la configuración tiene el parámetro de tamaño máximo"""
        assert hasattr(Config, 'LIVE_PHOTO_MAX_VIDEO_SIZE')
        assert Config.LIVE_PHOTO_MAX_VIDEO_SIZE > 0
        # Por defecto debería ser 6 MB
        assert Config.LIVE_PHOTO_MAX_VIDEO_SIZE == 6 * 1024 * 1024
    
    def test_small_video_no_warning(self, temp_dir, create_test_image, create_test_video, caplog):
        """Verifica que videos pequeños NO generan warning"""
        # Crear Live Photo con video pequeño (2 MB)
        small_video_size = 2 * 1024 * 1024  # 2 MB
        
        img_path = temp_dir / "IMG_0001.HEIC"
        vid_path = temp_dir / "IMG_0001.MOV"
        
        create_test_image(img_path, size=(200, 200))
        create_test_video(vid_path, size_bytes=small_video_size)
        
        # Analizar y ejecutar (modo KEEP_IMAGE = eliminar video)
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE, recursive=False)
        
        # Verificar que se detectó el Live Photo
        assert analysis.live_photos_found == 1
        assert len(analysis.files_to_delete) == 1
        
        # Ejecutar eliminación en dry_run
        result = service.execute(analysis, create_backup=False, dry_run=True)
        
        # Verificar que NO hay warning de tamaño sospechoso
        warning_logs = [record for record in caplog.records if record.levelname == 'WARNING']
        suspicious_warnings = [w for w in warning_logs if 'SOSPECHA' in w.message]
        
        assert len(suspicious_warnings) == 0, "No debería haber warnings para videos pequeños"
    
    def test_large_video_generates_warning(self, temp_dir, create_test_image, create_test_video, caplog):
        """Verifica que videos grandes SÍ generan warning"""
        import logging
        caplog.set_level(logging.WARNING)
        
        # Crear Live Photo con video grande (10 MB)
        large_video_size = 10 * 1024 * 1024  # 10 MB (excede el límite de 6 MB)
        
        img_path = temp_dir / "IMG_0002.HEIC"
        vid_path = temp_dir / "IMG_0002.MOV"
        
        create_test_image(img_path, size=(200, 200))
        create_test_video(vid_path, size_bytes=large_video_size)
        
        # Analizar y ejecutar (modo KEEP_IMAGE = eliminar video)
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE, recursive=False)
        
        # Verificar que se detectó el Live Photo
        assert analysis.live_photos_found == 1
        assert len(analysis.files_to_delete) == 1
        
        # Ejecutar eliminación en dry_run
        result = service.execute(analysis, create_backup=False, dry_run=True)
        
        # Verificar que HAY warning de tamaño sospechoso
        warning_logs = [record for record in caplog.records if record.levelname == 'WARNING']
        suspicious_warnings = [w for w in warning_logs if 'SOSPECHA' in w.message]
        
        assert len(suspicious_warnings) == 1, "Debería haber 1 warning para video grande"
        
        # Verificar el contenido del warning
        warning_msg = suspicious_warnings[0].message
        assert 'Video eliminado supera tamaño típico de Live Photo' in warning_msg
        assert str(vid_path) in warning_msg
        assert '10.0 MB' in warning_msg or '10.00 MB' in warning_msg
        assert 'Puede no ser realmente un video de Live Photo' in warning_msg
    
    def test_keep_video_mode_no_warning(self, temp_dir, create_test_image, create_test_video, caplog):
        """Verifica que modo KEEP_VIDEO (eliminar imagen) NO genera warning"""
        import logging
        caplog.set_level(logging.WARNING)
        
        # Crear Live Photo con video grande (10 MB)
        large_video_size = 10 * 1024 * 1024  # 10 MB
        
        img_path = temp_dir / "IMG_0003.HEIC"
        vid_path = temp_dir / "IMG_0003.MOV"
        
        create_test_image(img_path, size=(200, 200))
        create_test_video(vid_path, size_bytes=large_video_size)
        
        # Analizar y ejecutar (modo KEEP_VIDEO = eliminar imagen)
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_VIDEO, recursive=False)
        
        # Verificar que se detectó el Live Photo
        assert analysis.live_photos_found == 1
        # En modo KEEP_VIDEO, se elimina la imagen, no el video
        assert len(analysis.files_to_delete) == 1
        assert analysis.files_to_delete[0]['type'] == 'image'
        
        # Ejecutar eliminación en dry_run
        result = service.execute(analysis, create_backup=False, dry_run=True)
        
        # Verificar que NO hay warning (porque se elimina imagen, no video)
        warning_logs = [record for record in caplog.records if record.levelname == 'WARNING']
        suspicious_warnings = [w for w in warning_logs if 'SOSPECHA' in w.message]
        
        assert len(suspicious_warnings) == 0, "No debería haber warnings al eliminar imágenes"
    
    def test_warning_in_real_execution(self, temp_dir, create_test_image, create_test_video, caplog):
        """Verifica que el warning también se genera en ejecución real (no solo dry_run)"""
        import logging
        caplog.set_level(logging.WARNING)
        
        # Crear Live Photo con video grande (15 MB)
        large_video_size = 15 * 1024 * 1024  # 15 MB
        
        img_path = temp_dir / "IMG_0004.HEIC"
        vid_path = temp_dir / "IMG_0004.MOV"
        
        create_test_image(img_path, size=(200, 200))
        create_test_video(vid_path, size_bytes=large_video_size)
        
        # Analizar y ejecutar (modo KEEP_IMAGE = eliminar video)
        service = LivePhotoService()
        analysis = service.analyze(temp_dir, cleanup_mode=CleanupMode.KEEP_IMAGE, recursive=False)
        
        # Ejecutar eliminación REAL (sin backup)
        result = service.execute(analysis, create_backup=False, dry_run=False)
        
        # Verificar que el video fue eliminado
        assert result.success
        assert result.files_deleted == 1
        assert not vid_path.exists()
        
        # Verificar que HAY warning de tamaño sospechoso
        warning_logs = [record for record in caplog.records if record.levelname == 'WARNING']
        suspicious_warnings = [w for w in warning_logs if 'SOSPECHA' in w.message]
        
        assert len(suspicious_warnings) == 1, "Debería haber warning en ejecución real"
        
        # Verificar formato del warning
        warning_msg = suspicious_warnings[0].message
        assert '⚠️' in warning_msg
        assert 'SOSPECHA' in warning_msg
        assert 'Video eliminado supera tamaño típico de Live Photo' in warning_msg
