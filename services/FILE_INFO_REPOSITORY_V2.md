# File Info Repository - Nueva Arquitectura

## Resumen

Sistema de caché centralizado completamente rediseñado con arquitectura limpia, preparado para migración a MySQL.

## Cambios Principales

### 1. Separación de Responsabilidades

**Antes**: Todo en un solo archivo mezclado
**Ahora**: Dos módulos especializados

```
services/
├── file_metadata.py          # Dataclass pura (modelo de datos)
└── file_info_repository.py  # Sistema de caché (lógica)
```

### 2. FileMetadata - Modelo de Datos

```python
from services.file_metadata import FileMetadata

# Dataclass pura con metadatos completos
metadata = FileMetadata(
    path=Path("/foto.jpg"),
    fs_size=1024,
    fs_ctime=1234.5,
    fs_mtime=1234.5,
    fs_atime=1234.5,
    sha256="abc123...",
    exif_DateTimeOriginal="2023:05:15 10:30:45"
)

# Properties útiles
metadata.extension          # ".jpg"
metadata.has_hash          # True/False
metadata.has_exif          # True/False
metadata.get_exif_dates()  # Solo fechas EXIF

# Serialización (preparado para BBDD)
data_dict = metadata.to_dict()
metadata2 = FileMetadata.from_dict(data_dict)
```

### 3. FileInfoRepository - Sistema de Caché

#### Inicialización y Población

```python
from services.file_info_repository import (
    FileInfoRepository,
    PopulationStrategy
)

# Obtener instancia (Singleton)
repo = FileInfoRepository.get_instance()

# Poblar con archivos del scan (orchestrator)
files = [Path("foto1.jpg"), Path("foto2.jpg"), ...]

# Estrategia BASIC: Solo filesystem (rápido)
repo.populate_from_scan(files, PopulationStrategy.BASIC)

# Estrategia WITH_HASH: + hash SHA256 (costoso, para duplicados)
repo.populate_from_scan(files, PopulationStrategy.WITH_HASH)

# Estrategia WITH_EXIF: + EXIF (moderado, para organización)
repo.populate_from_scan(files, PopulationStrategy.WITH_EXIF)

# Estrategia FULL: Todo (muy costoso)
repo.populate_from_scan(files, PopulationStrategy.FULL)
```

#### Consultas desde Servicios

```python
# En cualquier servicio (NO pasar repositorio como parámetro)
repo = FileInfoRepository.get_instance()

# Get completo (con auto-fetch opcional)
metadata = repo.get_file_metadata(path, auto_fetch=True)  # Crea si no existe
metadata = repo.get_file_metadata(path, auto_fetch=False) # None si no existe

# Get específicos
hash_val = repo.get_hash(path, auto_fetch=True)  # Calcula si no está
exif_data = repo.get_exif(path, auto_fetch=False)  # {} si no está
fs_meta = repo.get_filesystem_metadata(path, auto_fetch=False)

# Set (solo para archivos ya en caché)
success = repo.set_hash(path, "abc123...")  # True si actualizó
success = repo.set_exif(path, exif_dict)    # True si actualizó

# Consultas masivas
all_files = repo.get_all_files()
by_size = repo.get_files_by_size()
jpgs = repo.get_files_by_extension(".jpg")

# Contadores
total = repo.count()
with_hash = repo.count_with_hash()
with_exif = repo.count_with_exif()

# Estadísticas
stats = repo.get_stats()  # RepositoryStats object
repo.log_stats()          # Log automático
```

#### Operadores Pythonic

```python
# len()
total = len(repo)

# in
if path in repo:
    print("Archivo en caché")

# []
metadata = repo[path]  # Equivalente a get_file_metadata(path, auto_fetch=False)
```

### 4. Estrategias de Población

| Estrategia | Información Cargada | Velocidad | Uso Recomendado |
|-----------|-------------------|-----------|-----------------|
| `BASIC` | Filesystem metadata | ⚡ Rápido | Scan inicial, UI |
| `WITH_HASH` | Filesystem + SHA256 | 🐌 Lento | Detector duplicados exactos |
| `WITH_EXIF` | Filesystem + EXIF | 🐢 Moderado | Organizador, Renombrador |
| `FULL` | Todo | 🐌🐌 Muy Lento | Solo si necesitas todo |

### 5. Auto-fetch

Los métodos GET aceptan parámetro `auto_fetch`:

- `auto_fetch=True`: Si no está en caché, lo busca/calcula automáticamente
- `auto_fetch=False`: Si no está en caché, retorna `None` / `{}`

```python
# Con auto-fetch (recomendado para hash)
hash_val = repo.get_hash(path, auto_fetch=True)  # Siempre retorna hash

# Sin auto-fetch (recomendado para EXIF)
exif = repo.get_exif(path, auto_fetch=False)  # {} si no está poblado
```

### 6. Preparado para MySQL

#### Arquitectura Desacoplada

```python
# Protocol define contrato abstracto
class IFileRepository(Protocol):
    def add_file(self, path: Path, metadata: FileMetadata) -> None: ...
    def get_file(self, path: Path) -> Optional[FileMetadata]: ...
    # ... etc

# Backend actual: dict en memoria
class FileInfoRepository:
    def __init__(self):
        self._cache: Dict[Path, FileMetadata] = {}

# Backend futuro: MySQL
class MySQLFileRepository:
    def __init__(self, connection_string: str):
        self._conn = mysql.connector.connect(connection_string)
    
    def add_file(self, path: Path, metadata: FileMetadata) -> None:
        data = metadata.to_dict()
        # INSERT INTO files ...
```

#### Migración a BBDD

1. FileMetadata ya tiene `to_dict()` / `from_dict()`
2. IFileRepository define interfaz abstracta
3. Crear `MySQLFileRepository` implementando el Protocol
4. Cambiar backend sin tocar código de servicios

## Ejemplo Completo

```python
from pathlib import Path
from services.file_info_repository import (
    FileInfoRepository,
    PopulationStrategy
)

# ===== En Orchestrator (scan inicial) =====
repo = FileInfoRepository.get_instance()

# Escanear directorio
files = list(Path("/fotos").rglob("*.jpg"))

# Poblar con estrategia básica (rápido)
repo.populate_from_scan(files, PopulationStrategy.BASIC)

print(f"Cargados: {repo.count()} archivos")

# ===== En Servicio de Duplicados =====
repo = FileInfoRepository.get_instance()

# Obtener hashes (auto-fetch calcula si no está)
for file in repo.get_all_files():
    hash_val = repo.get_hash(file.path, auto_fetch=True)
    print(f"{file.path.name}: {hash_val[:8]}...")

# ===== En Servicio de Organización =====
repo = FileInfoRepository.get_instance()

# Obtener EXIF (sin auto-fetch, retorna {} si no está)
for file in repo.get_all_files():
    exif = repo.get_exif(file.path, auto_fetch=False)
    if 'DateTimeOriginal' in exif:
        print(f"{file.path.name}: {exif['DateTimeOriginal']}")

# ===== Cambio de Dataset =====
repo.clear()  # Limpiar antes de nuevo scan
```

## Ventajas de la Nueva Arquitectura

1. **Separación clara**: Modelo (FileMetadata) vs Lógica (Repository)
2. **Estrategias de población**: Control fino sobre qué cargar
3. **Auto-fetch flexible**: Decisión por método, no global
4. **Preparado para BBDD**: Interfaz abstracta + serialización
5. **Thread-safe**: RLock en todas las operaciones críticas
6. **Estadísticas**: Hit/miss tracking para optimización
7. **Singleton robusto**: Una única instancia compartida
8. **API limpia**: Métodos descriptivos y consistentes

## Migración desde Código Antiguo

### Antes
```python
from services.file_info_repository import FileInfoRepository, FileMetadata

repo = FileInfoRepository()
repo.add_file(path)
meta = repo.get_metadata(path, auto_create=True)
hash_val = repo.get_hash(path, auto_create=True)
```

### Ahora
```python
from services.file_metadata import FileMetadata
from services.file_info_repository import FileInfoRepository, PopulationStrategy

repo = FileInfoRepository.get_instance()
repo.populate_from_scan(files, PopulationStrategy.BASIC)
meta = repo.get_file_metadata(path, auto_fetch=True)
hash_val = repo.get_hash(path, auto_fetch=True)
```

### Cambios de Nombres

| Antes | Ahora |
|-------|-------|
| `get_metadata()` | `get_file_metadata()` |
| `auto_create` | `auto_fetch` |
| `add_file()` | `populate_from_scan()` (bulk) |
| `get_or_create()` | `get_file_metadata(..., auto_fetch=True)` |
| `get_all_dates()` | `get_exif()` |
| `set_all_dates()` | `set_exif()` |

## Tests

Los tests actuales están rotos (muchos problemas previos). La nueva arquitectura está lista, pero los tests necesitan adaptarse a:

1. Nuevo import: `from services.file_metadata import FileMetadata`
2. Población explícita: `repo.populate_from_scan(files, strategy)`
3. Parámetro `auto_fetch` en lugar de `auto_create`

## Próximos Pasos

1. ✅ FileMetadata separado en módulo propio
2. ✅ FileInfoRepository con estrategias de población
3. ✅ Auto-fetch configurable por método
4. ✅ Preparado para migración a BBDD
5. ⏳ Adaptar tests a nueva API
6. ⏳ Integrar extracción de EXIF en estrategias
7. ⏳ Implementar backend MySQL (futuro)
