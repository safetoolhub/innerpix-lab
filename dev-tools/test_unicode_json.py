#!/usr/bin/env python3
"""Test de guardado/carga con caracteres Unicode"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tempfile
from services.file_metadata import FileMetadata
from services.file_metadata_repository_cache import FileInfoRepositoryCache
from datetime import datetime

print('=' * 70)
print('TEST: Guardar y Cargar con ensure_ascii=False')
print('=' * 70)

repo = FileInfoRepositoryCache.get_instance()
repo.clear()

# Crear metadatos con caracteres especiales
test_files = [
    Path('/test/2023_cumpleaños/foto1.jpg'),
    Path('/test/año_nuevo/español.jpg'),
    Path('/test/niño/ñoño.jpg'),
]

for test_path in test_files:
    metadata = FileMetadata(
        path=test_path,
        fs_size=100000,
        fs_ctime=datetime.now().timestamp(),
        fs_mtime=datetime.now().timestamp(),
        fs_atime=datetime.now().timestamp(),
    )
    repo._cache[test_path] = metadata

print(f'✅ Agregados {len(repo._cache)} archivos')

# Guardar
tmp_path = Path('/tmp/test_unicode.json')
repo.save_to_disk(tmp_path)
print(f'✅ Guardado en: {tmp_path}')

# Ver contenido
with open(tmp_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'path' in line and 'test' in line:
            print(f'  Línea {i}: {line.strip()}')

# Verificar caracteres
with open(tmp_path, 'r', encoding='utf-8') as f:
    content = f.read()
    
has_escaped = '\\u00f1' in content or '\\u00e1' in content
print(f'\n{"❌" if has_escaped else "✅"} Caracteres escapados: {has_escaped}')

# Recargar
repo.clear()
loaded = repo.load_from_disk(tmp_path, validate=False)  # No validar existencia
print(f'✅ Recargados: {loaded} archivos')

# Verificar
for path in test_files:
    found = path in repo._cache
    print(f'{"✅" if found else "❌"} {path}')

tmp_path.unlink(missing_ok=True)
print('\n✅ Test completado')
