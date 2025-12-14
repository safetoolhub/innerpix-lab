#!/usr/bin/env python3
"""
Demo de FileInfoRepository V2 - Nueva Arquitectura

Demuestra el uso del sistema de caché con diferentes estrategias.
"""
from pathlib import Path
from services.file_metadata import FileMetadata
from services.file_info_repository import (
    FileInfoRepository,
    PopulationStrategy
)

def demo_basic():
    """Demo de funcionalidad básica"""
    print("=" * 70)
    print("DEMO 1: Funcionalidad Básica")
    print("=" * 70)
    
    # Obtener instancia singleton
    repo = FileInfoRepository.get_instance()
    print(f"✓ Repositorio inicializado: {type(repo).__name__}")
    print(f"  Archivos en caché: {repo.count()}")
    
    # Crear archivos de prueba
    test_dir = Path("/tmp/fileinfo_demo")
    test_dir.mkdir(exist_ok=True)
    
    files = []
    for i in range(5):
        f = test_dir / f"test{i}.txt"
        f.write_text(f"Contenido del archivo {i}" * 100)
        files.append(f)
    
    print(f"\n✓ Creados {len(files)} archivos de prueba en {test_dir}")
    
    # Poblar con estrategia BASIC
    print("\n→ Poblando con PopulationStrategy.BASIC...")
    repo.populate_from_scan(files, PopulationStrategy.BASIC)
    
    print(f"✓ Población completada")
    print(f"  Archivos en caché: {repo.count()}")
    print(f"  Archivos con hash: {repo.count_with_hash()}")
    print(f"  Archivos con EXIF: {repo.count_with_exif()}")
    
    # Consultar metadata
    print("\n→ Consultando metadatos...")
    for file_path in files[:2]:  # Solo primeros 2
        meta = repo.get_file_metadata(file_path)
        if meta:
            print(f"\n  {meta.path.name}:")
            print(f"    Size: {meta.fs_size} bytes")
            print(f"    Ext: {meta.extension}")
            print(f"    Has hash: {meta.has_hash}")
            print(f"    Has EXIF: {meta.has_exif}")
    
    # Limpiar
    repo.clear()
    for f in files:
        f.unlink()
    test_dir.rmdir()
    print("\n✓ Limpieza completada")


def demo_strategies():
    """Demo de diferentes estrategias de población"""
    print("\n" + "=" * 70)
    print("DEMO 2: Estrategias de Población")
    print("=" * 70)
    
    repo = FileInfoRepository.get_instance()
    
    # Crear archivos de prueba
    test_dir = Path("/tmp/fileinfo_demo")
    test_dir.mkdir(exist_ok=True)
    
    files = []
    for i in range(3):
        f = test_dir / f"file{i}.txt"
        f.write_text(f"Test content {i}" * 50)
        files.append(f)
    
    print(f"\n✓ Creados {len(files)} archivos de prueba")
    
    # Estrategia 1: BASIC
    print("\n→ Estrategia 1: BASIC (solo filesystem)")
    repo.populate_from_scan(files, PopulationStrategy.BASIC)
    print(f"  Archivos: {repo.count()}")
    print(f"  Con hash: {repo.count_with_hash()}")
    
    # Estrategia 2: HASH
    print("\n→ Estrategia 2: HASH (solo SHA256, requiere BASIC previo)")
    repo.clear()
    # Primero BASIC
    repo.populate_from_scan(files, PopulationStrategy.BASIC)
    print(f"  Después de BASIC: {repo.count()} archivos")
    # Luego HASH incremental
    repo.populate_from_scan(files, PopulationStrategy.HASH)
    print(f"  Después de HASH: {repo.count_with_hash()} con hash")
    
    # Mostrar hashes
    print("\n  Hashes calculados:")
    for file_path in files:
        hash_val = repo.get_hash(file_path, auto_fetch=False)
        if hash_val:
            print(f"    {file_path.name}: {hash_val[:16]}...")
    
    # Limpiar
    repo.clear()
    for f in files:
        f.unlink()
    test_dir.rmdir()
    print("\n✓ Limpieza completada")


def demo_auto_fetch():
    """Demo de auto-fetch"""
    print("\n" + "=" * 70)
    print("DEMO 3: Auto-fetch")
    print("=" * 70)
    
    repo = FileInfoRepository.get_instance()
    
    # Crear archivo de prueba
    test_dir = Path("/tmp/fileinfo_demo")
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test.txt"
    test_file.write_text("Test content" * 100)
    
    print(f"\n✓ Creado archivo de prueba: {test_file.name}")
    
    # Sin auto-fetch (no está en caché)
    print("\n→ get_hash(..., auto_fetch=False)")
    hash_val = repo.get_hash(test_file, auto_fetch=False)
    print(f"  Resultado: {hash_val}")
    print(f"  (None porque no está en caché)")
    
    # Con auto-fetch (calcula automáticamente)
    print("\n→ get_hash(..., auto_fetch=True)")
    hash_val = repo.get_hash(test_file, auto_fetch=True)
    print(f"  Resultado: {hash_val[:16]}...")
    print(f"  (Calculado automáticamente)")
    
    # Segunda llamada (ya está en caché)
    print("\n→ get_hash(..., auto_fetch=False)")
    hash_val = repo.get_hash(test_file, auto_fetch=False)
    print(f"  Resultado: {hash_val[:16]}...")
    print(f"  (Retornado desde caché)")
    
    # Estadísticas
    print("\n→ Estadísticas:")
    stats = repo.get_stats()
    print(f"  Hits: {stats.cache_hits}")
    print(f"  Misses: {stats.cache_misses}")
    print(f"  Hit rate: {stats.hit_rate:.1f}%")
    
    # Limpiar
    repo.clear()
    test_file.unlink()
    test_dir.rmdir()
    print("\n✓ Limpieza completada")


def demo_operators():
    """Demo de operadores pythonic"""
    print("\n" + "=" * 70)
    print("DEMO 4: Operadores Pythonic")
    print("=" * 70)
    
    repo = FileInfoRepository.get_instance()
    
    # Crear archivos de prueba
    test_dir = Path("/tmp/fileinfo_demo")
    test_dir.mkdir(exist_ok=True)
    
    files = []
    for i in range(3):
        f = test_dir / f"file{i}.txt"
        f.write_text(f"Content {i}")
        files.append(f)
    
    repo.populate_from_scan(files, PopulationStrategy.BASIC)
    
    print(f"\n✓ Poblado repositorio con {len(files)} archivos")
    
    # len()
    print(f"\n→ len(repo) = {len(repo)}")
    
    # in
    print(f"\n→ files[0] in repo = {files[0] in repo}")
    print(f"→ Path('/noexiste.txt') in repo = {Path('/noexiste.txt') in repo}")
    
    # []
    print(f"\n→ repo[files[0]]:")
    meta = repo[files[0]]
    if meta:
        print(f"  {meta.path.name} - {meta.fs_size} bytes")
    
    # Limpiar
    repo.clear()
    for f in files:
        f.unlink()
    test_dir.rmdir()
    print("\n✓ Limpieza completada")


def demo_serialization():
    """Demo de serialización (preparado para BBDD)"""
    print("\n" + "=" * 70)
    print("DEMO 5: Serialización (Preparado para BBDD)")
    print("=" * 70)
    
    # Crear metadata
    print("\n→ Creando FileMetadata...")
    meta = FileMetadata(
        path=Path("/test/photo.jpg"),
        fs_size=1024000,
        fs_ctime=1702598400.0,
        fs_mtime=1702598400.0,
        fs_atime=1702598400.0,
        sha256="abc123def456" * 5,
        exif_DateTimeOriginal="2023:12:15 10:30:45"
    )
    
    print(f"  {meta.path.name}:")
    print(f"    Size: {meta.fs_size} bytes")
    print(f"    Hash: {meta.sha256[:16]}...")
    print(f"    EXIF Date: {meta.exif_DateTimeOriginal}")
    
    # Serializar
    print("\n→ Serializar a dict (to_dict)...")
    data_dict = meta.to_dict()
    print(f"  Keys: {list(data_dict.keys())[:5]}...")
    print(f"  path: {data_dict['path']}")
    print(f"  fs_size: {data_dict['fs_size']}")
    
    # Deserializar
    print("\n→ Deserializar desde dict (from_dict)...")
    meta2 = FileMetadata.from_dict(data_dict)
    print(f"  {meta2.path.name}:")
    print(f"    Size: {meta2.fs_size} bytes")
    print(f"    Hash: {meta2.sha256[:16]}...")
    
    print("\n✓ Serialización/Deserialización OK")
    print("  (Listo para guardar en MySQL)")


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "FileInfoRepository V2 - Demo" + " " * 25 + "║")
    print("║" + " " * 20 + "Nueva Arquitectura" + " " * 30 + "║")
    print("╚" + "=" * 68 + "╝")
    
    try:
        demo_basic()
        demo_strategies()
        demo_auto_fetch()
        demo_operators()
        demo_serialization()
        
        print("\n" + "=" * 70)
        print("✓ Todas las demos completadas exitosamente")
        print("=" * 70)
        print()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
