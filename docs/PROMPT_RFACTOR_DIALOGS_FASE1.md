

## **PROMPT 1: Refactorización Fase 1 - exact_copies_dialog.py - Header y Métricas**

```
Refactoriza el archivo `ui/dialogs/exact_copies_dialog.py` siguiendo estas reglas estrictas de Pixaro Lab:

### Objetivo
Actualizar la sección superior del diálogo (header explicativo y métricas) para usar Material Design consistente con `organization_dialog.py` como referencia.

### Reglas obligatorias (PEP 8 y Pixaro Lab):
1. **NO usar emojis** (💾, 🖼️, etc.) - usar `icon_manager` exclusivamente
2. **Estilos SOLO de DesignSystem** (`ui/styles/design_system.py`) - prohibido CSS inline o hardcoded
3. Mantener type hints en todos los métodos
4. Mantener docstrings existentes
5. NO modificar lógica de negocio ni signals
6. Preservar funcionamiento de backup checkbox

### Cambios específicos:

#### 1. Header explicativo (método `init_ui()` - sección superior)
Reemplazar el frame de explicación actual por este patrón de `organization_dialog.py`:

```


# Header con icono y explicación

header = QFrame()
header.setStyleSheet(f"""
QFrame {{
background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
stop:0 {DesignSystem.COLOR_BG_1},
stop:1 {DesignSystem.COLOR_BG_2});
border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
border-radius: {DesignSystem.RADIUS_LG};
padding: {DesignSystem.SPACE_16};
}}
""")
header_layout = QHBoxLayout(header)
header_layout.setSpacing(int(DesignSystem.SPACE_12))

# Icono desde icon_manager (NO emoji)

icon_label = QLabel()
icon_label.setPixmap(
icon_manager.get_icon('content-copy', DesignSystem.COLOR_PRIMARY)
.pixmap(int(DesignSystem.ICON_SIZE_LG), int(DesignSystem.ICON_SIZE_LG))
)
icon_label.setFixedSize(int(DesignSystem.ICON_SIZE_LG), int(DesignSystem.ICON_SIZE_LG))
header_layout.addWidget(icon_label)

# Texto explicativo

explanation = QLabel(
"Se han detectado archivos idénticos (mismo contenido digital SHA256). "
"Puedes eliminar las copias redundantes conservando un original por grupo."
)
explanation.setWordWrap(True)
explanation.setStyleSheet(f"""
font-size: {DesignSystem.FONT_SIZE_BASE};
color: {DesignSystem.COLOR_TEXT};
line-height: 1.5;
""")
header_layout.addWidget(explanation, 1)
layout.addWidget(header)

```

#### 2. Métricas inline
Reemplazar el método `_create_inline_metric()` actual por esta versión estandarizada:

```

def _create_inline_metric(
self,
value: str,
label: str,
color: str = DesignSystem.COLOR_PRIMARY
) -> QFrame:
"""Crea una métrica inline con estilo Material Design.

    Args:
        value: Valor a mostrar (número, texto)
        label: Etiqueta descriptiva
        color: Color del borde izquierdo (accent color)
    
    Returns:
        QFrame con la métrica formateada
    """
    frame = QFrame()
    frame.setStyleSheet(f"""
        QFrame {{
            background-color: {DesignSystem.COLOR_BG_1};
            border-left: 3px solid {color};
            border-radius: {DesignSystem.RADIUS_MD};
            padding: {DesignSystem.SPACE_8};
        }}
    """)
    
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(
        int(DesignSystem.SPACE_8),
        int(DesignSystem.SPACE_4),
        int(DesignSystem.SPACE_8),
        int(DesignSystem.SPACE_4)
    )
    layout.setSpacing(int(DesignSystem.SPACE_2))
    
    value_label = QLabel(value)
    value_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_2XL};
        font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        color: {DesignSystem.COLOR_TEXT};
    """)
    
    desc_label = QLabel(label)
    desc_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_SM};
        color: {DesignSystem.COLOR_TEXT_SECONDARY};
    """)
    
    layout.addWidget(value_label)
    layout.addWidget(desc_label)
    
    return frame
    ```

#### 3. Actualizar llamadas a métricas
En `init_ui()`, donde se crean las métricas, actualizar a:

```

metrics_layout = QHBoxLayout()
metrics_layout.setSpacing(int(DesignSystem.SPACE_12))

# Grupos de duplicados

groups_metric = self._create_inline_metric(
str(self.analysis.groups_count),
"Grupos de duplicados",
DesignSystem.COLOR_PRIMARY
)
metrics_layout.addWidget(groups_metric)

# Copias a eliminar

copies_metric = self._create_inline_metric(
str(self.analysis.redundant_files_count),
"Copias redundantes",
DesignSystem.COLOR_WARNING
)
metrics_layout.addWidget(copies_metric)

# Espacio recuperable

space_metric = self._create_inline_metric(
format_size(self.analysis.recoverable_space),
"Espacio recuperable",
DesignSystem.COLOR_SUCCESS
)
metrics_layout.addWidget(space_metric)

metrics_layout.addStretch()
layout.addLayout(metrics_layout)

```

#### 4. Iconos en toolbar
Buscar todos los emojis en el toolbar (💾, búsqueda, etc.) y reemplazarlos por:

```


# Ejemplo: botón de guardar

save_button = QPushButton()
save_button.setIcon(icon_manager.get_icon('save', DesignSystem.COLOR_TEXT))
save_button.setToolTip("Guardar selección")
save_button.setStyleSheet(DesignSystem.get_tooltip_style())

```

### NO tocar:
- Lógica de estrategias de eliminación
- TreeWidget y su población
- Métodos de selección y filtrado
- Sistema de paginación
- Signals y slots
- Backup checkbox (viene de BaseDialog)

### Validación:
- Verifica que NO queden emojis en el código
- Verifica que NO haya colores hardcoded (ej: "#ffffff", "rgb()", etc.)
- Verifica que todos los estilos usen `DesignSystem.COLOR_*`, `DesignSystem.SPACE_*`, etc.
- Mantén todos los imports existentes y añade solo si es necesario
- Ejecuta el código y verifica que el diálogo se abre sin errores

¿Entendido? Responde solo con el código refactorizado del archivo completo.
```


***

## **PROMPT 2: Refactorización Fase 1 - heic_dialog.py - Header y Métricas**

```
Refactoriza el archivo `ui/dialogs/heic_dialog.py` aplicando los mismos cambios que en `exact_copies_dialog.py`, siguiendo el patrón Material Design de `organization_dialog.py`.

### Objetivo
Actualizar header explicativo y métricas para consistencia visual con el resto de diálogos.

### Reglas obligatorias (idénticas al prompt anterior):
1. **NO usar emojis** - usar `icon_manager`
2. **Estilos SOLO de DesignSystem**
3. Type hints obligatorios
4. NO modificar lógica de negocio
5. Preservar backup checkbox

### Cambios específicos:

#### 1. Header explicativo
Usa el mismo patrón del prompt anterior pero con icono apropiado:

```


# Icono para duplicados HEIC/JPG

icon_label.setPixmap(
icon_manager.get_icon('photo_library', DesignSystem.COLOR_PRIMARY)
.pixmap(int(DesignSystem.ICON_SIZE_LG), int(DesignSystem.ICON_SIZE_LG))
)

# Texto explicativo adaptado

explanation = QLabel(
"Se han detectado fotos en formato HEIC que tienen una copia idéntica en JPG. "
"Puedes eliminar los archivos HEIC para ahorrar espacio manteniendo los JPG."
)

```

#### 2. Métricas inline
Copia exactamente el método `_create_inline_metric()` del prompt anterior (idéntico).

#### 3. Actualizar métricas en `init_ui()`

```

metrics_layout = QHBoxLayout()
metrics_layout.setSpacing(int(DesignSystem.SPACE_12))

# Pares HEIC/JPG

pairs_metric = self._create_inline_metric(
str(self.analysis.total_pairs),
"Pares HEIC/JPG",
DesignSystem.COLOR_PRIMARY
)
metrics_layout.addWidget(pairs_metric)

# Espacio recuperable

space_metric = self._create_inline_metric(
format_size(self.analysis.total_heic_size),
"Espacio recuperable",
DesignSystem.COLOR_SUCCESS
)
metrics_layout.addWidget(space_metric)

metrics_layout.addStretch()
layout.addLayout(metrics_layout)

```

#### 4. Iconos en toolbar y paginación
Reemplaza todos los emojis por iconos de `icon_manager`:

```


# Ejemplo: navegación de páginas

prev_button.setIcon(icon_manager.get_icon('chevron_left', DesignSystem.COLOR_TEXT))
next_button.setIcon(icon_manager.get_icon('chevron_right', DesignSystem.COLOR_TEXT))
refresh_button.setIcon(icon_manager.get_icon('refresh', DesignSystem.COLOR_TEXT))

```

### NO tocar:
- TableWidget y población de datos
- Sistema de paginación
- Context menu
- Lógica de filtrado y búsqueda
- Signals y slots

### Validación:
- NO emojis
- NO colores hardcoded
- Todos los estilos desde DesignSystem
- Código ejecutable sin errores

Responde solo con el código refactorizado completo.
```


***

## **PROMPT 3: Refactorización Fase 1 - renaming_dialog.py - Header y Métricas**

```
Refactoriza el archivo `ui/dialogs/renaming_dialog.py` aplicando consistencia Material Design.

### Objetivo
Este diálogo ya está bastante limpio, solo necesita ajustes menores en header y métricas.

### Reglas obligatorias:
1. NO usar emojis - usar `icon_manager`
2. Estilos SOLO de DesignSystem
3. Type hints obligatorios
4. NO modificar lógica de negocio

### Cambios específicos:

#### 1. Header explicativo
Aplica el patrón estándar:

```


# Icono para renombrado

icon_label.setPixmap(
icon_manager.get_icon('drive_file_rename_outline', DesignSystem.COLOR_PRIMARY)
.pixmap(int(DesignSystem.ICON_SIZE_LG), int(DesignSystem.ICON_SIZE_LG))
)

# Texto explicativo

explanation = QLabel(
"Previsualización del renombrado de archivos. Revisa los cambios antes de aplicarlos. "
"Los archivos con conflictos están marcados para tu atención."
)

```

#### 2. Métricas inline
Usa el mismo método `_create_inline_metric()` estandarizado de los prompts anteriores.

#### 3. Actualizar métricas

```

metrics_layout = QHBoxLayout()
metrics_layout.setSpacing(int(DesignSystem.SPACE_12))

# Total archivos

total_metric = self._create_inline_metric(
str(len(self.rename_plan)),
"Archivos a renombrar",
DesignSystem.COLOR_PRIMARY
)
metrics_layout.addWidget(total_metric)

# Conflictos

if self.conflicts_count > 0:
conflicts_metric = self._create_inline_metric(
str(self.conflicts_count),
"Conflictos detectados",
DesignSystem.COLOR_WARNING
)
metrics_layout.addWidget(conflicts_metric)

metrics_layout.addStretch()
layout.addLayout(metrics_layout)

```

#### 4. Iconos en toolbar
Actualiza búsqueda, filtros y estadísticas:

```

search_icon = icon_manager.get_icon('search', DesignSystem.COLOR_TEXT_SECONDARY)
filter_icon = icon_manager.get_icon('filter_list', DesignSystem.COLOR_TEXT_SECONDARY)
stats_icon = icon_manager.get_icon('analytics', DesignSystem.COLOR_PRIMARY)

```

### NO tocar:
- TableWidget
- Sistema de filtrado
- Context menu
- Dry run mode
- Lógica de conflictos

### Validación:
- NO emojis
- NO colores hardcoded
- Estilos desde DesignSystem

Responde con el código refactorizado completo.
```


***

## **PROMPT 4: Refactorización Fase 1 - live_photos_dialog.py - Header y Métricas**

```
Refactoriza el archivo `ui/dialogs/live_photos_dialog.py` aplicando Material Design consistente.

### Objetivo
Este es el diálogo más simple, aplicar header y métricas estandarizadas.

### Reglas obligatorias:
1. NO usar emojis - usar `icon_manager`
2. Estilos SOLO de DesignSystem
3. Type hints obligatorios
4. NO modificar lógica de negocio

### Cambios específicos:

#### 1. Header explicativo
Aplica el patrón estándar:

```


# Icono para Live Photos

icon_label.setPixmap(
icon_manager.get_icon('photo_camera', DesignSystem.COLOR_PRIMARY)
.pixmap(int(DesignSystem.ICON_SIZE_LG), int(DesignSystem.ICON_SIZE_LG))
)

# Texto explicativo

explanation = QLabel(
"Se han detectado Live Photos de iOS (pares de imagen + video corto). "
"Puedes conservar solo la imagen, solo el video, o mantener ambos."
)

```

#### 2. Métricas inline
Usa el mismo método `_create_inline_metric()` estandarizado.

#### 3. Actualizar métricas

```

metrics_layout = QHBoxLayout()
metrics_layout.setSpacing(int(DesignSystem.SPACE_12))

# Grupos detectados

groups_metric = self._create_inline_metric(
str(len(self.analysis.groups)),
"Live Photos detectadas",
DesignSystem.COLOR_PRIMARY
)
metrics_layout.addWidget(groups_metric)

# Espacio según modo seleccionado

space_metric = self._create_inline_metric(
format_size(self._calculate_space_for_mode(self.selected_mode)),
"Espacio a liberar",
DesignSystem.COLOR_SUCCESS
)
metrics_layout.addWidget(space_metric)

metrics_layout.addStretch()
layout.addLayout(metrics_layout)

```

#### 4. RadioButtons de selección
Actualiza iconos en las opciones de modo:

```


# Modo: conservar imagen

keep_image_label = QLabel()
keep_image_label.setPixmap(
icon_manager.get_icon('image', DesignSystem.COLOR_TEXT)
.pixmap(int(DesignSystem.ICON_SIZE_MD), int(DesignSystem.ICON_SIZE_MD))
)

# Modo: conservar video

keep_video_label = QLabel()
keep_video_label.setPixmap(
icon_manager.get_icon('videocam', DesignSystem.COLOR_TEXT)
.pixmap(int(DesignSystem.ICON_SIZE_MD), int(DesignSystem.ICON_SIZE_MD))
)

# Modo: conservar ambos

keep_both_label = QLabel()
keep_both_label.setPixmap(
icon_manager.get_icon('collections', DesignSystem.COLOR_TEXT)
.pixmap(int(DesignSystem.ICON_SIZE_MD), int(DesignSystem.ICON_SIZE_MD))
)

```

### NO tocar:
- Lógica de CleanupMode
- Cálculo de espacio por modo
- Signals y slots
- TreeWidget

### Validación:
- NO emojis
- NO colores hardcoded
- Estilos desde DesignSystem

Responde con el código refactorizado completo.
```


***

## **PROMPT 5: Verificación y Testing Final**

```
Verifica que los 4 diálogos refactorizados cumplen estos criterios:

### Checklist obligatorio:

#### 1. NO emojis
Busca en todos los archivos `\u` o caracteres unicode de emojis (💾, 🖼️, 📸, etc.)
- `exact_copies_dialog.py`: ✅ / ❌
- `heic_dialog.py`: ✅ / ❌
- `renaming_dialog.py`: ✅ / ❌
- `live_photos_dialog.py`: ✅ / ❌

#### 2. NO colores hardcoded
Busca strings con: `#`, `rgb(`, `rgba(`
- Deben estar SOLO en `DesignSystem` references

#### 3. Consistencia de header
Todos los headers deben tener:
- Frame con gradient background
- Icono de `icon_manager` (tamaño `ICON_SIZE_LG`)
- QLabel con explicación
- Border radius `RADIUS_LG`
- Padding `SPACE_16`

#### 4. Consistencia de métricas
Todas las métricas deben usar:
- `_create_inline_metric()` con firma idéntica
- Border-left con color temático
- Valor: `FONT_SIZE_2XL` + `FONT_WEIGHT_BOLD`
- Label: `FONT_SIZE_SM` + `COLOR_TEXT_SECONDARY`

#### 5. Imports correctos
Verifica que todos tienen:
```

from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from utils.format_utils import format_size

```

#### 6. Type hints
Verifica que `_create_inline_metric()` tiene:
```

def _create_inline_metric(
self,
value: str,
label: str,
color: str = DesignSystem.COLOR_PRIMARY
) -> QFrame:

```

### Testing manual:
1. Ejecuta `python main.py`
2. Selecciona una carpeta de prueba
3. Completa el análisis
4. Abre cada diálogo desde Stage 3
5. Verifica:
   - Header se visualiza correctamente
   - Métricas se muestran alineadas
   - Iconos se renderizan (no aparecen cuadrados vacíos)
   - No hay errores en consola
   - Tooltips funcionan
   - Colores son consistentes entre diálogos

### Reporte:
Crea un reporte con:
- Lista de archivos modificados
- Resumen de cambios principales
- Problemas encontrados (si hay)
- Capturas de pantalla opcionales mostrando un diálogo antes/después

Responde con el reporte de verificación.
```
