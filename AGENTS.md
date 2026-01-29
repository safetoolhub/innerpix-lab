**AGENTS - Guía de Testing, Codificación y Buenas Prácticas**

Propósito
- **Descripción**: Documento de referencia para desarrolladores y agentes automatizados que interactúan con este repositorio. Contiene pautas de testing, estilo de código, flujo de trabajo, y reglas operativas específicas del proyecto.
- **Alcance**: Aplica a todo el código fuente, tests y scripts de CI 

Entorno y ejecución
### Setup
`uv venv --python 3.13 && source .venv/bin/activate && uv pip install -r requirements.txt`

### Run
`source .venv/bin/activate && python main.py`

### Test
`source .venv/bin/activate && pytest`

### Install
`uv pip install <package>` (within venv)


Estructura y patrones del proyecto
- **Separación UI / Servicios**: Toda la lógica de negocio reside en `services/` y debe ser PyQt6-free. Las interfaces gráficas deben usar esos servicios sin mezclar lógica.
- **Servicios**: Patrón `analyze()` -> retorna dataclass; `execute(create_backup=True)` para ejecutar cambios destructivos.
- **Orquestador**: `AnalysisOrchestrator.run_full_analysis()` es el punto de entrada del análisis completo.

Estilo de código y calidad
- **Formato**: PEP8 + type hints. Preferir claridad y nombres descriptivos; evitar abreviaturas de una letra.
- **Tipos**: Anotar tipos en funciones públicas y dataclasses para resultados (usar `services/result_types.py`).
- **Dataclasses**: Todas las salidas de los servicios deben ser dataclasses; no devolver dicts para resultados ni ninguna otra estructura. Solo dataclasses. 
- **No try/except pasivo**: Evitar `except: pass`. Manejar errores o en su defecto registrar y volver a lanzar.
- **Imports**: Mantener imports organizados (estándar -> terceros -> locales). Usar `isort` si existe en CI.

Logging y registros
- **Logger**: Usar `from utils.logger import get_logger` y obtener el logger por módulo: `get_logger('ModuleName')`.
- **Dual logging**: El proyecto soporta log dual (archivo completo + archivo WARN/ERROR). Respetar la convención y no imprimir directamente.
- **Formato de borrado**: Cuando se eliminen archivos, usar el formato `FILE_DELETED:` o `FILE_DELETED_SIMULATION:` para operaciones en modo simulación.
  - **Tamaños de archivo**: SIEMPRE usar `format_size()` de `utils.format_utils` para mostrar tamaños en unidades apropiadas (KB, MB, GB) en lugar de bytes puros.
  - Ejemplo: `f"Size: {format_size(file_size)}"` NO `f"Size: {file_size} B"`

Backups y modo simulación
- **Política**: Todas las operaciones destructivas aceptan `create_backup=True`. Antes de borrar/mover/renombrar, crear backup por defecto salvo indicación explícita.
- **Simulación**: Implementar y probar el modo dry-run; las acciones deben registrar eventos marcados con `SIMULATION` y no modificar el FS.

Guidelines para tests

- **Tipos de tests**: Unitarios (rápidos), integración (interacción entre servicios), performance (datasets grandes) y tests de UI (si proceden).
- **Ubicación**: `tests/unit`, `tests/integration`, `tests/performance`, `tests/ui`.
- **Naming**: Tests claros y deterministas. Prefiere nombres como `test_<comportamiento>_cuando_<condicion>` o en inglés si el repo usa inglés.
- **Fixtures**: Reutilizar fixtures centralizadas en `tests/conftest.py` para crear entornos controlados.
- **No acceso a red**: Tests deben poder correr offline. Mockear I/O externo y recursos del sistema de archivos cuando sea posible.
- **Patrón Singleton**: Para FileInfoRepositoryCache, SIEMPRE usar `self.repo = FileInfoRepositoryCache.get_instance()` y `self.repo.clear()` en setup_method.
- **FileMetadata**: Al crear instancias, incluir TODOS los campos requeridos: `path`, `fs_size`, `fs_ctime`, `fs_mtime`, `fs_atime`. Opcionalmente `best_date`, `best_date_source`.
- **Repositorio API**: Usar `repo.add_file(path, metadata)` con DOS parámetros (path y FileMetadata), NO uno solo.
- **Tests de integración**: CRÍTICO - Verificar operaciones consecutivas (analyze → execute → analyze) para detectar bugs de estado.
- **Test classes**: Organizar en clases por funcionalidad: TestBasics, TestAnalyze, TestExecute, TestEdgeCases, TestIntegration.
- **Cobertura**: CI debe ejecutar test suite completa; mantener cobertura razonable para servicios críticos.

CI / Integración continua
- **Pre-merge checks**: Ejecutar `pytest`, linters (`flake8`/`ruff`) y formateadores (`black`, `isort`) en CI antes de merge.
- **Pull requests**: Incluir descripción clara, cambios relevantes y pasos para reproducir manualmente si aplica.


Prácticas específicas del repositorio
- **Servicios**: Implementar `analyze()` que devuelva dataclasses definidos en `services/result_types.py`. Mantener `execute(create_backup=True)` con la lógica de backup y simulación.
- **Dialogs / UI**: Los diálogos en `ui/dialogs/` usan `BaseDialog` y la presentación debe ser solo UI; no incluir lógica pesada.
- **Design system**: Usar `DesignSystem` y evitar QSS o estilos inline fuera del sistema de diseño.

Tool Cards (Stage 3) - Definiciones centralizadas en `ui/tools_definitions.py`
- **Archivos vacíos** (`zero_byte_card.py`): "Archivos vacíos" - Archivos de 0 bytes sin información
- **Duplicados HEIC/JPG** (`heic_card.py`): "Duplicados HEIC/JPG" - Fotos HEIC con versiones JPG idénticas
- **Live Photos** (`live_photos_card.py`): "Live Photos" - Live Photos de iPhone (Imagen + MOV)
- **Copias exactas** (`duplicates_exact_card.py`): "Copias exactas" - Archivos 100% idénticos aunque tengan nombres diferentes
- **Copias visualmente idénticas** (`visual_identical_card.py`): "Copias visualmente idénticas" - Archivos visualmente idénticos con diferentes datos internos
- **Archivos similares** (`duplicates_similar_card.py`): "Archivos similares" - Imágenes similares pero no iguales
- **Organización inteligente** (`file_organizer_card.py`): "Organización inteligente" - Organiza imágenes y videos en carpetas
- **Renombrado completo** (`file_renamer_card.py`): "Renombrado completo" - Renombra archivos al formato YYYY-MM-DD_HH-MM-SS
- **Categorías** (centralizadas en `tools_definitions.py`):
  - "Limpieza y espacio": zero_byte, live_photos, heic, duplicates_exact
  - "Detección visual": visual_identical, duplicates_similar
  - "Organización": file_organizer, file_renamer
- Todas las cards siguen el mismo patrón: reciben `analysis_results` y `on_click_callback` excepto Organizar y Renombrar que no requieren análisis previo

Herramientas de Archivos Similares (Similar Files Tools)
- **Copias Visuales Idénticas** (`visual_identical`): Detecta copias 100% idénticas visualmente usando perceptual hash con threshold=0
  - Servicio: `VisualIdenticalService.analyze()` → `VisualIdenticalAnalysisResult`
  - Diálogo: `visual_identical_dialog.py` - TreeView con estrategias de conservación
  - Eliminación automática y segura (una copia siempre se conserva)
- **Archivos Similares** (`duplicates_similar`): Detecta archivos 70-99% similares para revisión manual
  - Servicio: `DuplicatesSimilarService.analyze(sensitivity=85)` → `DuplicateAnalysisResult`
  - Diálogo: `duplicates_similar_dialog.py` - Slider de sensibilidad para ajuste en tiempo real

Configuración de Hash Perceptual (Similar Files)
- **Config.PERCEPTUAL_HASH_ALGORITHM**: Algoritmo de hash perceptual. Valores: "phash" (default), "dhash", "ahash"
  - phash: Robusto, basado en DCT (tolerante a cambios de tamaño/brillo)
  - dhash: Rápido, bueno para recortes/ediciones (compara píxeles adyacentes)
  - ahash: Más rápido y simple (compara con media de brillo)
- **Config.PERCEPTUAL_HASH_SIZE**: Tamaño del hash. Valores: 16 (256 bits, default), 8 (64 bits), 32 (1024 bits)
- **Config.PERCEPTUAL_HASH_TARGET**: Archivos a procesar. Valores: "images" (default), "videos", "both"
- **Config.PERCEPTUAL_HASH_HIGHFREQ_FACTOR**: Factor de alta frecuencia para phash. Valores: 4 (default), 8
- **Tests**: `tests/unit/services/test_perceptual_hash_algorithms.py` - Tests para los 3 algoritmos con diferentes configuraciones

Preguntas frecuentes (FAQ)
- **Dónde poner nueva lógica?**: En `services/` como servicio reutilizable. UI solo para render y orquestación.
- **Cómo pruebo cambios de UI?**: Ejecutar localmente y usar los tests de UI en `tests/ui` si existen; preferir pruebas manuales guiadas por dialogs cuando no haya automatización.


