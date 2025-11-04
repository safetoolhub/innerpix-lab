# PROMPT COMPLETO PARA DESARROLLO DE PIXARO LAB - VENTANA PRINCIPAL

## CONTEXTO DE LA APLICACIÓN

Pixaro Lab es una aplicación de escritorio multiplataforma (Linux, Windows, macOS) desarrollada en Python con PyQt6/PySide6 para analizar, previsualizar y ejecutar acciones sobre colecciones de imágenes y vídeos, principalmente orientada a fotos iOS.

La aplicación ofrece 6 herramientas principales:

1. **Limpieza de Live Photos** - Gestiona vídeos asociados a Live Photos
2. **Eliminación de duplicados HEIC/JPG** - Encuentra pares de archivos en ambos formatos
3. **Detección de duplicados exactos** - Identifica archivos idénticos byte-a-byte
4. **Detección de duplicados similares** - Detecta imágenes visualmente similares
5. **Organización de archivos** - Reorganiza por fecha, origen, categoría
6. **Renombrado de archivos** - Aplica esquemas de nombres personalizados

Cada herramienta tiene su propio diálogo implementado (live_photos_dialog.py, heic_dialog.py, etc.) que sigue el patrón: preview → plan → ejecutar, con política "backup-first" para operaciones destructivas.

La lógica de negocio está en `services/` y es PyQt6-free para permitir futura migración a móvil.

***

## OBJETIVO DEL DESARROLLO

Implementar la **ventana principal (MainWindow)** que sirva como punto de entrada a la aplicación. Esta ventana debe:

- Permitir seleccionar el directorio de trabajo
- Mostrar el progreso del análisis inicial
- Presentar las 6 herramientas de forma clara e intuitiva
- Invocar los diálogos correspondientes al hacer clic en cada herramienta

**Prioridades absolutas:**

- **Usabilidad máxima** - Diseño claro para usuarios no expertos
- **Profesionalidad** - Interfaz pulida y bien diseñada
- **Simplicidad** - Evitar confusión, un punto de acción por herramienta
- **Diseño limpio** - Sin saturación visual, jerarquía clara

***

## DESIGN SYSTEM OBLIGATORIO

Debes usar EXCLUSIVAMENTE los tokens CSS del design system proporcionado. NO inventes colores ni variables propias.

### SISTEMA DE ICONOS

**CRÍTICO:** La aplicación usa **qtawesome (MaterialDesign Icons)** para todos los iconos. **NUNCA usar emojis**.

- **Import:** `from utils.icons import icon_manager`
- **Uso en botones:** `icon_manager.set_button_icon(button, 'icon_name', color='#color', size=16)`
- **Uso en labels:** `icon_manager.set_label_icon(label, 'icon_name', color='#color', size=16)`
- **Iconos disponibles:** 'settings', 'about', 'folder', 'folder-open', 'info', 'check', 'warning', 'error', etc.
- **Razón:** Emojis no se renderizan correctamente en todas las plataformas. qtawesome garantiza consistencia visual en Windows, Linux, macOS, Android e iOS.

### Variables CSS principales a usar:

```css
/* Colores semánticos */
--color-background: /* Fondo de la ventana */
--color-surface: /* Fondo de cards */
--color-text: /* Texto principal */
--color-text-secondary: /* Texto secundario/descriptivo */
--color-primary: /* Color primario para botones/acciones */
--color-primary-hover: /* Hover de elementos primarios */
--color-secondary: /* Fondo de botones secundarios */
--color-border: /* Bordes de cards y separadores */
--color-card-border: /* Bordes específicos de cards */
--color-success: /* Indicadores de éxito (checkmarks) */
--color-warning: /* Indicadores pendientes */
--color-error: /* Errores */

/* Tipografía */
--font-family-base: /* Fuente principal */
--font-family-mono: /* Fuente monoespaciada para rutas */
--font-size-sm: 12px
--font-size-base: 14px
--font-size-md: 14px
--font-size-lg: 16px
--font-size-xl: 18px
--font-size-2xl: 20px
--font-weight-medium: 500
--font-weight-semibold: 550

/* Espaciado */
--space-8: 8px
--space-12: 12px
--space-16: 16px
--space-20: 20px
--space-24: 24px
--space-32: 32px

/* Border radius */
--radius-base: 8px
--radius-lg: 12px

/* Sombras */
--shadow-sm: /* Sombra sutil para cards */
--shadow-md: /* Sombra en hover */
```

**Sistema de cards:** Todas las cards usan:

- `background-color: var(--color-surface)`
- `border: 1px solid var(--color-card-border)`
- `border-radius: var(--radius-lg)`
- `box-shadow: var(--shadow-sm)`
- Hover: `box-shadow: var(--shadow-md)`

***

## ESTADOS DE LA VENTANA PRINCIPAL

La ventana principal tiene **3 estados principales** que debes implementar:

### ESTADO 1: INICIAL (sin directorio seleccionado)

**Prioridades de diseño:**
- **Compactación vertical:** La interfaz debe ocupar el mínimo espacio vertical posible
- **Diseño horizontal:** Aprovechar el espacio horizontal para reducir altura
- **Spacing reducido:** 12-16px entre elementos principales (no 20-24px)
- **Padding compacto:** 12-16px en cards (no 20-24px)
- **Una sola línea para header:** Todo el contenido de bienvenida en layout horizontal

### ESTADO 2: ANALIZANDO (después de seleccionar directorio)

### ESTADO 3: COMPLETADO (análisis finalizado, herramientas disponibles)


***

## MOCK ESTADO 1: INICIAL

```
╔════════════════════════════════════════════════════════════════════════════╗
║  🎨 Pixaro Lab                          [⚙️ Configuración] [ℹ️ Acerca de]  ║
║                                                          [—] [□] [✕]       ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║                                                                            ║
║  ┌──────────────────────────────────────────────────────────────────────┐ ║
║  │                                                                      │ ║
║  │                        👋 ¡Bienvenido a Pixaro Lab!                 │ ║
║  │                                                                      │ ║
║  │              Analiza y optimiza tu colección de fotos y vídeos      │ ║
║  │                                                                      │ ║
║  └──────────────────────────────────────────────────────────────────────┘ ║
║                                                                            ║
║  ┌──────────────────────────────────────────────────────────────────────┐ ║
║  │  Selecciona la carpeta con tus fotos                                │ ║
║  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │ ║
║  │                                                                      │ ║
║  │                         ┌────────────────────┐                      │ ║
║  │                         │                    │                      │ ║
║  │                         │        📁          │                      │ ║
║  │                         │                    │                      │ ║
║  │                         │  Arrastra aquí     │                      │ ║
║  │                         │  una carpeta       │                      │ ║
║  │                         │                    │                      │ ║
║  │                         │        o           │                      │ ║
║  │                         │                    │                      │ ║
║  │                         └────────────────────┘                      │ ║
║  │                                                                      │ ║
║  │                    [  Seleccionar carpeta...  ]                     │ ║
║  │                                                                      │ ║
║  │  ────────────────────────────────────────────────────────────────   │ ║
║  │                                                                      │ ║
║  │  💡 Consejo: Elige la carpeta donde tengas tus fotos del iPhone,    │ ║
║  │     de WhatsApp, o cualquier colección que quieras organizar.       │ ║
║  │                                                                      │ ║
║  │  ℹ️  Pixaro Lab analizará esa carpeta y todas sus subcarpetas.      │ ║
║  │     No se modificará nada hasta que tú lo autorices.                │ ║
║  │                                                                      │ ║
║  │  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │ ║
║  │  Última carpeta: ~/Photos/iPhone_Export        [Usar esta carpeta] │ ║
║  └──────────────────────────────────────────────────────────────────────┘ ║
║                                                                            ║
║  ┌──────────────────────────────────────────────────────────────────────┐ ║
║  │  Paso siguiente: Elige qué quieres hacer                            │ ║
║  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │ ║
║  │                                                                      │ ║
║  │  Las herramientas aparecerán aquí después de analizar tu carpeta    │ ║
║  │                                                                      │ ║
║  └──────────────────────────────────────────────────────────────────────┘ ║
║                                                                            ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```


### DESCRIPCIÓN ESTADO 1:

**Card de bienvenida compacta (una sola línea horizontal):**

- Altura: ~40px (ultra-compacta)
- Fondo: rgba(250, 250, 250, 0.8)
- Border: 1px solid color-card-border
- Padding: 12px 16px
- Layout horizontal con elementos alineados:
  - **Izquierda:** Título "¡Bienvenido a Pixaro Lab!" - font-size-lg, font-weight-medium, color-text
  - **Separador vertical:** Línea delgada (1px) entre título y subtítulo
  - **Centro:** "Analiza y optimiza tu colección de fotos y vídeos" - font-size-sm, color-text-secondary
  - **Derecha:** Iconos de configuración y acerca de
    - QToolButton con icono 'settings' (16px) - Tooltip: "Configuración"
    - QToolButton con icono 'about' (16px) - Tooltip: "Acerca de"
    - Hover: background-color secondary
    - Border-radius: radius-base
- **Iconos:** Todos los iconos usan qtawesome (MaterialDesign), NO emojis
- **Funcionalidad:** Los botones están conectados a SettingsDialog y AboutDialog

**Card principal: "Selecciona la carpeta con tus fotos":**

1. **Header:**
    - Texto: "Selecciona la carpeta con tus fotos"
    - font-size-lg, font-weight-semibold, color-text
    - Separador horizontal fino debajo (border-bottom: 1px solid color-border)
2. **Dropzone (área de arrastrar carpeta) - REDISEÑADO:**
    - Dimensiones: 300px ancho × 160px alto (más compacto)
    - Centrado horizontalmente
    - Border: 2px dashed color-border
    - Background: rgba(245, 245, 245, 0.8)
    - Border-radius: radius-lg
    - Contenido centrado vertical y horizontalmente:
        - **Icono carpeta:** usando icon_manager ('folder-open', size=64px, color=primary)
        - **Texto principal:** "Arrastra una carpeta aquí" (font-size-base, font-weight-medium, color-text)
        - **Texto secundario:** "o usa el botón de abajo" (font-size-sm, color-text-secondary)
    - Spacing interno: 24px top/bottom, 20px left/right
    - Spacing entre elementos: 12px
    - **Estado hover (al pasar mouse):**
        - Border cambia a 2px dashed color-primary
        - Background: rgba(37, 99, 235, 0.05)
        - Transición suave (0.3s)
    - **Estado drag-over (al arrastrar carpeta sobre él):**
        - Border: 2px solid color-primary
        - Background: rgba(37, 99, 235, 0.15)
        - Texto principal cambia a "Suelta para analizar"
        - Texto secundario se oculta
        - Icono mantiene color primary
    - **Nota:** NO usar emojis, solo iconos de qtawesome (MaterialDesign)
3. **Botón primario "Seleccionar carpeta...":**
    - Centrado horizontalmente
    - Margen superior: 20px desde dropzone
    - Padding: 10px 24px
    - Background: color-primary
    - Color texto: color-btn-primary-text
    - Border-radius: radius-base
    - Hover: background color-primary-hover
    - Al hacer clic: abre diálogo nativo de selección de carpetas
4. **Separador horizontal:**
    - Línea fina, margen 20px arriba y abajo
5. **Sección de consejos (compactada):**
    - **Consejo 1:**
        - Icono 'info' (icon_manager, 14px, color-text-secondary) + texto: "Elige la carpeta donde tengas tus fotos del iPhone, de WhatsApp, o cualquier colección que quieras organizar."
        - font-size-sm, color-text-secondary
        - Background: rgba(240, 240, 240, 0.5)
        - Padding: 8px 12px (más compacto)
        - Border-radius: radius-base
        - Sin margins de contenido
        - Spacing entre icono y texto: 8px
    - **Consejo 2:**
        - Icono 'check' (icon_manager, 14px, color-text-secondary) + texto: "Pixaro Lab analizará esa carpeta y todas sus subcarpetas. No se modificará nada hasta que tú lo autorices."
        - Mismo estilo que Consejo 1
        - Sin margen superior extra (seguido inmediatamente)
    - **Nota:** Todos los iconos usan icon_manager con MaterialDesign, NO emojis
6. **Separador punteado (┄┄┄):**
    - Línea punteada muy sutil
    - Margen: 16px arriba
7. **Línea de última carpeta (SOLO si existe):**
    - Layout horizontal en una línea
    - Texto izquierda: "Última carpeta: ~/Photos/iPhone_Export"
        - font-size-sm, color-text-secondary
        - Ruta truncada si es muy larga (usar ellipsis en el medio)
        - Tooltip al hover mostrando ruta completa
    - Botón derecha: "Usar esta carpeta"
        - Botón secundario PEQUEÑO
        - Padding: 6px 12px
        - font-size-sm
        - Color secundario
    - **Si la carpeta ya no existe:** NO mostrar esta línea
    - Padding: 12px vertical

**Card "Paso siguiente":**

- Header: "Paso siguiente: Elige qué quieres hacer"
- Separador horizontal
- Texto centrado: "Las herramientas aparecerán aquí después de analizar tu carpeta"
- font-size-base, color-text-secondary, italic
- Padding vertical generoso (40px)
- Overlay semitransparente (opacity 0.5) o simplemente fondo más apagado

**Drag \& Drop global:**

- Toda la ventana debe aceptar drops de carpetas cuando está en estado inicial
- Al arrastrar carpeta sobre cualquier parte de la ventana: mostrar overlay completo con mensaje "Suelta la carpeta para comenzar"
- Si sueltan un archivo (no carpeta): mostrar mensaje de error amable "Por favor selecciona una carpeta, no un archivo individual"

***

## MOCK ESTADO 2: ANALIZANDO

```
╔════════════════════════════════════════════════════════════════════════════╗
║  🎨 Pixaro Lab                          [⚙️ Configuración] [ℹ️ Acerca de]  ║
║                                                          [—] [□] [✕]       ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌──────────────────────────────────────────────────────────────────────┐ ║
║  │  📁 Directorio seleccionado                                          │ ║
║  │  /Users/usuario/Photos/iPhone_Export                                 │ ║
║  │  ────────────────────────────────────────────────────────────────────│ ║
║  │  ⏳ Analizando tu colección...                                       │ ║
║  │                                                                      │ ║
║  │  ████████████████████████████░░░░░░░░░░░░  68%                      │ ║
║  │                                                                      │ ║
║  │  📊 1,924 de 2,847 archivos analizados • 10.3 GB • ~30 segundos     │ ║
║  └──────────────────────────────────────────────────────────────────────┘ ║
║                                                                            ║
║  ┌────────────────────────────────────────────────────────────────────┐   ║
║  │  🔍 ¿Qué estamos analizando?                                       │   ║
║  │                                                                    │   ║
║  │  ✓ Detectando Live Photos...                                      │   ║
║  │  ✓ Buscando duplicados HEIC/JPG...                                │   ║
║  │  ⏳ Identificando duplicados exactos...                            │   ║
║  │  ⏸ Pendiente: Duplicados similares (puedes hacerlo después)       │   ║
║  └────────────────────────────────────────────────────────────────────┘   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```


### DESCRIPCIÓN ESTADO 2:

**Card de directorio (versión compacta durante análisis):**

1. **Header:**
    - Texto: "📁 Directorio seleccionado"
    - font-size-base, font-weight-medium
2. **Ruta del directorio:**
    - Línea siguiente al header
    - font-family-mono, font-size-sm, color-text-secondary
    - Ruta completa mostrada
3. **Separador horizontal**
4. **Estado de análisis:**
    - Icono: ⏳ (reloj de arena o spinner animado)
    - Texto: "Analizando tu colección..."
    - font-size-base, color-text
5. **Barra de progreso:**
    - Margen superior: 12px
    - Altura: 8px
    - Ancho: 100%
    - QProgressBar con estilo personalizado:
        - Relleno: color-primary
        - Background: color-secondary
        - Border-radius: radius-full (pill shape)
    - Texto del porcentaje a la derecha de la barra: "68%"
    - font-size-sm, color-text
6. **Línea de estadísticas:**
    - Margen superior: 8px
    - Texto: "📊 1,924 de 2,847 archivos analizados -  10.3 GB -  ~30 segundos"
    - font-size-sm, color-text-secondary
    - Actualización en tiempo real

**Card "¿Qué estamos analizando?" (OPCIONAL pero recomendado):**

1. **Header:**
    - Texto: "🔍 ¿Qué estamos analizando?"
    - font-size-base, font-weight-medium
2. **Lista de tareas:**
    - Cada línea con icono de estado + texto:
        - ✓ (checkmark verde, color-success) = Completado: "Detectando Live Photos..."
        - ⏳ (reloj amarillo, color-warning) = En proceso: "Identificando duplicados exactos..."
        - ⏸ (pausa gris, color-text-secondary) = Pendiente: "Duplicados similares (puedes hacerlo después)"
    - font-size-sm, color-text-secondary
    - Espaciado entre líneas: 8px
    - Padding: 16px

**Beneficio:** Muestra al usuario qué está pasando y evita impaciencia

***

## MOCK ESTADO 3: COMPLETADO

```
╔════════════════════════════════════════════════════════════════════════════╗
║  🎨 Pixaro Lab                          [⚙️ Configuración] [ℹ️ Acerca de]  ║
║                                                          [—] [□] [✕]       ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌──────────────────────────────────────────────────────────────────────┐ ║
║  │  📁 Carpeta analizada                                                │ ║
║  │  /Users/usuario/Photos/iPhone_Export                    [Cambiar...] │ ║
║  │  ────────────────────────────────────────────────────────────────────│ ║
║  │  ✅ Análisis completado • 2,847 archivos • 15.2 GB                   │ ║
║  │  💾 Espacio optimizable: ~5.8 GB (38%)               [🔄 Reanalizar] │ ║
║  └──────────────────────────────────────────────────────────────────────┘ ║
║                                                                            ║
║  ┌─────────────────────────────────────┐  ┌───────────────────────────┐  ║
║  │ 🎬 Live Photos                      │  │ 🖼️  HEIC/JPG Duplicados   │  ║
║  │                                     │  │                           │  ║
║  │ Gestiona los vídeos asociados a    │  │ Elimina fotos duplicadas  │  ║
║  │ tus Live Photos. Puedes conservar  │  │ que están en dos formatos │  ║
║  │ solo la foto, solo el vídeo, o     │  │ (HEIC y JPG). Decide qué  │  ║
║  │ ambos según tus preferencias.      │  │ formato conservar.        │  ║
║  │                                     │  │                           │  ║
║  │ ✓ 234 Live Photos detectadas       │  │ ✓ 89 pares encontrados    │  ║
║  │ 💾 ~1.8 GB recuperables             │  │ 💾 ~0.8 GB recuperables   │  ║
║  │                                     │  │                           │  ║
║  │         [Gestionar ahora]           │  │         [Gestionar ahora] │  ║
║  └─────────────────────────────────────┘  └───────────────────────────┘  ║
║                                                                            ║
║  ┌─────────────────────────────────────┐  ┌───────────────────────────┐  ║
║  │ ⚡ Duplicados Exactos               │  │ 🔍 Duplicados Similares   │  ║
║  │                                     │  │                           │  ║
║  │ Encuentra archivos que son          │  │ Detecta fotos que son     │  ║
║  │ idénticos byte a byte (copias       │  │ visualmente similares pero│  ║
║  │ exactas). Revisa los grupos y       │  │ no idénticas (recortes,   │  ║
║  │ decide cuáles eliminar.             │  │ rotaciones, ediciones).   │  ║
║  │                                     │  │                           │  ║
║  │ ✓ 42 grupos detectados              │  │ ⏸ Pendiente de análisis   │  ║
║  │ 💾 ~3.2 GB recuperables             │  │                           │  ║
║  │                                     │  │ Este análisis puede tardar│  ║
║  │         [Gestionar ahora]           │  │ unos minutos.             │  ║
║  │                                     │  │                           │  ║
║  │                                     │  │         [Analizar ahora]  │  ║
║  └─────────────────────────────────────┘  └───────────────────────────┘  ║
║                                                                            ║
║  ┌─────────────────────────────────────┐  ┌───────────────────────────┐  ║
║  │ 📂 Organizar Archivos               │  │ ✏️  Renombrar Archivos    │  ║
║  │                                     │  │                           │  ║
║  │ Reorganiza tu colección en          │  │ Renombra archivos según   │  ║
║  │ carpetas por fecha, origen          │  │ patrones personalizados   │  ║
║  │ (WhatsApp, Telegram...) o tipo.     │  │ con fechas, secuencias o  │  ║
║  │ Previsualiza antes de mover.        │  │ metadatos. Vista previa   │  ║
║  │                                     │  │ antes de aplicar cambios. │  ║
║  │ ✓ 2,847 archivos listos             │  │ ✓ 2,847 archivos listos   │  ║
║  │                                     │  │                           │  ║
║  │         [Planificar ahora]          │  │         [Configurar ahora]│  ║
║  └─────────────────────────────────────┘  └───────────────────────────┘  ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```


### DESCRIPCIÓN ESTADO 3:

**Card de directorio (versión final compacta):**

1. **Header con ruta y botón cambiar:**
    - Texto izquierda: "📁 Carpeta analizada"
    - Ruta en línea siguiente: font-family-mono, font-size-sm, color-text-secondary
    - Botón derecha (alineado al header): "Cambiar..."
        - Botón secundario pequeño
        - Padding: 6px 12px
        - Al hacer clic: muestra diálogo de confirmación si hay análisis: "¿Cambiar de carpeta? Se perderá el análisis actual." [Cancelar] [Sí, cambiar]
2. **Separador horizontal**
3. **Línea de resumen:**
    - Icono: ✅ (checkmark verde grande)
    - Texto: "Análisis completado -  2,847 archivos -  15.2 GB"
    - font-size-base, color-success para checkmark, color-text para resto
4. **Línea de espacio optimizable:**
    - Icono: 💾
    - Texto izquierda: "Espacio optimizable: ~5.8 GB (38%)"
    - font-size-base, color-text
    - Botón derecha: "🔄 Reanalizar"
        - Botón secundario pequeño
        - Al hacer clic: re-ejecuta análisis completo

**Grid de herramientas (6 cards en layout 2 columnas):**

**Layout:**

- CSS Grid o QGridLayout con 2 columnas
- Gap entre cards: 16px horizontal, 20px vertical
- En pantallas pequeñas (<768px): 1 columna
- Orden de las cards:

1. Live Photos (fila 1, col 1)
2. HEIC/JPG Duplicados (fila 1, col 2)
3. Duplicados Exactos (fila 2, col 1)
4. Duplicados Similares (fila 2, col 2)
5. Organizar Archivos (fila 3, col 1)
6. Renombrar Archivos (fila 3, col 2)

**Estructura de cada card de herramienta:**

```
┌─────────────────────────────────────┐
│ [ICONO] TÍTULO DE LA HERRAMIENTA    │  ← Header
│                                     │
│ [DESCRIPCIÓN QUÉ HACE]              │  ← Cuerpo (3-4 líneas)
│ [EN LENGUAJE CLARO]                 │
│ [BENEFIT PARA EL USUARIO]           │
│                                     │
│ [ESTADO/RESULTADOS]                 │  ← Footer
│ [MÉTRICA SI LA HAY]                 │
│                                     │
│         [BOTÓN DE ACCIÓN]           │  ← Call-to-action
└─────────────────────────────────────┘
```

**Detalles de cada card:**

1. **Card container:**
    - Background: color-surface
    - Border: 1px solid color-card-border
    - Border-radius: radius-lg
    - Box-shadow: shadow-sm
    - Padding: 20px todos los lados
    - Altura mínima: ~220px (para uniformidad)
    - Hover: box-shadow shadow-md, cursor pointer
    - **Toda la card es clicable** (no solo el botón)
2. **Header interno:**
    - Icono + Título en línea horizontal
    - Icono: tamaño ~24px, alineado verticalmente con texto
    - Título: font-size-lg, font-weight-semibold, color-text
    - Margen inferior: 12px
3. **Descripción (cuerpo):**
    - 3-4 líneas explicando QUÉ hace y PARA QUÉ sirve
    - Lenguaje claro y simple, evitar jerga técnica
    - font-size-base, line-height-normal, color-text-secondary
    - Margen inferior: 16px
4. **Separador visual invisible** (solo espaciado)
5. **Sección de resultados/estado:**

**Para herramientas CON datos analizados:**
    - Línea 1: Checkmark verde (✓) + cantidad
        - Ejemplo: "✓ 234 Live Photos detectadas"
        - Checkmark con color-success
        - font-size-sm, font-weight-medium, color-text
    - Línea 2: Icono disco (💾) + espacio recuperable
        - Ejemplo: "💾 ~1.8 GB recuperables"
        - font-size-sm, color-text-secondary
    - Espaciado entre líneas: 4px

**Para herramientas SIN análisis (ej: Duplicados Similares):**
    - Línea 1: Icono pausa (⏸) + "Pendiente de análisis"
        - color-warning
        - font-size-sm
    - Línea 2: Mini-explicación
        - Ejemplo: "Este análisis puede tardar unos minutos."
        - font-size-sm, color-text-secondary

**Para herramientas de organización (siempre listas):**
    - Línea única: "✓ 2,847 archivos listos"
    - font-size-sm, color-text
6. **Espaciador:** 12px
7. **Botón de acción:**
    - Centrado horizontalmente
    - Ancho fijo: ~200px (o auto con padding)
    - Padding: 8px 16px
    - Border-radius: radius-base
    - font-size-base, font-weight-medium
    - **Textos según herramienta:**
        - Live Photos, HEIC/JPG, Duplicados Exactos: "Gestionar ahora"
        - Duplicados Similares (sin analizar): "Analizar ahora"
        - Organizar: "Planificar ahora"
        - Renombrar: "Configurar ahora"
    - **Color del botón:**
        - Primario si hay datos listos
        - Secundario si requiere análisis previo
    - Hover: color-primary-hover o color-secondary-hover

**Comportamiento al hacer clic en card:**

1. Si la herramienta requiere análisis previo (ej: Duplicados Similares sin analizar):
    - Ejecutar análisis primero mostrando dialog de progreso
    - Al completar: abrir el diálogo específico
2. Si tiene datos listos:
    - Abrir directamente el diálogo correspondiente (live_photos_dialog.py, heic_dialog.py, etc.)
3. El diálogo se abre como modal sobre la ventana principal

***

## TEXTOS ESPECÍFICOS DE CADA CARD

### Card 1: Live Photos

- **Título:** "🎬 Live Photos"
- **Descripción:** "Gestiona los vídeos asociados a tus Live Photos. Puedes conservar solo la foto, solo el vídeo, o ambos según tus preferencias."
- **Estado con datos:** "✓ 234 Live Photos detectadas" + "💾 ~1.8 GB recuperables"
- **Botón:** "Gestionar ahora"


### Card 2: HEIC/JPG Duplicados

- **Título:** "🖼️ HEIC/JPG Duplicados"
- **Descripción:** "Elimina fotos duplicadas que están en dos formatos (HEIC y JPG). Decide qué formato conservar."
- **Estado con datos:** "✓ 89 pares encontrados" + "💾 ~0.8 GB recuperables"
- **Botón:** "Gestionar ahora"


### Card 3: Duplicados Exactos

- **Título:** "⚡ Duplicados Exactos"
- **Descripción:** "Encuentra archivos que son idénticos byte a byte (copias exactas). Revisa los grupos y decide cuáles eliminar."
- **Estado con datos:** "✓ 42 grupos detectados" + "💾 ~3.2 GB recuperables"
- **Botón:** "Gestionar ahora"


### Card 4: Duplicados Similares

- **Título:** "🔍 Duplicados Similares"
- **Descripción:** "Detecta fotos que son visualmente similares pero no idénticas (recortes, rotaciones, ediciones)."
- **Estado sin analizar:** "⏸ Pendiente de análisis" + "Este análisis puede tardar unos minutos."
- **Botón:** "Analizar ahora"


### Card 5: Organizar Archivos

- **Título:** "📂 Organizar Archivos"
- **Descripción:** "Reorganiza tu colección en carpetas por fecha, origen (WhatsApp, Telegram...) o tipo. Previsualiza antes de mover."
- **Estado:** "✓ 2,847 archivos listos"
- **Botón:** "Planificar ahora"


### Card 6: Renombrar Archivos

- **Título:** "✏️ Renombrar Archivos"
- **Descripción:** "Renombra archivos según patrones personalizados con fechas, secuencias o metadatos. Vista previa antes de aplicar cambios."
- **Estado:** "✓ 2,847 archivos listos"
- **Botón:** "Configurar ahora"

***

## CASOS ESPECIALES Y MENSAJES DE ERROR

### Directorio vacío o sin archivos multimedia:

Mostrar card en lugar del grid de herramientas:

```
┌──────────────────────────────────────────────────────────────────────┐
│  ⚠️  No se encontraron fotos o vídeos                                │
│                                                                      │
│  La carpeta que seleccionaste no contiene archivos de imagen        │
│  o vídeo compatibles.                                               │
│                                                                      │
│  Formatos compatibles: JPG, HEIC, PNG, MOV, MP4, etc.               │
│                                                                      │
│                      [Elegir otra carpeta]                           │
└──────────────────────────────────────────────────────────────────────┘
```

- Background: color-bg-4 (warning)
- Padding: 40px
- Botón primario centrado


### Sin permisos de lectura:

```
┌──────────────────────────────────────────────────────────────────────┐
│  🔒 No se puede acceder a esta carpeta                               │
│                                                                      │
│  Pixaro Lab necesita permisos de lectura para analizar el           │
│  contenido. Verifica los permisos del sistema.                      │
│                                                                      │
│                      [Elegir otra carpeta]                           │
└──────────────────────────────────────────────────────────────────────┘
```


### Carpeta de última sesión ya no existe:

En ESTADO 1, simplemente NO mostrar la línea de "Última carpeta" en la card de selección.

***

## DIÁLOGOS RELACIONADOS

### Diálogo de Configuración (⚙️):

Implementar QDialog con las siguientes secciones (usa QTabWidget o lista lateral):

**Tab 1: General**

- Tema: Combo box [Claro / Oscuro / Sistema]
- Idioma: Combo box (si planeas i18n)
- Directorio predeterminado para backups: Line edit + botón browse
- Comportamiento al iniciar: Combo box [Recordar último directorio / Mostrar selector / Abrir automáticamente último]

**Tab 2: Seguridad**

- Checkbox: "Crear backup antes de operaciones destructivas" (checked por defecto)
- Line edit: "Ubicación de backups" + botón browse
- Checkbox: "Confirmar antes de eliminar archivos" (checked por defecto)

**Tab 3: Análisis**

- Checkbox: "Re-analizar automáticamente al cambiar directorio" (checked)
- Checkbox: "Ejecutar análisis de similares automáticamente" (unchecked - puede ser lento)
- Slider: "Umbral de similitud para duplicados" (0-100%, default 85%)
- Spin box: "Número de hilos para procesamiento paralelo" (1-16, default auto)

**Botones:**

- [Restaurar valores por defecto] (secundario, izquierda)
- [Cancelar] [Guardar] (derecha)


### Diálogo Acerca de (ℹ️):

Implementar QDialog simple:

**Contenido:**

- Logo/icono grande de Pixaro Lab (centrado)
- Texto: "Pixaro Lab" (font-size-3xl, centrado)
- Texto: "Versión 1.0.0" (font-size-base, color-text-secondary, centrado)
- Texto: "Análisis profesional de colecciones multimedia" (font-size-base, centrado)
- Texto: "Copyright © 2025" (font-size-sm, color-text-secondary, centrado)

**Botones/enlaces:**

- Link: "Documentación" (abre navegador)
- Link: "Reportar un problema" (abre navegador o mailto)
- Link: "Ver licencias de código abierto"
- Botón primario: [Cerrar]

**Dimensiones:** ~400px ancho × ~500px alto

***

## PERSISTENCIA DE DATOS

Debes implementar guardado/carga de preferencias usando QSettings o archivo JSON.

**Datos a persistir:**

```json
{
  "last_workspace": {
    "path": "/Users/usuario/Photos/iPhone_Export",
    "last_analyzed": "2025-11-03T18:45:00",
    "file_count": 2847,
    "total_size_bytes": 16318464000,
    "analysis_cache": {
      "live_photos": 234,
      "heic_jpg_pairs": 89,
      "exact_duplicates": 42,
      "similar_duplicates": null,
      "recoverable_space_bytes": 6223544320
    }
  },
  "preferences": {
    "theme": "system",
    "language": "es",
    "backup_directory": "~/Pixaro_Backups",
    "auto_reanalyze": true,
    "create_backups": true,
    "confirm_deletions": true,
    "similarity_threshold": 85,
    "processing_threads": 4
  },
  "ui_state": {
    "show_welcome_card": false,
    "window_geometry": "...",
    "window_state": "..."
  }
}
```

**Validación al iniciar:**

1. Leer `last_workspace.path`
2. Verificar que el directorio exista (`os.path.exists()`) y sea accesible
3. Si existe y es válido: mostrar línea de "Última carpeta" en ESTADO 1
4. Si no existe o sin permisos: NO mostrar línea, actuar como primera vez

***

## TRANSICIONES ENTRE ESTADOS

### De ESTADO 1 → ESTADO 2:

**Trigger:** Click en "Seleccionar carpeta...", "Usar esta carpeta", o drop de carpeta

**Animación:**

1. Card de bienvenida se oculta (fade out)
2. Card de selección se colapsa a versión compacta de ESTADO 2
3. Aparece barra de progreso (fade in desde 0%)
4. Card "¿Qué estamos analizando?" aparece (slide down o fade in)
5. Card "Paso siguiente" permanece pero se mueve hacia abajo

**Duración:** ~300ms con easing suave (ease-in-out)

### De ESTADO 2 → ESTADO 3:

**Trigger:** Análisis completa (progreso llega a 100%)

**Animación:**

1. Barra de progreso se completa (100%)
2. Icono ⏳ cambia a ✅ con micro-animación
3. Card "¿Qué estamos analizando?" se oculta (fade out o slide up)
4. Card de directorio actualiza a versión final (texto + botones)
5. Grid de herramientas aparece (fade in + stagger: cada card con 50ms delay)
6. Card "Paso siguiente" se oculta completamente

**Duración:** ~500ms total

***

## RESPONSIVENESS

**Breakpoints:**

- **≥ 1024px:** Grid 2 columnas, espaciado completo
- **768px - 1023px:** Grid 2 columnas, padding reducido
- **< 768px:** Grid 1 columna, padding mínimo (12px)

**Ajustes por tamaño:**

- Dropzone se reduce a 250px × 180px en mobile
- Botones de header "Configuración" y "Acerca de" pueden colapsar a iconos solo
- Font-sizes pueden reducirse ligeramente en mobile (opcional)

***

## ESTRUCTURA DE ARCHIVOS SUGERIDA

```
ui/
├── main_window.py          # Ventana principal (este desarrollo)
├── dialogs/
│   ├── live_photos_dialog.py     # Ya implementado
│   ├── heic_dialog.py             # Ya implementado
│   ├── exact_duplicates_dialog.py # Ya implementado
│   ├── similar_duplicates_dialog.py # Ya implementado
│   ├── organization_dialog.py     # Ya implementado
│   ├── renaming_dialog.py         # Ya implementado
│   ├── settings_dialog.py         # Ya implementado
│   └── about_dialog.py            # Ya implementado
├── widgets/
│   ├── tool_card.py        # Widget reutilizable para cards de herramientas
│   ├── dropzone_widget.py  # Widget para área de drop
│   └── progress_card.py    # Widget para card de análisis
└── styles/
    └── main_styles.qss     # Stylesheet con design system
```


***

## NOTAS TÉCNICAS IMPORTANTES

1. **No usar browser storage APIs** - Esta es app de escritorio Qt, no web
2. **Signals \& Slots:**
    - Usa signals para comunicación entre análisis y UI
    - Ejemplo: `analysis_progress_updated.emit(percentage, current_file, total_files)`
    - Actualiza UI desde main thread
3. **Threading:**
    - El análisis DEBE ejecutarse en thread separado (QThread)
    - Nunca bloquees el main thread
    - Usa QTimer para polling si es necesario
4. **Iconos:**
    - Puedes usar emojis (como en mocks) o QIcon con recursos SVG
    - Si usas SVG, asegúrate que se adapten a tema claro/oscuro
5. **Drag \& Drop:**
    - Implementa `dragEnterEvent`, `dragMoveEvent`, `dropEvent`
    - Valida que sea directorio: `event.mimeData().urls()[0].toLocalFile()`
    - Rechaza si es archivo individual
6. **Diálogos modales:**
    - Usa `dialog.exec()` para bloquear ventana padre
    - Retornar resultado al cerrar (QDialog.Accepted/Rejected)
7. **Actualización post-ejecución:**
    - Al cerrar diálogos de herramientas tras ejecutar cambios
    - Re-ejecutar análisis automáticamente
    - Actualizar métricas en cards
    - Mostrar toast notification discreta confirmando operación

***

## CRITERIOS DE ÉXITO

La implementación será exitosa si:

✅ Usuario nuevo puede seleccionar carpeta sin confusión
✅ Usuario recurrente puede continuar con última carpeta en 1 clic
✅ Progreso de análisis es visible y comprensible
✅ Las 6 herramientas son obvias en su función (sin necesidad de manual)
✅ Un clic en cualquier card abre la herramienta correspondiente
✅ Diseño es limpio, profesional y no saturado
✅ Responsive en diferentes tamaños de ventana
✅ Transiciones suaves entre estados
✅ Mensajes de error son claros y accionables
✅ Design system se respeta 100%

***

## PRIORIDADES DE IMPLEMENTACIÓN

**Fase 1 (Core):**

1. Estructura básica de MainWindow
2. ESTADO 1 con selección de carpeta
3. Drag \& Drop funcional
4. Transición a ESTADO 2

**Fase 2 (Análisis):**
5. ESTADO 2 con progreso real
6. Threading para análisis
7. Transición a ESTADO 3

**Fase 3 (Herramientas):**
8. Grid de cards en ESTADO 3
9. Apertura de diálogos al hacer clic
10. Integración con servicios existentes

**Fase 4 (Polish):**
11. Persistencia de datos
12. Línea de última carpeta
13. Diálogos Configuración y Acerca de
14. Animaciones y transiciones suaves

***

## IMPLEMENTACIÓN ACTUAL (Estado real del código)

### ✅ COMPLETADO - ESTADO 1

**Archivo:** `ui/main_window.py`

**Características implementadas:**

1. **Card de bienvenida ultra-compacta (una línea):**
   - Layout horizontal: título | separador | subtítulo | iconos
   - Altura: ~40px (reducida de ~80px original)
   - Iconos integrados: settings (16px) y about (16px) con tooltips
   - Conectados a SettingsDialog y AboutDialog
   - Padding: 12px 16px

2. **Dropzone rediseñado:**
   - Dimensiones: 300×160px (reducido de 300×200px)
   - Icono folder-open (64px, color primary) usando icon_manager
   - Texto principal: "Arrastra una carpeta aquí"
   - Texto secundario: "o usa el botón de abajo"
   - Estados hover y drag-over implementados
   - Sin emojis, solo iconos qtawesome

3. **Sección de consejos compactada:**
   - Iconos 'info' y 'check' (14px) usando icon_manager
   - Padding reducido: 8px 12px
   - Sin spacing extra entre tips
   - Background: rgba(240, 240, 240, 0.5)

4. **Card "Paso siguiente" compactada:**
   - Padding: 20px (reducido de 24px)
   - Spacing: 12px (reducido de 20px)
   - Texto padding: 24px (reducido de 40px)

5. **Spacing general:**
   - Main layout spacing: 16px (reducido de 20px)
   - Main layout margins: 20px (reducido de 24px)

**Resultado:** Interfaz ocupa aproximadamente **50% menos espacio vertical** que la versión original.

### 🔄 PENDIENTE - ESTADOS 2 y 3

- ESTADO 2: Análisis con progreso
- ESTADO 3: Grid de herramientas

### 📝 ARCHIVOS RELACIONADOS

- `ui/main_window.py` - Ventana principal (Estado 1 completo)
- `ui/widgets/dropzone_widget.py` - Widget de drag & drop (rediseñado)
- `ui/styles/design_system.py` - Tokens de diseño
- `ui/dialogs/settings_dialog.py` - Diálogo de configuración
- `ui/dialogs/about_dialog.py` - Diálogo acerca de
- `utils/icons.py` - Sistema de iconos qtawesome
15. Casos de error

***

¡Implementa esta ventana principal siguiendo estas especificaciones al detalle!

