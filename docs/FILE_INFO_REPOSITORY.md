# File Info Repository - Arquitectura y Uso

## Resumen

El `FileInfoRepository` es un **repositorio singleton** que centraliza toda la información de archivos del dataset. Usa el patrón **auto-fetch**: si no tiene un dato lo busca automáticamente.

## Cambios Arquitecturales Principales

### ❌ Patrón Antiguo (Pasado como Parámetro)

```python
# Orchestrator creaba y pasaba el repositorio
repo = FileInfoRepository()
service.analyze(directory, metadata_cache=repo)

# Servicio lo recibía como parámetro
def analyze(self, directory, metadata_cache=None):
    if metadata_cache:
        hash_val = metadata_cache.get_hash(path)
```

**Problemas:**
- Parámetros repetitivos en todas las firmas
- Fácil olvidar pasar el repositorio
- Difícil compartir entre servicios sin coordinación explícita

### ✅ Patrón Nuevo (Singleton con Auto-Fetch)

```python
# Orchestrator inicializa el singleton
from services.file_info_repository import FileInfoRepository
repo = FileInfoRepository.get_instance()
for file in files:
    repo.add_file(file)

# Servicio accede directamente (sin parámetro)
from services.file_info_repository import FileInfoRepository

def analyze(self, directory):  # Sin metadata_cache parameter
    repo = FileInfoRepository.get_instance()
    hash_val = repo.get_hash(path)  # Auto-fetch si no está cacheado
```

**Beneficios:**
- Sin parámetros metadata_cache en firmas
- Acceso directo y simple desde cualquier servicio
- Auto-fetch: si no tiene el dato, lo busca automáticamente
- Thread-safe: múltiples servicios pueden acceder concurrentemente

## Uso en Servicios

### Patrón Básico

```python
from services.file_info_repository import FileInfoRepository

class MyService:
    def analyze(self, directory):
        # Obtener instancia singleton
        repo = FileInfoRepository.get_instance()
        
        # Usar métodos con auto-fetch
        all_files = repo.get_all_files()
        count = repo.get_file_count()
        
        for file_path in some_paths:
            # Si está cacheado, lo devuelve
            # Si no está cacheado, lo calcula y cachea
            hash_val = repo.get_hash(file_path)
```

### Métodos con Auto-Fetch

#### `get_hash(path)` - Hash SHA256
```python
# Usa utils.file_utils.calculate_file_hash()
# Si está cacheado: retorna inmediatamente
# Si no está cacheado: calcula, cachea y retorna
hash_val = repo.get_hash(path)
```

#### `get_or_create(path)` - Metadata completa
```python
# Si está en caché: retorna metadata
# Si no está en caché: lee del disco, añade y retorna
meta = repo.get_or_create(path)
print(meta.size, meta.mtime, meta.extension)
```

#### `set_hash(path, hash)` - Establecer hash externamente
```python
# Si el archivo no está en caché, lo añade automáticamente
repo.set_hash(path, "abc123...")
```

### Métodos sin Auto-Fetch

#### `get_metadata(path)` - Solo lectura de caché
```python
# Retorna None si no está en caché (no lo busca)
meta = repo.get_metadata(path)
if meta:
    print(meta.sha256)
```

## Lifecycle del Repositorio

### 1. Inicialización (Orchestrator - Scan Phase)

```python
from services.file_info_repository import FileInfoRepository

# Obtener/crear singleton
repo = FileInfoRepository.get_instance()

# Limpiar datos anteriores si es necesario
repo.clear()

# Poblar con archivos del scan
for file_path in discovered_files:
    repo.add_file(file_path)

# Verificar población
repo.log_stats()
```

### 2. Uso en Servicios (Analysis Phase)

```python
# Cada servicio accede directamente
repo = FileInfoRepository.get_instance()

# Auto-fetch de hashes para duplicados
for file in candidates:
    hash_val = repo.get_hash(file.path)
```

### 3. Limpieza (Después de operaciones destructivas)

```python
# Después de borrar/mover archivos
repo = FileInfoRepository.get_instance()
repo.clear()  # Invalida todo el caché
```

## Migración de Código Existente

### 1. Eliminar parámetros metadata_cache

**Antes:**
```python
def analyze(
    self, 
    directory: Path,
    metadata_cache: Optional[FileInfoRepository] = None,
    progress_callback: Optional[ProgressCallback] = None
) -> AnalysisResult:
    if metadata_cache:
        files = metadata_cache.get_all_files()
```

**Después:**
```python
def analyze(
    self, 
    directory: Path,
    progress_callback: Optional[ProgressCallback] = None
) -> AnalysisResult:
    from services.file_info_repository import FileInfoRepository
    repo = FileInfoRepository.get_instance()
    files = repo.get_all_files()
```

### 2. Reemplazar llamadas condicionales

**Antes:**
```python
if metadata_cache:
    hash_val = metadata_cache.get_hash(path)
else:
    hash_val = calculate_file_hash(path)
```

**Después:**
```python
from services.file_info_repository import FileInfoRepository
repo = FileInfoRepository.get_instance()
hash_val = repo.get_hash(path)  # Auto-fetch incluido
```

### 3. Actualizar llamadas a servicios (Orchestrator)

**Antes:**
```python
metadata_cache = FileInfoRepository()
result = service.analyze(directory, metadata_cache=metadata_cache)
```

**Después:**
```python
# Inicializar singleton una vez
from services.file_info_repository import FileInfoRepository
repo = FileInfoRepository.get_instance()
# ... poblar repo ...

# Llamar servicios sin parámetro
result = service.analyze(directory)  # Sin metadata_cache
```

## Tests

### Setup para Tests

```python
import pytest
from services.file_info_repository import FileInfoRepository

@pytest.fixture(autouse=True)
def reset_repository():
    """Reset singleton entre tests"""
    FileInfoRepository.reset_instance()
    yield
    FileInfoRepository.reset_instance()

def test_my_service():
    repo = FileInfoRepository.get_instance()
    
    # Poblar con archivos de test
    repo.add_file(test_path1)
    repo.add_file(test_path2)
    
    # Ejecutar servicio
    result = my_service.analyze(test_dir)
    
    assert result.success
```

## Reutilización de Funciones Existentes

El repositorio usa funciones de `utils.file_utils.py` en lugar de reimplementar:

```python
from utils.file_utils import calculate_file_hash

def get_hash(self, path: Path) -> str:
    # ... verificar caché ...
    
    # Usa función existente
    sha256 = calculate_file_hash(path)
    
    # Cachea y retorna
    meta.sha256 = sha256
    return sha256
```

**Funciones reutilizadas:**
- `calculate_file_hash(path)` - Hash SHA256
- Futuro: Integrar con `date_utils.get_date_from_file()` para fechas EXIF

## Thread Safety

El repositorio es completamente thread-safe:

```python
# Múltiples threads pueden acceder simultáneamente
def worker_thread(file_paths):
    repo = FileInfoRepository.get_instance()
    for path in file_paths:
        hash_val = repo.get_hash(path)  # Thread-safe
```

**Mecanismos:**
- `RLock` para operaciones en `_cache`
- Lock separado para singleton creation
- Métodos individuales son atómicos

## Preparación para BBDD

La arquitectura actual permite migración futura sin cambios en servicios:

```python
class SQLiteFileRepository(IFileRepository):
    """Implementación con SQLite"""
    def get_hash(self, path: Path) -> str:
        # SELECT hash FROM files WHERE path = ?
        # Si no existe: calcula, INSERT, retorna
        pass

# En orchestrator:
# Solo cambiar esta línea:
FileInfoRepository._instance = SQLiteFileRepository()

# Servicios NO cambian - misma API
repo = FileInfoRepository.get_instance()
hash_val = repo.get_hash(path)
```

## Comandos útiles para migración

### Buscar servicios que reciben metadata_cache
```bash
grep -r "metadata_cache:" services/ --include="*.py"
```

### Buscar llamadas con metadata_cache
```bash
grep -r "metadata_cache=" services/ --include="*.py"
```

### Verificar imports antiguos
```bash
grep -r "from services.file_repository" . --include="*.py"
```

## Preguntas Frecuentes

### ¿Por qué singleton y no inyección de dependencias?

**Razones:**
1. Repositorio es único por dataset (no múltiples instancias)
2. Simplifica código eliminando parámetros repetitivos
3. Acceso directo sin necesidad de plumbing
4. Thread-safe por diseño

### ¿Cómo testear con singleton?

Usar `reset_instance()` entre tests:

```python
@pytest.fixture(autouse=True)
def reset_repo():
    FileInfoRepository.reset_instance()
    yield
```

### ¿Qué pasa si dos threads llaman get_hash() del mismo archivo?

El repositorio es thread-safe. Uno calculará el hash, el otro esperará el lock y obtendrá el resultado cacheado.

### ¿Cuándo debo llamar clear()?

- Después de operaciones destructivas (borrar/mover archivos)
- Al cambiar de dataset
- Nunca durante análisis activo

## Estado de Migración

### ✅ Completado
- [x] Renombrado: `file_repository.py` → `file_info_repository.py`
- [x] Implementado patrón singleton
- [x] Métodos usan `utils.file_utils.calculate_file_hash()`
- [x] Auto-fetch en `get_hash()`, `set_hash()`, `get_or_create()`
- [x] Documentación de API

### 🚧 Pendiente
- [ ] Eliminar parámetros `metadata_cache` de servicios
- [ ] Actualizar llamadas en orchestrator
- [ ] Actualizar tests para usar singleton
- [ ] Integrar `date_utils` para fechas EXIF con auto-fetch

Ver lista completa: [FILE_REPOSITORY_REFACTOR.md](FILE_REPOSITORY_REFACTOR.md)
