**AGENTS - Guía de Testing, Codificación y Buenas Prácticas**

Propósito
- **Descripción**: Documento de referencia para desarrolladores y agentes automatizados que interactúan con este repositorio. Contiene pautas de testing, estilo de código, flujo de trabajo, y reglas operativas específicas del proyecto.
- **Alcance**: Aplica a todo el código fuente, tests, scripts de CI y a los servicios descritos en la carpeta `services/`.

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
- **Dataclasses**: Todas las salidas de los servicios deben ser dataclasses; no devolver dicts para resultados.
- **No try/except pasivo**: Evitar `except: pass`. Manejar errores o en su defecto registrar y volver a lanzar.
- **Imports**: Mantener imports organizados (estándar -> terceros -> locales). Usar `isort` si existe en CI.

Logging y registros
- **Logger**: Usar `from utils.logger import get_logger` y obtener el logger por módulo: `get_logger('ModuleName')`.
- **Dual logging**: El proyecto soporta log dual (archivo completo + archivo WARN/ERROR). Respetar la convención y no imprimir directamente.
- **Formato de borrado**: Cuando se eliminen archivos, usar el formato `FILE_DELETED:` o `FILE_DELETED_SIMULATION:` para operaciones en modo simulación.

Backups y modo simulación
- **Política**: Todas las operaciones destructivas aceptan `create_backup=True`. Antes de borrar/mover/renombrar, crear backup por defecto salvo indicación explícita.
- **Simulación**: Implementar y probar el modo dry-run; las acciones deben registrar eventos marcados con `SIMULATION` y no modificar el FS.

Guidelines para tests
- **Tipos de tests**: Unitarios (rápidos), integración (interacción entre servicios), performance (datasets grandes) y tests de UI (si proceden).
- **Ubicación**: `tests/unit`, `tests/integration`, `tests/performance`, `tests/ui`.
- **Naming**: Tests claros y deterministas. Prefiere nombres como `test_<comportamiento>_cuando_<condicion>` o en inglés si el repo usa inglés.
- **Fixtures**: Reutilizar fixtures centralizadas en `tests/conftest.py` para crear entornos controlados.
- **No acceso a red**: Tests deben poder correr offline. Mockear I/O externo y recursos del sistema de archivos cuando sea posible.
- **Cobertura**: CI debe ejecutar test suite completa; mantener cobertura razonable para servicios críticos.

CI / Integración continua
- **Pre-merge checks**: Ejecutar `pytest`, linters (`flake8`/`ruff`) y formateadores (`black`, `isort`) en CI antes de merge.
- **Pull requests**: Incluir descripción clara, cambios relevantes y pasos para reproducir manualmente si aplica.

Revisión de código
- **Commits**: Pequeños y autocontenidos; mensajes tipo `feat:`, `fix:`, `chore:`. Referenciar issue si aplica.
- **PRs**: Solicitar revisión de al menos 1 revisor; incluir comentarios sobre decisiones no evidentes.

Prácticas específicas del repositorio
- **Servicios**: Implementar `analyze()` que devuelva dataclasses definidos en `services/result_types.py`. Mantener `execute(create_backup=True)` con la lógica de backup y simulación.
- **Dialogs / UI**: Los diálogos en `ui/dialogs/` usan `BaseDialog` y la presentación debe ser solo UI; no incluir lógica pesada.
- **Design system**: Usar `DesignSystem` y evitar QSS o estilos inline fuera del sistema de diseño.

Preguntas frecuentes (FAQ)
- **Dónde poner nueva lógica?**: En `services/` como servicio reutilizable. UI solo para render y orquestación.
- **Cómo pruebo cambios de UI?**: Ejecutar localmente y usar los tests de UI en `tests/ui` si existen; preferir pruebas manuales guiadas por dialogs cuando no haya automatización.


