# FileInfoRepositoryCache → SQLite Migration Notes

## Arquitectura recomendada

### 1. Separar Protocol en dos niveles

```python
class IFileStorageBackend(Protocol):
    """Backend de almacenamiento puro (dict, SQLite, PostgreSQL, etc.)"""
    def add_file(self, path: Path, metadata: FileMetadata) -> None: ...
    def get_file(self, path: Path) -> Optional[FileMetadata]: ...
    def has_file(self, path: Path) -> bool: ...
    def remove_file(self, path: Path) -> bool: ...
    def update_metadata(self, path: Path, **updates) -> None: ...
    def clear(self) -> None: ...
    
    # Batch operations (crítico para SQL performance)
    def add_files_batch(self, files: List[tuple[Path, FileMetadata]]) -> int: ...
    def remove_files_batch(self, paths: List[Path]) -> int: ...
    
    # Transaction support (necesario para SQLite)
    def begin_transaction(self) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    
    # Queries básicas
    def count(self) -> int: ...
    def get_all_files(self) -> List[FileMetadata]: ...


class IFileRepository(Protocol):
    """Repositorio de alto nivel con lógica de negocio"""
    # Incluye todo lo anterior + lógica específica de población
    def populate_from_scan(...) -> None: ...
    def get_cache_statistics() -> RepositoryStats: ...
```

### 2. Estructura de tablas SQLite recomendada

```sql
-- Tabla principal de archivos
CREATE TABLE files (
    path TEXT PRIMARY KEY,
    fs_size INTEGER NOT NULL,
    fs_ctime REAL NOT NULL,
    fs_mtime REAL NOT NULL,
    fs_atime REAL NOT NULL,
    sha256 TEXT,
    
    -- EXIF fields (todos opcionales)
    exif_DateTimeOriginal TEXT,
    exif_DateTime TEXT,
    exif_DateTimeDigitized TEXT,
    exif_SubSecTimeOriginal TEXT,
    exif_OffsetTimeOriginal TEXT,
    exif_GPSDateStamp TEXT,
    exif_GPSTimeStamp TEXT,
    exif_Software TEXT,
    exif_ExifVersion TEXT,
    exif_ImageWidth INTEGER,
    exif_ImageLength INTEGER,
    exif_VideoDuration REAL,
    
    -- Best date (calculado)
    best_date REAL,
    best_date_source TEXT,
    
    -- Metadata
    created_at REAL DEFAULT (julianday('now')),
    updated_at REAL DEFAULT (julianday('now'))
);

-- Índices para performance
CREATE INDEX idx_files_size ON files(fs_size);  -- Para duplicados por tamaño
CREATE INDEX idx_files_hash ON files(sha256);   -- Para duplicados exactos
CREATE INDEX idx_files_mtime ON files(fs_mtime); -- Para ordenamiento temporal
CREATE INDEX idx_files_extension ON files(path); -- Usar substr para extensión
CREATE INDEX idx_files_best_date ON files(best_date); -- Para organización temporal

-- Tabla de estadísticas (opcional)
CREATE TABLE cache_stats (
    key TEXT PRIMARY KEY,
    value INTEGER NOT NULL,
    updated_at REAL DEFAULT (julianday('now'))
);
```

### 3. Implementación en capas

```
┌─────────────────────────────────────┐
│   FileInfoRepositoryCache           │ ← Singleton, API pública
│   (Lógica de negocio)              │
└──────────────┬──────────────────────┘
               │
               ├─ populate_from_scan()
               ├─ get_cache_statistics()
               └─ Estrategias de población
               
┌──────────────▼──────────────────────┐
│   IFileStorageBackend               │ ← Interface abstracta
└──────────────┬──────────────────────┘
               │
      ┌────────┴────────┐
      │                 │
┌─────▼──────┐   ┌─────▼─────────┐
│ DictBackend│   │ SQLiteBackend │
│ (actual)   │   │ (futuro)      │
└────────────┘   └───────────────┘
```

### 4. Cambios específicos necesarios

#### A. Método `populate_from_scan()`

**Actual (orientado a memoria):**
```python
def populate_from_scan(self, files, strategy, ...):
    with ThreadPoolExecutor() as executor:
        for future in as_completed(...):
            metadata = future.result()
            with self._lock:
                self._cache[path] = metadata  # Una por una
```

**Futuro (orientado a SQL):**
```python
def populate_from_scan(self, files, strategy, ...):
    batch = []
    batch_size = 1000
    
    with ThreadPoolExecutor() as executor:
        for future in as_completed(...):
            metadata = future.result()
            batch.append((path, metadata))
            
            if len(batch) >= batch_size:
                self._backend.begin_transaction()
                try:
                    self._backend.add_files_batch(batch)
                    self._backend.commit()
                    batch.clear()
                except Exception:
                    self._backend.rollback()
                    raise
    
    # Flush remaining
    if batch:
        self._backend.add_files_batch(batch)
```

#### B. LRU Policy

**En memoria:** OrderedDict con `move_to_end()`, `popitem(last=False)`

**En SQLite:** 
```sql
-- Añadir campo last_access_time
ALTER TABLE files ADD COLUMN last_access_time REAL;
CREATE INDEX idx_files_lru ON files(last_access_time);

-- Eviction query
DELETE FROM files 
WHERE rowid IN (
    SELECT rowid FROM files 
    ORDER BY last_access_time ASC 
    LIMIT ?
);
```

#### C. Estadísticas

**Actual:** Contadores en memoria (`self._hits`, `self._misses`)

**SQLite:**
```sql
-- Opción 1: Query en tiempo real (más lento pero preciso)
SELECT 
    COUNT(*) as total_files,
    SUM(CASE WHEN sha256 IS NOT NULL THEN 1 ELSE 0 END) as files_with_hash,
    SUM(CASE WHEN exif_DateTimeOriginal IS NOT NULL THEN 1 ELSE 0 END) as files_with_exif
FROM files;

-- Opción 2: Tabla de stats (más rápido pero requiere mantenimiento)
INSERT OR REPLACE INTO cache_stats (key, value) VALUES ('total_files', ?);
```

### 5. Checklist de migración

- [ ] Extraer interface `IFileStorageBackend` con operaciones básicas
- [ ] Mover lógica LRU/cache fuera del backend (o hacerla opcional)
- [ ] Implementar `DictBackend` como wrapper del código actual
- [ ] Añadir métodos batch: `add_files_batch()`, `remove_files_batch()`
- [ ] Añadir soporte de transacciones al Protocol
- [ ] Implementar `SQLiteBackend` con schema propuesto
- [ ] Migrar tests para que funcionen con ambos backends
- [ ] Añadir connection pooling para SQLite (multiple threads)
- [ ] Implementar WAL mode para concurrencia (`PRAGMA journal_mode=WAL`)
- [ ] Documentar índices necesarios para performance
- [ ] Benchmark: comparar dict vs SQLite en datasets grandes

### 6. Ventajas de SQLite sobre dict en memoria

✅ **Persistencia nativa** (no más JSON serialization)  
✅ **Queries SQL complejas** (filtros, joins, agregaciones)  
✅ **Índices optimizados** (búsquedas O(log n) vs O(n))  
✅ **Soporte de transacciones** (atomicidad, rollback)  
✅ **Menor uso de RAM** (datasets enormes: >100k archivos)  
✅ **Concurrencia real** (múltiples readers, writer serializado)  
✅ **Compresión integrada** (archivos .db más pequeños que JSON)  

### 7. Cuándo migrar

**Quedarse con dict si:**
- Datasets pequeños (<50k archivos)
- Performance crítica en reads (dict es O(1) puro)
- No necesitas persistencia entre sesiones
- Simplicidad > features

**Migrar a SQLite si:**
- Datasets grandes (>50k archivos, >4GB metadata)
- Necesitas queries complejas (ej: "imágenes sin EXIF de 2023")
- Persistencia entre sesiones (cachear análisis costosos)
- Múltiples workers/procesos accediendo al repo
- Necesitas histórico/auditoría de cambios

## Próximos pasos recomendados

1. **Refactorizar actual** → Extraer `DictBackend` sin cambiar funcionalidad
2. **Añadir tests de integración** → Para ambos backends
3. **Implementar `SQLiteBackend`** → Como alternativa opcional
4. **Benchmark** → Comparar performance dict vs SQLite
5. **Documentar decisión** → Cuándo usar cada uno

## Referencias

- SQLite Python: https://docs.python.org/3/library/sqlite3.html
- WAL Mode: https://www.sqlite.org/wal.html
- Performance tips: https://www.sqlite.org/performance.html
