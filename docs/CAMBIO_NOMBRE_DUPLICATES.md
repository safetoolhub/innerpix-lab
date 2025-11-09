<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# PROMPT COMPLETO: Renombrado de Herramientas de Duplicados en Pixaro Lab

## Contexto del Proyecto

Pixaro Lab es una aplicación de escritorio multiplataforma (Linux, Windows, macOS) desarrollada en Python con PyQt6 para analizar y gestionar colecciones de imágenes y vídeos.[^11]

Actualmente existen dos herramientas relacionadas con duplicados:

1. **"Detección de duplicados exactos"** (archivos idénticos por SHA256)
2. **"Detección de duplicados similares"** (imágenes visualmente similares)

## Objetivo del Renombrado

Renombrar estas herramientas a una nomenclatura más clara y profesional:

- ✅ **"Copias exactas"** (antes: "Duplicados exactos" / "Detección de duplicados exactos")
- ✅ **"Archivos similares"** (antes: "Duplicados similares" / "Detección de duplicados similares")

**Justificación del cambio**:

- "Copias exactas" comunica claramente que son archivos 100% idénticos digitalmente
- "Archivos similares" es inclusivo (fotos y vídeos) y evita confusión con "copias exactas"
- Ambos términos son profesionales, concisos y fáciles de entender


## Alcance del Cambio

### 1. Textos en la Interfaz de Usuario

#### Card de "Copias exactas" (Stage 3)

**Elementos a actualizar**:

- **Título de la card**: "Copias exactas"
- **Descripción**: "Encuentra fotos y vídeos copiados (100% idénticos), incluso si tienen nombres diferentes. Elimina duplicados."
- **Icono sugerido**: `content-copy` o `file-document-multiple` (Material Design)

**Ejemplo de card visual**:

```
┌─────────────────────────────────────────┐
│ 📄 Copias exactas                      │
│                                         │
│ Encuentra fotos y vídeos copiados      │
│ (100% idénticos), incluso si tienen    │
│ nombres diferentes. Elimina duplicados.│
│                                         │
│ ✓ 42 grupos detectados                 │
│ 💾 3.2 GB recuperables                  │
│                                         │
│         [Gestionar ahora]               │
└─────────────────────────────────────────┘
```


#### Card de "Archivos similares" (Stage 3)

**Elementos a actualizar**:

- **Título de la card**: "Archivos similares"
- **Descripción**: "Detecta fotos y vídeos visualmente similares: recortes, rotaciones, ediciones o diferentes resoluciones."
- **Icono sugerido**: `image-search` o `file-compare` (Material Design)

**Ejemplo de card visual**:

```
┌─────────────────────────────────────────┐
│ 🔍 Archivos similares                  │
│                                         │
│ Detecta fotos y vídeos visualmente     │
│ similares: recortes, rotaciones,       │
│ ediciones o diferentes resoluciones.    │
│                                         │
│ ⚙️  Requiere configuración              │
│    Este análisis se personaliza según  │
│    el nivel de similitud visual.       │
│                                         │
│         [Configurar y analizar]         │
└─────────────────────────────────────────┘
```


### 2. Nombres de Archivos y Clases

#### Archivos a Renombrar

**Estructura actual** (en `ui/dialogs/`):

```
ui/dialogs/
├── exactduplicatesdialog.py
├── duplicateexactdialog.py (puede tener este nombre también)
└── similardialog.py (o similarduplicatesdialog.py)
```

**Nuevo nombre sugerido**:

```
ui/dialogs/
├── exactcopiesdialog.py
└── similarfilesdialog.py
```

**Alternativa (mantener estructura similar)**:

```
ui/dialogs/
├── duplicateexactdialog.py  →  exactcopiesdialog.py
└── duplicatesimilardialog.py  →  similarfilesdialog.py
```


#### Clases Python a Renombrar

**Antes → Después**:

**Diálogos**:

- `ExactDuplicatesDialog` → `ExactCopiesDialog`
- `DuplicateExactDialog` → `ExactCopiesDialog`
- `SimilarDuplicatesDialog` → `SimilarFilesDialog`
- `SimilarDialog` → `SimilarFilesDialog`
- `SimilarityConfigDialog` → `SimilarFilesConfigDialog`
- `SimilarityProgressDialog` → `SimilarFilesProgressDialog`

**Services** (en `services/`):

- `DuplicateExactDetector` → `ExactCopiesDetector`
- `DuplicateSimilarDetector` → `SimilarFilesDetector`
- Archivos: `duplicateexactdetector.py` → `exactcopiesdetector.py`
- Archivos: `duplicatesimilardetector.py` → `similarfilesdetector.py`

**Workers** (en `ui/workers.py`):

- `SimilarityAnalysisWorker` → `SimilarFilesAnalysisWorker`

**View Models** (en `services/viewmodels.py`):

- `ExactDuplicatesResult` → `ExactCopiesResult`
- `SimilarDuplicatesResult` → `SimilarFilesResult`


### 3. Títulos de Diálogos

**Diálogo principal de copias exactas**:

- **Antes**: "Duplicados Exactos" o "Gestionar Duplicados Exactos"
- **Después**: "Gestionar copias exactas"

**Diálogo principal de archivos similares**:

- **Antes**: "Duplicados Similares" o "Gestionar Duplicados Similares"
- **Después**: "Gestionar archivos similares"

**Diálogo de configuración**:

- **Antes**: "Configurar Análisis de Duplicados Similares"
- **Después**: "Configurar análisis de archivos similares"

**Diálogo de progreso**:

- **Antes**: "Analizando Duplicados Similares"
- **Después**: "Analizando archivos similares"


### 4. Identificadores de Cards en Stage 3

**En `ui/stages/stage3window.py` (o donde se definan las cards)**:

**Antes**:

```python
self.tool_cards = {
    "exact_duplicates": ExactDuplicatesCard(...),
    "similar_duplicates": SimilarDuplicatesCard(...),
    # ... otras cards
}
```

**Después**:

```python
self.tool_cards = {
    "exact_copies": ExactCopiesCard(...),
    "similar_files": SimilarFilesCard(...),
    # ... otras cards
}
```


### 5. Constantes y Configuración

**En `config.py` o archivos de configuración**:

**Antes**:

```python
TOOL_EXACT_DUPLICATES = "exact_duplicates"
TOOL_SIMILAR_DUPLICATES = "similar_duplicates"
```

**Después**:

```python
TOOL_EXACT_COPIES = "exact_copies"
TOOL_SIMILAR_FILES = "similar_files"
```


### 6. Comentarios y Docstrings

**Actualizar documentación en todos los archivos relevantes**:

**Ejemplo de docstring actualizado**:

**Antes**:

```python
class ExactDuplicatesDialog(QDialog):
    """
    Diálogo para gestionar duplicados exactos.
    Muestra archivos idénticos byte a byte (SHA256).
    """
```

**Después**:

```python
class ExactCopiesDialog(QDialog):
    """
    Diálogo para gestionar copias exactas.
    Muestra fotos y vídeos idénticos digitalmente (mismo SHA256),
    incluso si tienen nombres diferentes.
    """
```


### 7. Persistencia de Datos

**En `utils/settingsmanager.py` o donde se guarden preferencias**:

Si existen claves guardadas con nombres antiguos, mantener compatibilidad:

```python
# Mapeo de compatibilidad
LEGACY_KEYS = {
    "exact_duplicates": "exact_copies",
    "similar_duplicates": "similar_files"
}
```

O migrar datos explícitamente:

```python
def migrate_settings():
    """Migra claves antiguas a nuevos nombres."""
    settings = QSettings()
    
    # Migrar exact_duplicates → exact_copies
    if settings.contains("analysis_cache/exact_duplicates"):
        value = settings.value("analysis_cache/exact_duplicates")
        settings.setValue("analysis_cache/exact_copies", value)
        settings.remove("analysis_cache/exact_duplicates")
    
    # Migrar similar_duplicates → similar_files
    if settings.contains("analysis_cache/similar_duplicates"):
        value = settings.value("analysis_cache/similar_duplicates")
        settings.setValue("analysis_cache/similar_files", value)
        settings.remove("analysis_cache/similar_duplicates")
```


### 8. Imports a Actualizar

**Actualizar todos los imports en archivos que usen las clases renombradas**:

**Antes**:

```python
from ui.dialogs.exactduplicatesdialog import ExactDuplicatesDialog
from ui.dialogs.similardialog import SimilarDuplicatesDialog
from services.duplicateexactdetector import DuplicateExactDetector
from services.duplicatesimilardetector import DuplicateSimilarDetector
```

**Después**:

```python
from ui.dialogs.exactcopiesdialog import ExactCopiesDialog
from ui.dialogs.similarfilesdialog import SimilarFilesDialog
from services.exactcopiesdetector import ExactCopiesDetector
from services.similarfilesdetector import SimilarFilesDetector
```


### 9. Archivos de Documentación

**Actualizar en**:

- `README.md` → Sección de herramientas disponibles
- `Funcionalidades.txt` → Renombrar herramientas 3 y 4
- `PROMPT-_MVP2.md` → Actualizar textos de las cards
- `CHANGELOG.md` → Añadir entrada sobre el cambio de nomenclatura

**Ejemplo de entrada en CHANGELOG**:

```markdown
## [Versión X.X.X] - 2025-11-08

### Changed
- Renombrada herramienta "Duplicados exactos" → "Copias exactas"
- Renombrada herramienta "Duplicados similares" → "Archivos similares"
- Actualizado nomenclatura en todas las clases, archivos y diálogos relacionados
- Mejorada claridad de las descripciones en las cards de Stage 3
```


### 10. Tests a Actualizar

**Si existen tests unitarios** (en `tests/`):

**Antes**:

```python
def test_exact_duplicates_detection():
    detector = DuplicateExactDetector()
    # ...

def test_similar_duplicates_detection():
    detector = DuplicateSimilarDetector()
    # ...
```

**Después**:

```python
def test_exact_copies_detection():
    detector = ExactCopiesDetector()
    # ...

def test_similar_files_detection():
    detector = SimilarFilesDetector()
    # ...
```


## Tabla de Mapeo Completo

| Elemento | Antes | Después |
| :-- | :-- | :-- |
| **Título Card 1** | Duplicados Exactos | Copias exactas |
| **Título Card 2** | Duplicados Similares | Archivos similares |
| **Archivo Dialog 1** | `exactduplicatesdialog.py` | `exactcopiesdialog.py` |
| **Archivo Dialog 2** | `similardialog.py` | `similarfilesdialog.py` |
| **Clase Dialog 1** | `ExactDuplicatesDialog` | `ExactCopiesDialog` |
| **Clase Dialog 2** | `SimilarDuplicatesDialog` | `SimilarFilesDialog` |
| **Archivo Service 1** | `duplicateexactdetector.py` | `exactcopiesdetector.py` |
| **Archivo Service 2** | `duplicatesimilardetector.py` | `similarfilesdetector.py` |
| **Clase Service 1** | `DuplicateExactDetector` | `ExactCopiesDetector` |
| **Clase Service 2** | `DuplicateSimilarDetector` | `SimilarFilesDetector` |
| **Diálogo Config** | Configurar Análisis de Duplicados Similares | Configurar análisis de archivos similares |
| **Diálogo Progress** | Analizando Duplicados Similares | Analizando archivos similares |
| **ID Card Stage 3** | `exact_duplicates`, `similar_duplicates` | `exact_copies`, `similar_files` |

## Instrucciones para la IA

**Por favor, realiza los siguientes cambios en todo el código de Pixaro Lab**:

1. **Renombra todos los archivos** según la tabla de mapeo
2. **Renombra todas las clases** Python según la tabla de mapeo
3. **Actualiza todos los imports** para usar los nuevos nombres
4. **Actualiza todos los textos de UI**:
    - Títulos de cards en Stage 3
    - Descripciones de cards
    - Títulos de diálogos
    - Textos de botones (si es necesario)
5. **Actualiza comentarios y docstrings** para reflejar los nuevos nombres
6. **Actualiza archivos de documentación** (README.md, Funcionalidades.txt, etc.)
7. **Mantén compatibilidad** en persistencia de datos si es necesario (añade código de migración)
8. **Actualiza tests** si existen

**Importante**:

- Mantener la funcionalidad intacta (solo cambiar nombres)
- No cambiar la lógica de negocio
- Asegurar que todas las referencias estén actualizadas
- Verificar que no queden imports rotos

**Capitalización en español**:

- Los títulos de cards y diálogos deben usar minúsculas excepto la primera letra: "Copias exactas", "Archivos similares"
- Esto sigue las convenciones del idioma español


## Checklist de Validación

Después de realizar los cambios, verifica:

- [ ] La aplicación compila sin errores de import
- [ ] Las cards en Stage 3 muestran los nuevos títulos y descripciones
- [ ] Los diálogos se abren correctamente con los nuevos títulos
- [ ] No quedan referencias a los nombres antiguos en el código
- [ ] Los tests pasan correctamente (si existen)
- [ ] La documentación está actualizada
- [ ] Los comentarios reflejan los nuevos nombres

***

**Fecha de cambio**: 2025-11-08
**Razón**: Mejorar claridad y profesionalidad de la nomenclatura de herramientas de detección de duplicados.[^12][^11]
<span style="display:none">[^1][^10][^2][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://learn.microsoft.com/es-es/microsoft-copilot-studio/code-interpreter-for-prompts

[^2]: https://learn.microsoft.com/es-es/power-apps/maker/model-driven-apps/copilot-chat-prompt-guide

[^3]: https://www.abd.es/2025/06/crear-prompts-copilot/

[^4]: https://learn.microsoft.com/es-es/microsoft-copilot-studio/authoring-ask-with-adaptive-card

[^5]: https://magda.es/trucos/asi-puedes-introducir-variables-en-los-prompts-de-copilot-para-guardarlos-y-reutilizarlos/

[^6]: https://www.youtube.com/watch?v=TE-bkn2LYXM

[^7]: https://blog.grupoactive.es/crear-prompts-en-microsoft-copilot/

[^8]: https://www.reddit.com/r/PromptEngineering/comments/1j5mca4/i_made_chatgpt_45_leak_its_system_prompt/

[^9]: https://jmfloreszazo.com/mejora-la-calidad-del-codigo-en-net-con-github-copilot-y-prompts-personalizados/

[^10]: https://learn.microsoft.com/es-es/microsoft-copilot-studio/code-interpreter-prompts-examples

[^11]: PROMPT-_MVP2.md

[^12]: Funcionalidades.txt

