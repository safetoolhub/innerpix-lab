<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# PROMPT COMPLETO PARA REDISEÑO DE SMART_STATS_BAR


***

## CONTEXTO

Archivo: `top_bar.py` - Aplicación Python/Qt6 de normalización de archivos multimedia.

**Objetivo del rediseño**:

1. Reducir espacio vertical de `smart_stats_bar` de ~200px a ~110px
2. Reorganizar estadísticas en grid 3×2 más compacto
3. Añadir badge compacto de metadata al control bar
4. Añadir botón "About" faltante
5. Simplificar color coding a amarillo/verde únicamente

***

## PARTE 1: MODIFICACIONES AL CONTROL BAR

### **1.1. ESTRUCTURA COMPLETA DEL CONTROL BAR**

El **Control Bar** mantiene su altura de 60px. Elementos organizados horizontalmente (de izquierda a derecha):

#### **Layout horizontal**:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ [Icon] App │  [📁 /path/dir [1.2k│45GB] [▼]] │ [Botones Acción] │ [▼⚙️ℹ️] │
└────────────────────────────────────────────────────────────────────────────┘
```


***

### **1.2. ELEMENTOS DEL CONTROL BAR**

#### **A. Título de la aplicación** *(sin cambios)*

- Icono app + texto nombre
- Layout container con 8px spacing
- Ancho: ~120-150px flexible


#### **B. Espaciador**

- 12px


#### **C. Campo de directorio con metadata badge** *(MODIFICADO)*

**Container exterior**:

- Min-width: 350px
- Max-width: 600px
- Flex: stretch=1

**Estructura interna del fieldwidget**:

```
┌──────────────────────────────────────────────────────────────┐
│ [📁] /Users/nombre/Photos/2024  [1.2k│45GB]  [✓ Analizado] [▼]│
└──────────────────────────────────────────────────────────────┘
```

**Componentes (de izquierda a derecha)**:

1. **Icono de carpeta** (`self.foldericon`)
    - Tamaño: 24×24px
    - Visible solo después de análisis completado
    - Click → abre carpeta en explorador
    - Sin cambios
2. **Campo de texto del directorio** (`self.directoryedit`)
    - QLineEdit read-only
    - Stretch: 1 (flexible)
    - Placeholder: "Ningún directorio seleccionado"
    - Color texto: `#334155` (slate-700)
    - **Aplicar text elide middle** cuando necesario para priorizar visibilidad del badge
    - Sin cambios en funcionalidad
3. **📊 BADGE DE METADATA** (NUEVO)
    - **Widget**: QLabel (`self.metadata_badge`)
    - **Tamaño**: Ancho ~80-90px (auto según contenido), altura 20px
    - **Contenido**: `"1.2k │ 45GB"` (archivos abreviados │ espacio abreviado)
    - **Visible**: Solo después de análisis completado (mismo comportamiento que analysis badge)
    - **Posición**: Entre `directoryedit` y `analysisbadge`

**Formato de texto**:
    - Archivos: Abreviado con función `format_count_short()`
        - `< 1,000`: número completo (ej: "234")
        - `>= 1,000 < 1M`: "X.Xk" (ej: "1.2k", "45.7k")
        - `>= 1M`: "X.XM" (ej: "1.5M")
    - Espacio: Abreviado con función `format_size_short()`
        - Formato: "XXB", "XXKB", "XXMB", "XXGB", "XXTB"
        - Sin decimales para GB/TB
    - Separador: `│` (pipe con espacios, U+2502)

**Estilo CSS**:

```python
QLabel {
    background: rgba(var(--color-brown-600-rgb), 0.08);
    color: var(--color-text-secondary);
    font-family: var(--font-family-mono);
    font-size: 10px;
    font-weight: 500;
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid rgba(var(--color-brown-600-rgb), 0.12);
}
```

**Dark mode**:

```python
[data-color-scheme="dark"] QLabel {
    background: rgba(var(--color-gray-400-rgb), 0.12);
    border: 1px solid rgba(var(--color-gray-400-rgb), 0.20);
}
```

**Tooltip (hover)**:
    - Texto completo sin abreviaciones: `"1,234 archivos · 45.6 GB"`
    - Formato con separador punto medio (·)
    - Números con separadores de miles (comas)
4. **Badge "Analizado"** (`self.analysisbadge`) *(sin cambios)*
    - Ancho automático
    - Solo visible tras análisis completado
    - Fondo verde claro, texto "✓ Analizado"
5. **Botón historial** (`self.historybtn`) *(sin cambios)*
    - 26×24px
    - Icono flecha abajo
    - Dropdown con historial de directorios

***

**Implementación técnica del fieldlayout**:

```python
# En el QHBoxLayout del fieldwidget (modificar orden):
fieldlayout.addWidget(self.foldericon)           # 24px
fieldlayout.addWidget(self.directoryedit, 1)     # stretch (flexible)
fieldlayout.addWidget(self.metadata_badge)       # 80-90px (NUEVO)
fieldlayout.addWidget(self.analysisbadge)        # auto width
fieldlayout.addWidget(self.historybtn)           # 26px
```

**Funciones auxiliares a crear**:

```python
def format_count_short(count: int) -> str:
    """Formato abreviado de conteo de archivos."""
    if count >= 1_000_000:
        return f"{count/1_000_000:.1f}M"
    elif count >= 1_000:
        return f"{count/1_000:.1f}k"
    return str(count)

def format_size_short(bytes_size: int) -> str:
    """Formato abreviado de tamaño de archivos."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{int(bytes_size)}{unit}"
        bytes_size /= 1024
    return f"{int(bytes_size)}PB"

def format_count_full(count: int) -> str:
    """Formato completo con separadores de miles."""
    return f"{count:,}"

def format_size_full(bytes_size: int) -> str:
    """Formato completo de tamaño legible."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"
```

**Método de actualización del badge**:

```python
def update_metadata_badge(self, file_count: int, total_size: int):
    """Actualiza el badge de metadata con valores abreviados."""
    short_count = format_count_short(file_count)
    short_size = format_size_short(total_size)
    
    self.metadata_badge.setText(f"{short_count} │ {short_size}")
    
    # Tooltip con valores completos
    full_count = format_count_full(file_count)
    full_size = format_size_full(total_size)
    self.metadata_badge.setToolTip(f"{full_count} archivos · {full_size}")
    
    self.metadata_badge.setVisible(True)
```


***

#### **D. Botones de acción** *(sin cambios funcionales)*

Botones con visibilidad dinámica según estado:

1. **Seleccionar/Cambiar** (`self.selectbtn`)
2. **Analizar** (`self.analyzebtn`)
3. **Re-analizar** (`self.reanalyzebtn`)
4. **Detener** (`self.stopbtn`)

*(Mantener lógica actual de visibilidad por estados)*

***

#### **E. Espaciador**

- 6px

***

#### **F. Botón toggle stats** (`self.statstogglebtn`) *(sin cambios)*

- 32×32px
- Icono chevron ▲/▼
- Visible solo post-análisis
- Colapsa/expande smart_stats_bar

***

#### **G. Botón configuración** (`configbtn`) *(sin cambios)*

- 32×32px
- Icono settings (engranaje)
- Color: `#64748b`
- Click: `self.mainwindow.toggle_config()`
- Tooltip: "Configuración"

***

#### **H. Botón About** *(AÑADIR NUEVO)*

**Widget**: `aboutbtn` (crear nuevo QPushButton)

**Especificaciones**:

- **Tamaño**: 32×32px fijo
- **Icono**: `info` (círculo con "i") o `help` (interrogación)
- **Color icono**: `#64748b` (gris, idéntico al botón config)
- **Tamaño icono**: 20px
- **Cursor**: `Qt.CursorShape.PointingHandCursor`
- **Tooltip**: "Acerca de"
- **Posición**: Inmediatamente después del botón de configuración

**Estilo CSS** (idéntico al botón configuración):

```python
QPushButton {
    background: transparent;
    border: none;
    border-radius: 6px;
}
QPushButton:hover {
    background: rgba(var(--color-brown-600-rgb), 0.08);
}
QPushButton:pressed {
    background: rgba(var(--color-brown-600-rgb), 0.12);
}

/* Dark mode */
[data-color-scheme="dark"] QPushButton:hover {
    background: rgba(var(--color-gray-400-rgb), 0.15);
}
[data-color-scheme="dark"] QPushButton:pressed {
    background: rgba(var(--color-gray-400-rgb), 0.25);
}
```

**Click event**:

```python
if self.mainwindow is not None:
    aboutbtn.clicked.connect(self.mainwindow.show_about)
```

**Código completo a añadir**:

```python
# Crear botón About
aboutbtn = QPushButton()
iconmanager.setbuttonicon(aboutbtn, 'info', color='#64748b', size=20)
aboutbtn.setFixedSize(32, 32)
aboutbtn.setCursor(Qt.CursorShape.PointingHandCursor)
aboutbtn.setToolTip("Acerca de")
aboutbtn.setStyleSheet("""
    QPushButton {
        background: transparent;
        border: none;
        border-radius: 6px;
    }
    QPushButton:hover {
        background: rgba(var(--color-brown-600-rgb), 0.08);
    }
    QPushButton:pressed {
        background: rgba(var(--color-brown-600-rgb), 0.12);
    }
""")

# Conectar señal si mainwindow está disponible
if self.mainwindow is not None:
    aboutbtn.clicked.connect(self.mainwindow.show_about)

# Añadir al layout (después de configbtn)
layout.addWidget(aboutbtn)
```


***

### **RESUMEN VISUAL DEL CONTROL BAR COMPLETO**

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│  [📱] App  │  [📁] /Photos/2024  [1.2k│45GB]  [✓] [▼]  │  [Cambiar] [▼⚙️ℹ️]  │
│                                    ↑                                          │
│                            metadata badge nuevo                               │
└───────────────────────────────────────────────────────────────────────────────┘
```


***

## PARTE 2: REDISEÑO DE SMART_STATS_BAR

### **2.1. OBJETIVO DE ALTURA**

**Antes**: ~200px expandido
**Después**: ~110px expandido
**Reducción**: 45%

***

### **2.2. NUEVA ESTRUCTURA: GRID 3×2**

**Layout**: 3 columnas × 2 filas = 6 estadísticas distribuidas en 3 categorías funcionales

```
┌──────────────────┬──────────────────┬──────────────────┐
│  REDUNDANCIAS    │   DUPLICADOS     │  ORGANIZACIÓN    │
├──────────────────┼──────────────────┼──────────────────┤
│ 🟡 Live Photos   │ 🟡 Exactos       │ 🟡 Renombrar     │
│ 🟡 HEIC Dupls.   │ ⚪ Similares     │ 🟡 Organizar     │
└──────────────────┴──────────────────┴──────────────────┘
```


***

### **2.3. DISTRIBUCIÓN POR COLUMNAS**

#### **COLUMNA 1: "REDUNDANCIAS"**

Archivos duplicados técnicos:

- **Fila 1**: Live Photos detectados
- **Fila 2**: Duplicados HEIC


#### **COLUMNA 2: "DUPLICADOS"**

Duplicados por contenido:

- **Fila 1**: Duplicados exactos
- **Fila 2**: Duplicados similares


#### **COLUMNA 3: "ORGANIZACIÓN"**

Acciones de estructuración:

- **Fila 1**: Archivos a renombrar
- **Fila 2**: Archivos a organizar

***

### **2.4. ESPECIFICACIONES VISUALES DETALLADAS**

#### **Medidas exactas del contenedor**:

```
8px     (padding-top)
18px    (título columna + spacing)
36px    (fila 1)
6px     (spacing entre filas)
36px    (fila 2)
8px     (padding-bottom)
─────
112px   TOTAL
```

**Objetivo**: 110-112px altura total de smart_stats_bar cuando expandido

***

#### **Títulos de columna**:

- **Texto**: `"REDUNDANCIAS"`, `"DUPLICADOS"`, `"ORGANIZACIÓN"` (mayúsculas)
- **Fuente**: `var(--font-size-xs)` (10-11px)
- **Weight**: `var(--font-weight-semibold)` (550-600)
- **Color**: `var(--color-text-secondary)`
- **Letter-spacing**: `0.05em` (tracking amplio)
- **Margin-bottom**: 6px
- **Alineación**: centrado horizontalmente en su columna

***

#### **Items de estadística (filas)**:

**Layout de cada item**:

```
┌────────────────────────────────┐
│ [icono] Label        Número    │  ← 36px altura
└────────────────────────────────┘
```

**Estructura interna**:

- Display: `flex`
- Align-items: `center`
- Justify-content: `space-between`
- Padding: `6px vertical, 8px horizontal`
- Border-radius: `var(--radius-sm)` (6px)
- Cursor: `pointer`
- Transition: `150ms ease` (var(--duration-fast))

**Contenido**:

- **Izquierda**: Icono (14-16px) + Label (12px, weight 400)
- **Derecha**: Número (12px, weight 550-600)
- Gap entre icono y label: 6px

***

### **2.5. SISTEMA DE COLOR BINARIO (AMARILLO/VERDE)**

**Regla única**: No hay jerarquía. Todos los tipos de detección tienen la misma prioridad visual.

***

#### **🟡 ESTADO AMARILLO (Detectado)**

**Condición**: `count > 0`

**Estilos**:

- **Background**: `rgba(var(--color-warning-rgb), 0.12)`
- **Border**: `1px solid rgba(var(--color-warning-rgb), 0.25)`
- **Icono**: `var(--color-warning)`
- **Label**: `var(--color-text)` (texto normal)
- **Número**: `var(--color-warning)` + `var(--font-weight-semibold)`

**Hover**:

- Background: `rgba(var(--color-warning-rgb), 0.17)` (aumentar opacidad +0.05)
- Border: `rgba(var(--color-warning-rgb), 0.35)` (aumentar opacidad +0.10)
- Transform: `scale(1.02)` muy sutil (opcional)

**Click feedback**:

- Transform: `scale(0.98)` durante 100ms

***

#### **🟢 ESTADO VERDE (Sin detección)**

**Condición**: `count === 0`

**Estilos**:

- **Background**: `rgba(var(--color-success-rgb), 0.08)`
- **Border**: `1px solid rgba(var(--color-success-rgb), 0.15)`
- **Icono**: `var(--color-success)` (verde/teal)
- **Label**: `var(--color-text-secondary)` (gris secundario)
- **Número**: Mostrar `"✓"` (checkmark) o `"0"` en `var(--color-text-secondary)`

**Hover**:

- Background: `rgba(var(--color-success-rgb), 0.13)`
- Border: `rgba(var(--color-success-rgb), 0.25)`

**Click feedback**:

- Transform: `scale(0.98)` durante 100ms

***

#### **⚪ ESTADO GRIS (No analizado)**

**Condición**: Funcionalidad no ejecutada (ej: duplicados similares sin analizar)

**Estilos**:

- **Background**: `var(--color-secondary)` (gris neutro)
- **Border**: `1px solid var(--color-border)`
- **Icono**: `var(--color-text-secondary)` con `opacity: 0.5`
- **Label**: `var(--color-text-secondary)`
- **Número**: `"—"` (em dash, U+2014) o texto `"No analizado"`

**Hover**:

- Background: `var(--color-secondary-hover)`
- Border: Sin cambio

**Click feedback**:

- Transform: `scale(0.98)` durante 100ms

***

### **2.6. INTERACTIVIDAD Y ACCESIBILIDAD**

#### **Estados interactivos**:

- **Default**: Estilos según estado (amarillo/verde/gris)
- **Hover**: Aumentar opacidad de fondo y borde
- **Active/Click**: Micro-animación scale(0.98)
- **Focus (teclado)**:
    - Outline: `var(--focus-outline)` (2px solid var(--color-primary))
    - Box-shadow: `var(--focus-ring)` (0 0 0 3px rgba(teal, 0.4))


#### **Transiciones**:

```css
transition: all var(--duration-fast) var(--ease-standard);
/* 150ms cubic-bezier(0.16, 1, 0.3, 1) */
```


#### **Tooltips**:

- Mantener tooltips descriptivos actuales
- Formato: "Descripción de la funcionalidad"
- Ejemplo: "Detecta pares de Live Photos (foto + video MOV)"

***

### **2.7. MAPEO DE ESTADÍSTICAS**

Mantener las mismas variables y métodos del código actual:


| **Columna** | **Fila** | **Label UI** | **Variable actual** | **Pestaña destino** |
| :-- | :-- | :-- | :-- | :-- |
| Redundancias | 1 | Live Photos | `live_photos_count` | Pestaña Live Photos |
| Redundancias | 2 | HEIC Duplicados | `heic_count` | Pestaña HEIC |
| Duplicados | 1 | Exactos | `exact_duplicates_count` | Pestaña Duplicados |
| Duplicados | 2 | Similares | `similar_duplicates_count` | Pestaña Duplicados |
| Organización | 1 | Renombrar | `rename_count` | Pestaña Renombrar |
| Organización | 2 | Organizar | `organize_count` | Pestaña Organizar |

**Click event**: Cada item emite señal `stats_clicked` con el nombre de la pestaña correspondiente (mantener lógica actual)

***

### **2.8. SEPARADORES ENTRE COLUMNAS**

**Diseño actual a mantener**:

- Línea vertical con gradiente sutil
- Ancho: 1px
- Margin lateral: 20-24px (según espacio disponible)
- Gradiente: Transparente arriba/abajo, visible en el centro

**Código referencia**:

```python
separator = QFrame()
separator.setFrameShape(QFrame.Shape.VLine)
separator.setStyleSheet("""
    QFrame {
        border: none;
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 transparent,
            stop:0.2 rgba(var(--color-brown-600-rgb), 0.15),
            stop:0.8 rgba(var(--color-brown-600-rgb), 0.15),
            stop:1 transparent
        );
        width: 1px;
        margin: 0px 20px;
    }
""")
```


***

### **2.9. LAYOUT TÉCNICO (Qt)**

**Opción recomendada**: `QHBoxLayout` con 3 `QVBoxLayout` anidados (uno por columna)

```python
# Layout principal horizontal
main_layout = QHBoxLayout()
main_layout.setContentsMargins(16, 8, 16, 8)  # L, T, R, B
main_layout.setSpacing(0)

# COLUMNA 1: Redundancias
col1_layout = QVBoxLayout()
col1_layout.setSpacing(6)
col1_title = QLabel("REDUNDANCIAS")
col1_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
# ... estilo título
col1_layout.addWidget(col1_title)
col1_layout.addWidget(live_photos_item)  # StatsCard
col1_layout.addWidget(heic_item)         # StatsCard

# Separador
separator1 = create_separator()

# COLUMNA 2: Duplicados
col2_layout = QVBoxLayout()
# ... similar a col1

# Separador
separator2 = create_separator()

# COLUMNA 3: Organización
col3_layout = QVBoxLayout()
# ... similar a col1

# Añadir al layout principal
main_layout.addLayout(col1_layout, 1)
main_layout.addWidget(separator1)
main_layout.addLayout(col2_layout, 1)
main_layout.addWidget(separator2)
main_layout.addLayout(col3_layout, 1)
```

**Alternativa**: `QGridLayout` con 3 columnas × 3 filas (título + 2 items)

***

### **2.10. COMPORTAMIENTO RESPONSIVE**

#### **Ventanas > 1200px**:

- 3 columnas con padding generoso (margin separadores: 24px)
- Todas las dimensiones según especificación


#### **Ventanas 900-1200px**:

- 3 columnas con padding reducido (margin separadores: 16px)
- Considerar reducir font-size en 1px si necesario


#### **Ventanas < 900px** (prioridad baja):

- Opción A: Mantener 3 columnas con scroll horizontal
- Opción B: Colapsar a stack vertical (3 secciones apiladas)
- Decisión según pruebas de usabilidad

***

### **2.11. ANIMACIÓN DE TOGGLE COLAPSABLE**

**Mantener funcionalidad actual** del botón toggle (▲/▼).

Cuando smart_stats_bar se colapsa:

- **Altura**: `0px` (oculto completamente)
- **Animación**: `var(--duration-normal)` (250ms) con `var(--ease-standard)`
- **Overflow**: `hidden`
- **Transición suave**: height + opacity

**Método actual a preservar**:

```python
def toggle_summary(self):
    self.is_summary_expanded = not self.is_summary_expanded
    # ... lógica de animación con QPropertyAnimation
```


***

## PARTE 3: CÓDIGO ACTUAL DE REFERENCIA

### **Archivos involucrados**:

- **Principal**: `top_bar.py` (adjunto)
- **Dependencias**: `config.py`, `ui/styles.py`, `utils/iconmanager.py`


### **Clases relevantes**:

- `TopBar` (contenedor principal)
- `SmartStatsBar` (componente a rediseñar completamente)
- `StatsCard` (items individuales clickeables - posiblemente reutilizar o rediseñar)


### **Mantener sin modificar**:

- Sistema de señales Qt (`stats_clicked`, `select_directory_requested`, etc.)
- Métodos de actualización de estados (`set_state`, `update_stats`)
- Lógica de toggle colapsable
- Sistema de iconos (`iconmanager`)
- Variables CSS del design system


### **Modificar**:

1. Layout de `SmartStatsBar`: De múltiples filas horizontales → Grid 3×2
2. Añadir `metadata_badge` al campo de directorio
3. Añadir botón `aboutbtn` después de `configbtn`
4. Simplificar color coding a 3 estados (amarillo/verde/gris)
5. Ajustar todas las dimensiones para objetivo de 110px de altura en stats bar

***

## PARTE 4: RESULTADO ESPERADO

### **Comparación antes/después**:

**ANTES**:

```
Control Bar:            60px
Smart Stats Bar:       200px (expandido)
────────────────────────────
TOTAL:                 260px
```

**DESPUÉS**:

```
Control Bar:            60px (con metadata badge integrado)
Smart Stats Bar:       110px (expandido, grid 3×2)
────────────────────────────
TOTAL:                 170px
────────────────────────────
REDUCCIÓN:             35%
```


### **Mejoras de UX**:

✅ Información general compacta y siempre visible (badge en control bar)
✅ Estadísticas agrupadas conceptualmente (3 categorías funcionales claras)
✅ Escaneo visual más rápido (grid organizado de 6 items vs lista larga)
✅ Color coding simple y consistente (amarillo=detectado, verde=OK, gris=no analizado)
✅ 35% menos espacio vertical consumido
✅ Todos los botones de acción presentes (incluyendo About)

***

## PARTE 5: CONSIDERACIONES TÉCNICAS

### **1. Formato de números**:

Usar las funciones auxiliares definidas en sección 1.2.C para mantener consistencia en toda la app.

### **2. Design system**:

Todas las variables CSS ya están definidas en el código actual. Usar exclusivamente:

- `--color-warning`, `--color-warning-rgb`
- `--color-success`, `--color-success-rgb`
- `--color-text`, `--color-text-secondary`
- `--font-size-xs`, `--font-size-sm`
- `--font-weight-normal`, `--font-weight-semibold`
- `--radius-sm`, `--radius-base`
- `--duration-fast`, `--ease-standard`


### **3. Elide del path**:

Usar `QFontMetrics.elidedText()` con `Qt.TextElideMode.ElideMiddle` para el directorio, asegurando que el metadata badge siempre sea visible (prioridad visual).

### **4. Testing**:

- Probar con ventanas de diferentes anchos (mínimo recomendado: 800px)
- Verificar estados: empty → ready → analyzing → analyzed
- Verificar todos los estados de color (amarillo/verde/gris) con diferentes valores de count
- Verificar tooltips en metadata badge y stats items
- Verificar navegación por teclado (focus states)


### **5. Manejo de estados**:

El metadata badge debe sincronizarse con el analysis badge:

- Ambos visibles solo después de análisis completado
- Ambos ocultos en estados `empty`, `ready`, `analyzing`
- Actualizar simultáneamente con el método `update_metadata_badge()`

***

## ENTREGABLE FINAL

**Código Python/Qt6 modificado** que implemente:

1. ✅ Metadata badge compacto en control bar (campo directorio)
2. ✅ Botón "About" añadido después del botón de configuración
3. ✅ Smart Stats Bar rediseñado con grid 3 columnas × 2 filas
4. ✅ Sistema de color amarillo/verde/gris según estado de detección
5. ✅ Altura total smart_stats_bar ~110px con spacing especificado
6. ✅ Funciones auxiliares de formato (números abreviados y completos)
7. ✅ Mantener toda la funcionalidad interactiva actual (clicks, tooltips, toggle)
8. ✅ Mantener sistema de señales y métodos de actualización existentes
9. ✅ Responsive básico (ventanas >900px)

***

**FIN DEL PROMPT** 🚀

