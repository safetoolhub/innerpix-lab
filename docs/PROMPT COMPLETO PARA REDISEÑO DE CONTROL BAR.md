<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# PROMPT COMPLETO PARA REDISEÑO DE CONTROL BAR - FLUJO DE ESTADOS Y SPLIT BUTTON


***

## CONTEXTO

**Archivo**: `top_bar.py` - Aplicación Python/Qt6 de normalización de archivos multimedia.

**Problema actual**:

- El botón "Seleccionar" actualmente selecciona el directorio Y lanza automáticamente el análisis, eliminando el estado natural `READY` (directorio seleccionado sin analizar)
- Los botones cambian de texto y visibilidad según el estado (Seleccionar→Cambiar, aparece Re-analizar), creando inconsistencia visual
- No hay forma de elegir entre análisis rápido vs profundo (con duplicados similares)
- Lógica de estados compleja con 3 botones que alternan visibilidad

**Objetivo del rediseño**:

1. Separar la acción de "seleccionar directorio" de "analizar"
2. Implementar los 4 estados naturales: EMPTY → READY → ANALYZING → ANALYZED
3. Añadir opción de análisis profundo (con duplicados similares)
4. Simplificar la interfaz con botones más predecibles
5. Integrar botón About en el logo (liberar espacio)

***

## PARTE 1: NUEVO FLUJO DE ESTADOS

### **1.1. Estados de la aplicación (4 estados completos)**

```
┌─────────┐
│  EMPTY  │  Sin directorio seleccionado
└────┬────┘
     │ [Usuario selecciona directorio]
     ↓
┌─────────┐
│  READY  │  Directorio seleccionado, listo para analizar (NUEVO)
└────┬────┘
     │ [Usuario lanza análisis rápido o profundo]
     ↓
┌────────────┐
│ ANALYZING  │  Análisis en progreso
└─────┬──────┘
      │ [Análisis completa]
      ↓
┌──────────┐
│ ANALYZED │  Análisis completado, resultados disponibles
└──────────┘
```

**Diferencia clave con el sistema actual**: El estado `READY` ahora existe como estado independiente, permitiendo al usuario decidir si analizar y qué tipo de análisis ejecutar.

***

### **1.2. Comportamiento de los botones por estado**

| Estado | Selector 📁 | Split Button "Analizar▼" | Botón "Detener" | Smart Stats |
| :-- | :-- | :-- | :-- | :-- |
| **EMPTY** | ✅ Enabled | 🔒 Disabled (gris) | ❌ Hidden | ❌ Hidden |
| **READY** | ✅ Enabled | ✅ Enabled "Analizar▼" | ❌ Hidden | ❌ Hidden |
| **ANALYZING** | 🔒 Disabled | ❌ Hidden | ✅ Enabled ⚠️ | ✅ Visible (progress) |
| **ANALYZED** | ✅ Enabled | ✅ Enabled "Re-analizar▼" | ❌ Hidden | ✅ Visible (results) |

**Nota crítica**: Los botones ya NO alternan entre "Seleccionar/Cambiar" o aparecen/desaparecen múltiples botones. Solo hay 3 botones máximo visibles simultáneamente, con estados enabled/disabled.

***

## PARTE 2: MODIFICACIONES AL CONTROL BAR

### **2.1. Layout del Control Bar (nuevo diseño)**

```
┌─────────────────────────────────────────────────────────────────────┐
│ [📱*] App │  [📁 /path [1.2k│45GB] [▼]]  │  [📁] [Analizar ▼] [⚙️]  │
└─────────────────────────────────────────────────────────────────────┘
   ↑                                           ↑        ↑
   Logo clickeable                          Selector  Split button
   (abre About)                              (solo icono)
```

**Elementos de izquierda a derecha**:

1. Logo clickeable (integra About)
2. Espaciador (12px)
3. Campo de directorio con metadata badge
4. Espaciador (12px)
5. **Botón selector (solo icono, sin texto)** ← CAMBIO
6. **Split button "Analizar" con dropdown** ← NUEVO
7. **Botón "Detener"** (visible solo en ANALYZING)
8. Espaciador (6px)
9. Botón toggle stats (▼/▲)
10. Botón configuración (⚙️)
11. ~~Botón About (eliminado)~~ ← REMOVIDO

***

### **2.2. CAMBIO 1: Logo clickeable (integra About)**

**Objetivo**: Eliminar el botón About independiente e integrarlo en el logo de la aplicación.

#### **Especificaciones**:

**Widget**: Convertir el container del logo (icono + texto "App Name") en un área clickeable.

**Implementación técnica**:

```python
# Container del logo (ya existe, solo modificar)
logo_container = QWidget()
logo_layout = QHBoxLayout(logo_container)
logo_layout.setSpacing(8)
logo_layout.setContentsMargins(4, 4, 4, 4)

# Icono + texto (sin cambios)
logo_icon = QLabel()
# ... código del icono actual
logo_text = QLabel(Config.APP_NAME)
# ... código del texto actual

logo_layout.addWidget(logo_icon)
logo_layout.addWidget(logo_text)

# NUEVO: Hacer clickeable
logo_container.setCursor(Qt.CursorShape.PointingHandCursor)
logo_container.setToolTip("Acerca de")

# Evento click
def on_logo_clicked(event):
    if self.mainwindow is not None:
        self.mainwindow.show_about()
    event.accept()

logo_container.mousePressEvent = on_logo_clicked
```

**Estilo CSS** (hover sutil):

```python
logo_container.setStyleSheet("""
    QWidget {
        background: transparent;
        border-radius: 6px;
        padding: 4px 8px;
    }
    QWidget:hover {
        background: rgba(var(--color-brown-600-rgb), 0.06);
    }
    
    /* Dark mode */
    [data-color-scheme="dark"] QWidget:hover {
        background: rgba(var(--color-gray-400-rgb), 0.10);
    }
""")
```

**Área clickeable**: Todo el container (icono + texto), aproximadamente 120×36px.

**Tooltip**: "Acerca de" (pequeño, discreto, visible en hover).

**Resultado**: Eliminar completamente el `aboutbtn` del código (ya no es necesario).

***

### **2.3. CAMBIO 2: Botón selector (solo icono, sin texto)**

**Objetivo**: Simplificar el botón de selección de directorio para que sea más compacto y consistente visualmente.

#### **Especificaciones**:

**Antes**:

```python
selectbtn = QPushButton("Seleccionar")  # o "Cambiar"
# Texto cambiaba según estado
```

**Después**:

```python
selectbtn = QPushButton()  # Sin texto
iconmanager.setbuttonicon(selectbtn, 'folder', color='#2563eb', size=18)
selectbtn.setFixedSize(36, 32)  # Compacto, cuadrado
selectbtn.setCursor(Qt.CursorShape.PointingHandCursor)
```

**Tooltip dinámico** (según estado):

```python
def update_selector_tooltip(self, state):
    if state == 'empty' or state == 'ready':
        self.selectbtn.setToolTip("Seleccionar directorio")
    elif state == 'analyzed':
        self.selectbtn.setToolTip("Cambiar directorio")
    elif state == 'analyzing':
        self.selectbtn.setToolTip("No puedes cambiar durante el análisis")
        self.selectbtn.setEnabled(False)
```

**Estilo CSS**:

```python
selectbtn.setStyleSheet("""
    QPushButton {
        background: transparent;
        border: 1px solid var(--color-border);
        border-radius: 6px;
    }
    QPushButton:hover:enabled {
        background: rgba(var(--color-primary-rgb), 0.08);
        border-color: var(--color-primary);
    }
    QPushButton:pressed:enabled {
        background: rgba(var(--color-primary-rgb), 0.15);
    }
    QPushButton:disabled {
        opacity: 0.5;
    }
""")
```

**Click event**:

```python
selectbtn.clicked.connect(self.on_select_directory)  # Solo selecciona, NO analiza
```

**Cambio crítico en `on_select_directory()`**:

```python
def on_select_directory(self):
    """Selecciona directorio SIN lanzar análisis automático."""
    directory = QFileDialog.getExistingDirectory(
        self,
        "Seleccionar directorio",
        str(Path.home()),
        QFileDialog.Option.ShowDirsOnly
    )
    
    if directory:
        self.directory_selected.emit(directory)  # Emite señal
        self.set_state('ready')  # NUEVO: Cambiar a estado READY
        # NO llamar a analyze_requested.emit() aquí
```


***

### **2.4. CAMBIO 3: Split Button "Analizar" con dropdown**

**Objetivo**: Crear un botón combinado que permita análisis rápido por defecto (clic directo) y opciones avanzadas en el dropdown (análisis profundo, re-analizar).

#### **Estructura del Split Button**:

```
┌────────────────────────┐
│ Analizar      │   ▼    │  ← Un solo widget compuesto
└────────────────────────┘
   ↑ Botón principal  ↑ Dropdown
   (acción por defecto) (menú opciones)
```


#### **Implementación técnica**:

**Crear container del split button**:

```python
# Widget contenedor del split button
split_container = QWidget()
split_container.setFixedHeight(32)
split_layout = QHBoxLayout(split_container)
split_layout.setSpacing(0)
split_layout.setContentsMargins(0, 0, 0, 0)

# ═══════════════════════════════════════════════════════════
# PARTE 1: Botón principal "Analizar"
# ═══════════════════════════════════════════════════════════
self.analyze_btn = QPushButton("Analizar")
self.analyze_btn.setFixedHeight(32)
self.analyze_btn.setMinimumWidth(90)
self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)

# Acción por defecto: Análisis rápido
self.analyze_btn.clicked.connect(self.on_analyze_quick)

# ═══════════════════════════════════════════════════════════
# SEPARADOR VISUAL (línea vertical)
# ═══════════════════════════════════════════════════════════
separator = QFrame()
separator.setFrameShape(QFrame.Shape.VLine)
separator.setFixedSize(1, 20)
separator.setStyleSheet("""
    QFrame {
        background: rgba(255, 255, 255, 0.3);
        border: none;
    }
""")

# ═══════════════════════════════════════════════════════════
# PARTE 2: Botón dropdown (chevron)
# ═══════════════════════════════════════════════════════════
self.dropdown_btn = QPushButton("▼")
self.dropdown_btn.setFixedSize(24, 32)
self.dropdown_btn.setCursor(Qt.CursorShape.PointingHandCursor)

# Crear menú de opciones
self.analyze_menu = QMenu(self.dropdown_btn)

# Opciones del menú
self.action_quick = self.analyze_menu.addAction("⚡ Análisis rápido")
self.action_quick.triggered.connect(self.on_analyze_quick)

self.action_deep = self.analyze_menu.addAction("🔍 Análisis profundo")
self.action_deep.triggered.connect(self.on_analyze_deep)

self.analyze_menu.addSeparator()

self.action_reanalyze = self.analyze_menu.addAction("🔄 Re-analizar")
self.action_reanalyze.triggered.connect(self.on_reanalyze)
self.action_reanalyze.setEnabled(False)  # Disabled por defecto

# Asociar menú al botón dropdown
self.dropdown_btn.setMenu(self.analyze_menu)

# ═══════════════════════════════════════════════════════════
# Añadir todo al layout del split button
# ═══════════════════════════════════════════════════════════
split_layout.addWidget(self.analyze_btn)
split_layout.addWidget(separator)
split_layout.addWidget(self.dropdown_btn)
```


#### **Estilo CSS del Split Button**:

```python
split_container.setStyleSheet("""
    /* Container exterior (fondo del split button) */
    QWidget {
        background: var(--color-primary);
        border-radius: 6px;
    }
    QWidget:hover {
        background: var(--color-primary-hover);
    }
    
    /* Botones internos (principal + dropdown) */
    QPushButton {
        background: transparent;
        color: var(--color-btn-primary-text);
        border: none;
        font-size: var(--font-size-sm);
        font-weight: var(--font-weight-medium);
        padding: 0 12px;
    }
    
    /* Hover individual de botones */
    QPushButton:hover {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 4px;
    }
    
    /* Estado disabled */
    QWidget:disabled {
        background: var(--color-secondary);
        opacity: 0.6;
    }
    QPushButton:disabled {
        color: var(--color-text-secondary);
    }
""")
```


#### **Tooltips descriptivos**:

```python
self.analyze_btn.setToolTip(
    "Análisis rápido: Live Photos, HEIC, renombrado, "
    "organización, duplicados exactos (~1-5 min)"
)

self.action_quick.setToolTip(
    "Análisis rápido: Live Photos, HEIC, renombrado, "
    "organización, duplicados exactos (~1-5 min)"
)

self.action_deep.setToolTip(
    "Análisis profundo: Todo lo anterior + duplicados "
    "similares (~10-30 min según tamaño del directorio)"
)

self.action_reanalyze.setToolTip(
    "Re-ejecutar el último tipo de análisis realizado"
)
```


#### **Comportamiento por estado**:

**Estado EMPTY**:

```python
split_container.setEnabled(False)  # Disabled completo
self.analyze_btn.setText("Analizar")
self.action_reanalyze.setVisible(False)
```

**Estado READY**:

```python
split_container.setEnabled(True)
self.analyze_btn.setText("Analizar")
self.action_reanalyze.setVisible(False)
```

**Estado ANALYZING**:

```python
split_container.setVisible(False)  # Oculto, aparece botón "Detener"
```

**Estado ANALYZED**:

```python
split_container.setEnabled(True)
split_container.setVisible(True)
self.analyze_btn.setText("Re-analizar")
self.action_reanalyze.setVisible(True)
self.action_reanalyze.setEnabled(True)
```


#### **Métodos de acción**:

```python
def on_analyze_quick(self):
    """Lanza análisis rápido (sin duplicados similares)."""
    self.analyze_requested.emit('quick')  # Emite señal con tipo
    self.set_state('analyzing')

def on_analyze_deep(self):
    """Lanza análisis profundo (con duplicados similares)."""
    self.analyze_requested.emit('deep')  # Emite señal con tipo
    self.set_state('analyzing')

def on_reanalyze(self):
    """Re-ejecuta el último análisis realizado."""
    # Lógica: recordar el último tipo (quick/deep) y re-ejecutar
    last_analysis_type = getattr(self, '_last_analysis_type', 'quick')
    if last_analysis_type == 'quick':
        self.on_analyze_quick()
    else:
        self.on_analyze_deep()
```

**Nota**: La señal `analyze_requested` ahora debe emitir el tipo de análisis (`'quick'` o `'deep'`) para que el backend sepa qué ejecutar.

***

### **2.5. CAMBIO 4: Botón "Detener" (sin cambios mayores)**

El botón "Detener" ya existe en el código actual. Solo ajustar su posición y visibilidad.

**Especificaciones**:

- **Visible solo en estado ANALYZING**
- **Reemplaza visualmente al split button** (mismo espacio en el layout)
- **Estilo**: Fondo amarillo/naranja, icono "stop"
- **Click**: Emite señal `stop_analysis_requested`

**Código**:

```python
self.stop_btn = QPushButton("Detener")
iconmanager.setbuttonicon(self.stop_btn, 'stop', color='white', size=16)
self.stop_btn.setFixedHeight(32)
self.stop_btn.setMinimumWidth(90)
self.stop_btn.setVisible(False)  # Hidden por defecto
self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
self.stop_btn.clicked.connect(self.stop_analysis_requested.emit)

self.stop_btn.setStyleSheet("""
    QPushButton {
        background: var(--color-warning);
        color: white;
        border: none;
        border-radius: 6px;
        font-size: var(--font-size-sm);
        font-weight: var(--font-weight-medium);
        padding: 0 16px;
    }
    QPushButton:hover {
        background: rgba(var(--color-warning-rgb), 0.85);
    }
    QPushButton:pressed {
        background: rgba(var(--color-warning-rgb), 0.70);
    }
""")
```

**Visibilidad por estado**:

```python
if state == 'analyzing':
    split_container.setVisible(False)
    self.stop_btn.setVisible(True)
else:
    split_container.setVisible(True)
    self.stop_btn.setVisible(False)
```


***

### **2.6. Layout final del Control Bar**

**Código de integración en el layout principal**:

```python
# Layout horizontal del control bar
control_layout = QHBoxLayout()
control_layout.setContentsMargins(16, 8, 16, 8)
control_layout.setSpacing(12)

# 1. Logo clickeable (con About integrado)
control_layout.addWidget(logo_container)

# 2. Espaciador
control_layout.addSpacing(12)

# 3. Campo de directorio con metadata
control_layout.addWidget(field_widget, 1)  # stretch

# 4. Espaciador
control_layout.addSpacing(12)

# 5. Botón selector (solo icono)
control_layout.addWidget(self.selectbtn)

# 6. Split button "Analizar" + Botón "Detener" (ocupan mismo espacio)
control_layout.addWidget(split_container)
control_layout.addWidget(self.stop_btn)

# 7. Espaciador
control_layout.addSpacing(6)

# 8. Botón toggle stats
control_layout.addWidget(self.stats_toggle_btn)

# 9. Botón configuración
control_layout.addWidget(self.config_btn)

# 10. About button eliminado (ahora está en logo)
```


***

## PARTE 3: MODIFICACIONES AL SISTEMA DE ESTADOS

### **3.1. Método `set_state()` actualizado**

**Actualizar el método existente para soportar el nuevo estado `READY`**:

```python
def set_state(self, state: str):
    """
    Actualiza el estado visual del control bar.
    
    Estados válidos:
    - 'empty': Sin directorio seleccionado
    - 'ready': Directorio seleccionado, listo para analizar (NUEVO)
    - 'analyzing': Análisis en progreso
    - 'analyzed': Análisis completado
    """
    self.current_state = state
    
    # ═══════════════════════════════════════════════════════════
    # Estado: EMPTY
    # ═══════════════════════════════════════════════════════════
    if state == 'empty':
        # Botón selector
        self.selectbtn.setEnabled(True)
        self.selectbtn.setToolTip("Seleccionar directorio")
        
        # Split button
        self.split_container.setEnabled(False)
        self.split_container.setVisible(True)
        self.analyze_btn.setText("Analizar")
        self.action_reanalyze.setVisible(False)
        
        # Botón detener
        self.stop_btn.setVisible(False)
        
        # Campo directorio
        self.directoryedit.setText("Ningún directorio seleccionado")
        self.metadata_badge.setVisible(False)
        self.analysis_badge.setVisible(False)
        self.folder_icon.setVisible(False)
        
        # Smart stats
        self.smart_stats_bar.setVisible(False)
        self.stats_toggle_btn.setVisible(False)
    
    # ═══════════════════════════════════════════════════════════
    # Estado: READY (NUEVO)
    # ═══════════════════════════════════════════════════════════
    elif state == 'ready':
        # Botón selector
        self.selectbtn.setEnabled(True)
        self.selectbtn.setToolTip("Cambiar directorio")
        
        # Split button
        self.split_container.setEnabled(True)
        self.split_container.setVisible(True)
        self.analyze_btn.setText("Analizar")
        self.action_reanalyze.setVisible(False)
        
        # Botón detener
        self.stop_btn.setVisible(False)
        
        # Campo directorio: ya muestra el path seleccionado
        # metadata_badge y analysis_badge permanecen ocultos (aún no hay análisis)
        self.metadata_badge.setVisible(False)
        self.analysis_badge.setVisible(False)
        self.folder_icon.setVisible(True)
        
        # Smart stats
        self.smart_stats_bar.setVisible(False)
        self.stats_toggle_btn.setVisible(False)
    
    # ═══════════════════════════════════════════════════════════
    # Estado: ANALYZING
    # ═══════════════════════════════════════════════════════════
    elif state == 'analyzing':
        # Botón selector
        self.selectbtn.setEnabled(False)
        self.selectbtn.setToolTip("No puedes cambiar durante el análisis")
        
        # Split button (oculto)
        self.split_container.setVisible(False)
        
        # Botón detener (visible)
        self.stop_btn.setVisible(True)
        
        # Campo directorio: sin cambios
        # metadata_badge y analysis_badge ocultos durante análisis
        self.metadata_badge.setVisible(False)
        self.analysis_badge.setVisible(False)
        
        # Smart stats (visible con progreso)
        self.smart_stats_bar.setVisible(True)
        self.stats_toggle_btn.setVisible(True)
    
    # ═══════════════════════════════════════════════════════════
    # Estado: ANALYZED
    # ═══════════════════════════════════════════════════════════
    elif state == 'analyzed':
        # Botón selector
        self.selectbtn.setEnabled(True)
        self.selectbtn.setToolTip("Cambiar directorio")
        
        # Split button
        self.split_container.setEnabled(True)
        self.split_container.setVisible(True)
        self.analyze_btn.setText("Re-analizar")
        self.action_reanalyze.setVisible(True)
        self.action_reanalyze.setEnabled(True)
        
        # Botón detener
        self.stop_btn.setVisible(False)
        
        # Campo directorio: mostrar badges
        self.metadata_badge.setVisible(True)
        self.analysis_badge.setVisible(True)
        
        # Smart stats (visible con resultados)
        self.smart_stats_bar.setVisible(True)
        self.stats_toggle_btn.setVisible(True)
```


***

### **3.2. Señales actualizadas**

**Modificar la señal `analyze_requested` para incluir el tipo de análisis**:

```python
# Antes:
analyze_requested = pyqtSignal()

# Después:
analyze_requested = pyqtSignal(str)  # Emite 'quick' o 'deep'
```

**En el backend (main window o controlador)**:

```python
def on_analyze_requested(self, analysis_type: str):
    """
    Maneja la solicitud de análisis.
    
    Args:
        analysis_type: 'quick' o 'deep'
    """
    if analysis_type == 'quick':
        # Ejecutar análisis rápido (sin duplicados similares)
        self.run_quick_analysis()
    elif analysis_type == 'deep':
        # Ejecutar análisis profundo (con duplicados similares)
        self.run_deep_analysis()
    
    # Guardar el tipo para re-análisis
    self.last_analysis_type = analysis_type
```


***

## PARTE 4: ESTILO DEL MENÚ DROPDOWN

### **4.1. Estilo del QMenu**

**Aplicar estilo consistente con el design system**:

```python
self.analyze_menu.setStyleSheet("""
    QMenu {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: 8px;
        padding: 6px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    QMenu::item {
        padding: 8px 16px;
        border-radius: 4px;
        color: var(--color-text);
        font-size: var(--font-size-sm);
    }
    
    QMenu::item:selected {
        background: var(--color-secondary-hover);
    }
    
    QMenu::item:disabled {
        color: var(--color-text-secondary);
        opacity: 0.5;
    }
    
    QMenu::separator {
        height: 1px;
        background: var(--color-border);
        margin: 4px 0;
    }
""")
```


***

### **4.2. Iconos en las opciones del menú**

**Añadir iconos para mejor reconocimiento visual**:

```python
# Cargar iconos
icon_quick = iconmanager.get_icon('zap', color=var(--color-primary))
icon_deep = iconmanager.get_icon('search', color=var(--color-warning))
icon_reanalyze = iconmanager.get_icon('refresh', color=var(--color-text))

# Asociar iconos a acciones
self.action_quick.setIcon(icon_quick)
self.action_deep.setIcon(icon_deep)
self.action_reanalyze.setIcon(icon_reanalyze)
```


***

## PARTE 5: RESUMEN DE CAMBIOS AL CÓDIGO

### **5.1. Componentes a modificar**

#### **Eliminar**:

- ❌ `aboutbtn` (botón About independiente)
- ❌ Lógica de cambio de texto "Seleccionar" → "Cambiar"
- ❌ Botón "Re-analizar" separado (ahora en el split button)


#### **Añadir**:

- ✅ Click event en `logo_container` para mostrar About
- ✅ `split_container` (widget del split button)
- ✅ `analyze_btn` (botón principal del split)
- ✅ `dropdown_btn` (botón chevron del split)
- ✅ `analyze_menu` (menú con opciones de análisis)
- ✅ Métodos `on_analyze_quick()` y `on_analyze_deep()`
- ✅ Estado `'ready'` en el sistema de estados


#### **Modificar**:

- 🔄 `selectbtn`: Quitar texto, dejar solo icono
- 🔄 `set_state()`: Añadir lógica para estado `'ready'`
- 🔄 `on_select_directory()`: NO lanzar análisis automático
- 🔄 Señal `analyze_requested`: Añadir parámetro `str` (tipo de análisis)

***

### **5.2. Variables de instancia nuevas**

```python
# En __init__() de TopBar o ControlBar:
self.current_state = 'empty'
self.split_container = None  # Container del split button
self.analyze_btn = None      # Botón principal "Analizar"
self.dropdown_btn = None     # Botón chevron dropdown
self.analyze_menu = None     # Menú de opciones
self.action_quick = None     # Acción análisis rápido
self.action_deep = None      # Acción análisis profundo
self.action_reanalyze = None # Acción re-analizar
self._last_analysis_type = 'quick'  # Recordar último tipo
```


***

## PARTE 6: FLUJO COMPLETO DEL USUARIO (NUEVO)

### **Escenario: Usuario nuevo inicia análisis profundo**

```
1. App abierta → Estado EMPTY
   ┌────────────────────────────────────────────────┐
   │ [📱*] │ [Ningún dir] │ [📁] [Analizar▼ 🔒] [⚙️]│
   └────────────────────────────────────────────────┘
   
   Usuario: Click en [📁] (selector)

2. Dialog de selección → Selecciona /Photos/Vacaciones
   → Estado READY (NUEVO)
   ┌───────────────────────────────────────────────────┐
   │ [📱*] │ [/Photos/Vac...] │ [📁] [Analizar▼] [⚙️] │
   └───────────────────────────────────────────────────┘
   
   Usuario: Click en dropdown ▼

3. Menú desplegable aparece:
   ┌──────────────────────┐
   │ ⚡ Análisis rápido   │
   │ 🔍 Análisis profundo │
   └──────────────────────┘
   
   Usuario: Click en "🔍 Análisis profundo"

4. Análisis profundo comienza → Estado ANALYZING
   ┌──────────────────────────────────────────────────┐
   │ [📱*] │ [/Photos...] │ [📁🔒] [Detener⚠️] [⚙️] │
   └──────────────────────────────────────────────────┘
   Smart Stats aparece con barra de progreso

5. Análisis completa → Estado ANALYZED
   ┌─────────────────────────────────────────────────────────┐
   │ [📱*] │ [/Photos [1.2k│45GB]] │ [📁] [Re-analizar▼] [⚙️]│
   └─────────────────────────────────────────────────────────┘
   Smart Stats muestra resultados (amarillo/verde)
   
   Usuario: Puede hacer click en dropdown para re-analizar:
   ┌──────────────────────────┐
   │ ⚡ Análisis rápido       │
   │ 🔍 Análisis profundo     │
   │ ─────────────────────    │
   │ 🔄 Re-analizar (profundo)│ ← Recuerda el último tipo
   └──────────────────────────┘
```


***

## PARTE 7: TESTING Y VALIDACIÓN

### **7.1. Casos de prueba**

**Test 1: Flujo completo EMPTY → READY → ANALYZING → ANALYZED**

- [ ] Estado EMPTY: Split button disabled, selector enabled
- [ ] Seleccionar directorio: Cambio a READY sin análisis automático
- [ ] Estado READY: Split button enabled, path visible, badges ocultos
- [ ] Click "Analizar" (principal): Lanza análisis rápido
- [ ] Estado ANALYZING: Selector disabled, botón Detener visible
- [ ] Análisis completa: Estado ANALYZED, badges visibles

**Test 2: Análisis profundo desde READY**

- [ ] Estado READY: Click en dropdown ▼
- [ ] Menú muestra "⚡ Rápido" y "🔍 Profundo"
- [ ] Click en "🔍 Profundo": Emite señal con tipo 'deep'
- [ ] Backend ejecuta análisis con duplicados similares

**Test 3: Re-analizar desde ANALYZED**

- [ ] Estado ANALYZED: Texto del botón principal es "Re-analizar"
- [ ] Click en dropdown ▼: Menú muestra opción "🔄 Re-analizar"
- [ ] Click en "Re-analizar": Ejecuta último tipo de análisis

**Test 4: Logo clickeable (About)**

- [ ] Hover sobre logo: Cursor cambia a pointer, fondo sutil
- [ ] Click en logo: Dialog About aparece
- [ ] Botón About independiente ya no existe

**Test 5: Cambiar directorio desde ANALYZED**

- [ ] Click en selector [📁]: Dialog de selección aparece
- [ ] Seleccionar nuevo directorio: Estado cambia a READY
- [ ] Smart stats se ocultan, badges se ocultan
- [ ] Split button vuelve a "Analizar" (no "Re-analizar")

***

### **7.2. Validación visual**

- [ ] Split button tiene separador vertical visible
- [ ] Hover en botón principal y dropdown funciona independientemente
- [ ] Menú dropdown tiene iconos y tooltips
- [ ] Logo tiene hover effect sutil
- [ ] Selector (solo icono) tiene tamaño correcto (36×32px)
- [ ] Espaciado entre elementos es consistente (12px, 6px)

***

## PARTE 8: RESULTADO ESPERADO

### **Antes del rediseño**:

```
┌────────────────────────────────────────────────────────────┐
│ [📱] App │ /path │ [Seleccionar/Cambiar] [Re-analizar] [⚙️ℹ️]│
└────────────────────────────────────────────────────────────┘
```

**Problemas**:

- Botones cambian texto (confuso)
- Re-analizar aparece/desaparece (inconsistente)
- No hay estado READY (seleccionar = analizar automático)
- No hay opción de análisis profundo

***

### **Después del rediseño**:

```
┌───────────────────────────────────────────────────────────┐
│ [📱*] App │ /path [1.2k│45GB] │ [📁] [Analizar▼] [⚙️]    │
└───────────────────────────────────────────────────────────┘
```

**Mejoras**:
✅ Logo clickeable (About integrado, -32px espacio)
✅ Selector compacto (solo icono, -50px espacio)
✅ Split button (análisis rápido/profundo en un solo control)
✅ Botones predecibles (no cambian de texto/posición)
✅ Estado READY existe (seleccionar ≠ analizar)
✅ Flujo natural de 4 estados completo
✅ ~112px de espacio horizontal liberado

***

## ENTREGABLE FINAL

**Código Python/Qt6 modificado** que implemente:

1. ✅ Logo clickeable con evento `mousePressEvent` para mostrar About
2. ✅ Eliminación del botón About independiente
3. ✅ Botón selector solo con icono (sin texto)
4. ✅ Split button "Analizar" con dropdown (rápido/profundo/re-analizar)
5. ✅ Separador visual en el split button
6. ✅ Menú dropdown con iconos y tooltips descriptivos
7. ✅ Estado `READY` añadido al sistema de estados
8. ✅ Método `set_state()` actualizado para 4 estados
9. ✅ Método `on_select_directory()` sin análisis automático
10. ✅ Señal `analyze_requested` con parámetro de tipo (`str`)
11. ✅ Métodos `on_analyze_quick()` y `on_analyze_deep()`
12. ✅ Tooltips dinámicos según estado
13. ✅ Estilo CSS del split button y menú
14. ✅ Lógica de visibilidad de botones por estado
15. ✅ Variable `_last_analysis_type` para recordar tipo de análisis

***

**FIN DEL PROMPT** 🚀

