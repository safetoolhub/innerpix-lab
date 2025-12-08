#!/usr/bin/env python3
"""
Script de debug para verificar detección de Live Photos CON CACHÉ
"""
import logging
from pathlib import Path
from services.live_photos_service import LivePhotoService, CleanupMode
from services.metadata_cache import FileMetadataCache
from services.analysis_orchestrator import AnalysisOrchestrator
from utils.logger import configure_logging, get_logger, set_global_log_level
from config import Config

# Configurar logging en DEBUG
log_dir = Path.home() / "Documents" / "Pixaro_Lab" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
configure_logging(log_dir, level="DEBUG")
set_global_log_level(logging.DEBUG)

logger = get_logger("TestLivePhotos")

# Directorio de prueba
test_dir = Path("/home/ed/Pictures/iPhoneC_hasta_202011")

if not test_dir.exists():
    print(f"❌ Directorio no encontrado: {test_dir}")
    exit(1)

print(f"🔍 Analizando: {test_dir}")
print(f"📝 Logs en: {log_dir}")
print(f"⚙️  USE_VIDEO_METADATA = {Config.USE_VIDEO_METADATA}")

# Crear orchestrator para hacer escaneo CON caché
orchestrator = AnalysisOrchestrator()

print("\n⏳ Fase 1: Escaneando directorio y creando caché de metadatos...")
scan_result = orchestrator.scan_directory(
    directory=test_dir,
    create_metadata_cache=True,
    precalculate_hashes=False
)

print(f"✅ Escaneo completado: {scan_result.total_files} archivos")
print(f"   - Imágenes: {scan_result.image_count}")
print(f"   - Videos: {scan_result.video_count}")

# Obtener caché del escaneo
metadata_cache = scan_result.metadata_cache
if metadata_cache:
    cache_stats = metadata_cache.get_stats()
    print(f"💾 Caché creado: {cache_stats['size']} entradas")

# Crear servicio y analizar CON caché
service = LivePhotoService()

print("\n⏳ Fase 2: Analizando Live Photos CON caché...")
result = service.analyze(
    directory=test_dir,
    cleanup_mode=CleanupMode.KEEP_IMAGE,
    recursive=False,
    metadata_cache=metadata_cache
)

print(f"\n✅ Análisis completado")
print(f"📊 Live Photos encontrados: {result.live_photos_found}")
print(f"📁 Archivos a eliminar: {len(result.files_to_delete)}")
print(f"💾 Espacio a liberar: {result.space_to_free / 1024 / 1024:.2f} MB")

# Mostrar primeros 10 grupos
print(f"\n📋 Primeros 10 grupos detectados:")
for i, group in enumerate(result.groups[:10], 1):
    print(f"\n{i}. {group.base_name}")
    print(f"   Img: {group.image_path.name}")
    print(f"   Vid: {group.video_path.name}")
    print(f"   Δt: {group.time_difference:.2f}s")
    if group.image_date_source:
        print(f"   Sources: Img={group.image_date_source}, Vid={group.video_date_source}")

print(f"\n🔍 Revisa los logs en {log_dir} para detalles completos")
print(f"   Busca 'Ajuste de fecha' para ver cuándo se aplicó el ajuste mtime")
