# **PROMPT COMPLETO: Refactorización Integral Material Design - Pixaro Lab Dialogs**

```
Refactoriza COMPLETAMENTE los siguientes archivos para usar Material Design consistente basado en `organization_dialog.py` como referencia única:

**Archivos a refactorizar:**
1. `ui/dialogs/exact_copies_dialog.py`
2. `ui/dialogs/heic_dialog.py`
3. `ui/dialogs/renaming_dialog.py`
4. `ui/dialogs/live_photos_dialog.py`

**Archivo de referencia (NO modificar):**
- `ui/dialogs/organization_dialog.py` - ESTE ES EL MODELO A SEGUIR

---

## REGLAS OBLIGATORIAS (PEP 8 y Pixaro Lab)

### 1. Prohibiciones absolutas:
- ❌ NO usar emojis (💾, 🖼️, 📸, ⚠️, etc.) - usar `icon_manager` exclusivamente
- ❌ NO usar colores hardcoded (`#ffffff`, `rgb()`, etc.) - solo `DesignSystem.COLOR_*`
- ❌ NO usar tamaños hardcoded - solo `DesignSystem.SPACE_*`, `FONT_SIZE_*`
- ❌ NO usar CSS inline sin `DesignSystem`
- ❌ NO modificar lógica de negocio ni signals existentes
- ❌ NO romper funcionalidad de backup checkbox (viene de `BaseDialog`)

### 2. Obligaciones absolutas:
- ✅ Type hints en TODOS los métodos nuevos y existentes
- ✅ Docstrings en formato Google para métodos públicos
- ✅ Mantener imports existentes y añadir solo si es necesario
- ✅ Aplicar `DesignSystem.get_tooltip_style()` en todos los diálogos
- ✅ Preservar nombres de métodos públicos (sin guion bajo) para compatibilidad
- ✅ Usar nombres con guion bajo (`_create_*`) solo para métodos nuevos privados

---

## PASO 1: Crear métodos comunes en `base_dialog.py`

Añade estos métodos helper al final de la clase `BaseDialog` (antes del método `accept()`):

```

def _create_explanation_frame(
self,
icon_name: str,
title: str,
description: str
) -> QFrame:
"""Crea frame de explicación estandarizado con icono, título y descripción.

    Args:
        icon_name: Nombre del icono de icon_manager (ej: 'content-copy')
        title: Título principal (negrita)
        description: Texto descriptivo
    
    Returns:
        QFrame con el header explicativo
    """
    from ui.styles.design_system import DesignSystem
    from utils.icons import icon_manager
    
    frame = QFrame()
    frame.setStyleSheet(f"""
        QFrame {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {DesignSystem.COLOR_BG_1},
                stop:1 {DesignSystem.COLOR_BG_2});
            border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
            border-radius: {DesignSystem.RADIUS_LG}px;
            padding: {DesignSystem.SPACE_16}px;
        }}
    """)
    
    layout = QHBoxLayout(frame)
    layout.setSpacing(int(DesignSystem.SPACE_12))
    layout.setContentsMargins(
        int(DesignSystem.SPACE_12),
        int(DesignSystem.SPACE_8),
        int(DesignSystem.SPACE_12),
        int(DesignSystem.SPACE_8)
    )
    
    # Icono
    icon_label = QLabel()
    icon_manager.set_label_icon(
        icon_label, 
        icon_name, 
        size=DesignSystem.ICON_SIZE_LG,
        color=DesignSystem.COLOR_PRIMARY
    )
    layout.addWidget(icon_label)
    
    # Contenedor de texto
    text_container = QVBoxLayout()
    text_container.setSpacing(int(DesignSystem.SPACE_4))
    
    # Título
    title_label = QLabel(title)
    title_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_LG}px;
        font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        color: {DesignSystem.COLOR_TEXT};
    """)
    text_container.addWidget(title_label)
    
    # Descripción
    desc_label = QLabel(description)
    desc_label.setWordWrap(True)
    desc_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_SM}px;
        color: {DesignSystem.COLOR_TEXT_SECONDARY};
        line-height: 1.5;
    """)
    text_container.addWidget(desc_label)
    
    layout.addLayout(text_container, 1)
    
    return frame
    def _create_metric_card(
self,
value: str,
label: str,
color: str = None
) -> QFrame:
"""Crea tarjeta de métrica inline estandarizada.

    Args:
        value: Valor a mostrar (número, texto)
        label: Etiqueta descriptiva
        color: Color del borde izquierdo (opcional, por defecto PRIMARY)
    
    Returns:
        QFrame con la métrica formateada
    """
    from ui.styles.design_system import DesignSystem
    
    if color is None:
        color = DesignSystem.COLOR_PRIMARY
    
    frame = QFrame()
    frame.setStyleSheet(f"""
        QFrame {{
            background-color: {DesignSystem.COLOR_BG_1};
            border-left: 3px solid {color};
            border-radius: {DesignSystem.RADIUS_BASE}px;
            padding: {DesignSystem.SPACE_8}px;
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
    
    # Valor
    value_label = QLabel(str(value))
    value_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_2XL}px;
        font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        color: {DesignSystem.COLOR_TEXT};
    """)
    
    # Label
    desc_label = QLabel(label)
    desc_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_SM}px;
        color: {DesignSystem.COLOR_TEXT_SECONDARY};
    """)
    
    layout.addWidget(value_label)
    layout.addWidget(desc_label)
    
    return frame
    def _create_selection_card(
self,
card_id: str,
icon_name: str,
title: str,
description: str,
is_selected: bool,
radio_button: QRadioButton = None
) -> QFrame:
"""Crea tarjeta de selección clickeable con RadioButton (patrón organization_dialog).

    Args:
        card_id: ID único de la card (ej: 'strategy-oldest')
        icon_name: Nombre del icono de icon_manager
        title: Título de la opción
        description: Descripción de la opción
        is_selected: Si la card está seleccionada
        radio_button: RadioButton a asociar (opcional, se crea si es None)
    
    Returns:
        QFrame con la card de selección
    """
    from ui.styles.design_system import DesignSystem
    from utils.icons import icon_manager
    
    card = QFrame()
    card.setObjectName(card_id)
    card.setStyleSheet(f"""
        QFrame#{card_id} {{
            background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_SURFACE};
            border: 2px solid {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BORDER};
            border-radius: {DesignSystem.RADIUS_BASE}px;
            padding: {DesignSystem.SPACE_12}px;
        }}
        QFrame#{card_id}:hover {{
            border-color: {DesignSystem.COLOR_PRIMARY};
            background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BG_2};
        }}
        QFrame#{card_id} QLabel {{
            color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT};
        }}
        QFrame#{card_id} QLabel#title-label {{
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        }}
        QFrame#{card_id} QLabel#desc-label {{
            color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT_SECONDARY};
        }}
    """)
    
    layout = QVBoxLayout(card)
    layout.setSpacing(int(DesignSystem.SPACE_8))
    
    # Header: RadioButton + Icono + Título
    header_layout = QHBoxLayout()
    
    if radio_button is None:
        radio_button = QRadioButton()
        radio_button.setChecked(is_selected)
    
    header_layout.addWidget(radio_button)
    
    icon_label = QLabel()
    icon_manager.set_label_icon(
        icon_label, 
        icon_name, 
        size=DesignSystem.ICON_SIZE_XL,
        color=DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_PRIMARY
    )
    header_layout.addWidget(icon_label)
    
    title_label = QLabel(title)
    title_label.setObjectName("title-label")
    header_layout.addWidget(title_label)
    header_layout.addStretch()
    
    layout.addLayout(header_layout)
    
    # Descripción
    desc_label = QLabel(description)
    desc_label.setWordWrap(True)
    desc_label.setObjectName("desc-label")
    layout.addWidget(desc_label)
    
    # Hacer la card clickeable
    card.mousePressEvent = lambda event: radio_button.setChecked(True)
    
    # Guardar referencia al radio en la card
    card.setProperty("radio_button", radio_button)
    
    return card
    ```

---

## PASO 2: Refactorizar cada diálogo

### **2.1 exact_copies_dialog.py**

#### Cambios principales:

1. **Header explicativo** - Reemplaza el frame actual por:
```

explanation = self._create_explanation_frame(
'content_copy',
'Copias exactas detectadas',
'Se han detectado archivos idénticos (100% mismo contenido digital SHA256). '
'Puedes eliminar las copias redundantes conservando un original por grupo.'
)
layout.addWidget(explanation)

```

2. **Métricas** - Reemplaza `_create_inline_metric()` por llamadas a:
```

metrics_layout = QHBoxLayout()
metrics_layout.setSpacing(int(DesignSystem.SPACE_12))

groups_card = self._create_metric_card(
str(self.analysis.total_groups),
'Grupos de duplicados',
DesignSystem.COLOR_PRIMARY
)
metrics_layout.addWidget(groups_card)

files_card = self._create_metric_card(
str(self.analysis.total_duplicates),
'Archivos duplicados',
DesignSystem.COLOR_WARNING
)
metrics_layout.addWidget(files_card)

# Espacio recuperable con color destacado

space_card = self._create_metric_card(
format_size(self.analysis.space_wasted),
'Espacio recuperable',
DesignSystem.COLOR_SUCCESS
)
metrics_layout.addWidget(space_card)

metrics_layout.addStretch()
layout.addLayout(metrics_layout)

```

3. **Selector de estrategia con cards** - Reemplaza el `QGroupBox` actual por:
```

def _create_strategy_selector(self) -> QFrame:
"""Crea selector de estrategia con cards interactivas."""
frame = QFrame()
frame.setStyleSheet(f"""
QFrame {{
background-color: {DesignSystem.COLOR_SURFACE};
border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
border-radius: {DesignSystem.RADIUS_LG}px;
padding: {DesignSystem.SPACE_16}px;
}}
""")

    layout = QVBoxLayout(frame)
    layout.setSpacing(int(DesignSystem.SPACE_12))
    
    # Título
    title_layout = QHBoxLayout()
    title_icon = QLabel()
    icon_manager.set_label_icon(title_icon, 'rule', size=DesignSystem.ICON_SIZE_LG)
    title_label = QLabel("Elige qué archivo conservar")
    title_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_LG}px;
        font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
    """)
    title_layout.addWidget(title_icon)
    title_layout.addWidget(title_label)
    title_layout.addStretch()
    layout.addLayout(title_layout)
    
    # ButtonGroup
    self.strategy_button_group = QButtonGroup(self)
    
    # Cards horizontales
    cards_layout = QHBoxLayout()
    cards_layout.setSpacing(int(DesignSystem.SPACE_12))
    
    strategies = [
        ('oldest', 'access_time', 'Más antiguo', 'Conserva el original con fecha más antigua'),
        ('newest', 'update', 'Más reciente', 'Conserva la versión más actualizada'),
        ('largest', 'expand', 'Más grande', 'Conserva máxima calidad'),
        ('smallest', 'compress', 'Más pequeño', 'Maximiza espacio liberado')
    ]
    
    for strategy_key, icon, title, desc in strategies:
        radio = QRadioButton()
        radio.setChecked(strategy_key == self.keep_strategy)
        radio.toggled.connect(
            lambda checked, s=strategy_key: self._on_strategy_changed(s) if checked else None
        )
        self.strategy_button_group.addButton(radio)
        
        card = self._create_selection_card(
            f"strategy-{strategy_key}",
            icon,
            title,
            desc,
            strategy_key == self.keep_strategy,
            radio
        )
        cards_layout.addWidget(card)
    
    layout.addLayout(cards_layout)
    return frame
    ```

4. **Toolbar** - Reemplaza emojis por iconos:
```


# Búsqueda

search_icon = QLabel()
icon_manager.set_label_icon(search_icon, 'search', size=DesignSystem.ICON_SIZE_SM)

# Filtros

filter_icon = QLabel()
icon_manager.set_label_icon(filter_icon, 'filter_list', size=DesignSystem.ICON_SIZE_SM)

# Botón "Ver Todos"

show_all_btn = QPushButton("Ver Todos")
icon_manager.set_button_icon(show_all_btn, 'visibility', size=DesignSystem.ICON_SIZE_SM)

```

5. **TreeWidget** - Estandarizar estilos:
```

self.tree_widget.setStyleSheet(f"""
QTreeWidget {{
border: 1px solid {DesignSystem.COLOR_BORDER};
border-radius: {DesignSystem.RADIUS_BASE}px;
background-color: {DesignSystem.COLOR_SURFACE};
font-size: {DesignSystem.FONT_SIZE_SM}px;
}}
QTreeWidget::item {{
padding: {DesignSystem.SPACE_4}px;
}}
QTreeWidget::item:hover {{
background-color: {DesignSystem.COLOR_BG_2};
}}
QTreeWidget::item:selected {{
background-color: {DesignSystem.COLOR_PRIMARY};
color: {DesignSystem.COLOR_PRIMARY_TEXT};
}}
""")

```

---

### **2.2 heic_dialog.py**

Aplica los mismos patrones:

1. **Header**: `_create_explanation_frame('photo_library', 'Duplicados HEIC/JPG', '...')`
2. **Métricas**: `_create_metric_card()` para pares, tamaños HEIC/JPG
3. **Selector de formato con cards** (2 cards: JPG y HEIC)
4. **Toolbar** sin emojis
5. **TableWidget** con estilos de `DesignSystem`

---

### **2.3 renaming_dialog.py**

Cambios menores (ya está bastante limpio):

1. **Header**: `_create_explanation_frame('drive_file_rename_outline', '...', '...')`
2. **Métricas**: `_create_metric_card()` para archivos, conflictos
3. **Toolbar** sin emojis (search, filter)
4. **TableWidget** con estilos de `DesignSystem`

---

### **2.4 live_photos_dialog.py**

1. **Header**: `_create_explanation_frame('photo_camera', 'Live Photos detectadas', '...')`
2. **Métricas**: `_create_metric_card()` para grupos, espacio
3. **Selector de modo con cards** (3 cards: imagen, video, ambos)
4. **TreeWidget** con estilos de `DesignSystem`

---

## PASO 3: Validación final

Ejecuta este checklist para cada archivo:

### ✅ Checklist de código:
- [ ] NO hay emojis en el código (busca: `\u`, unicode)
- [ ] NO hay colores hardcoded (busca: `#`, `rgb(`)
- [ ] NO hay tamaños hardcoded (busca números fuera de `DesignSystem`)
- [ ] Todos los métodos nuevos tienen type hints
- [ ] Todos los métodos públicos tienen docstrings
- [ ] Se aplica `self.setStyleSheet(DesignSystem.get_tooltip_style())`
- [ ] Los imports están organizados (stdlib → third-party → local)

### ✅ Checklist funcional:
- [ ] El diálogo se abre sin errores
- [ ] Los iconos se renderizan correctamente (no aparecen cuadrados)
- [ ] Las cards de selección cambian color al hacer clic
- [ ] Los tooltips funcionan
- [ ] El backup checkbox está presente y funciona
- [ ] La lógica de negocio no se ha roto

---

## ENTREGA

Para cada archivo refactorizado, proporciona:

1. **Código completo del archivo** (no fragmentos)
2. **Lista de cambios principales** (bullet points)
3. **Pruebas realizadas** (qué funcionalidad verificaste)
4. **Problemas encontrados** (si los hay)

**Orden de entrega sugerido:**
1. Primero: `base_dialog.py` (métodos helper)
2. Segundo: `exact_copies_dialog.py` (más complejo)
3. Tercero: `heic_dialog.py`
4. Cuarto: `live_photos_dialog.py`
5. Quinto: `renaming_dialog.py` (más simple)

---

## NOTAS FINALES

- **Referencia única**: `organization_dialog.py` - copia su estructura de cards, colores, iconos
- **No toques**: Lógica de análisis, SHA256, perceptual hash, signals/slots existentes
- **Prioriza**: Consistencia visual > código perfecto
- **Testea**: Después de cada archivo, ejecuta y verifica que funciona

¿Entendido? Responde "Entendido, empezando con base_dialog.py" y procede archivo por archivo.
```


***

Este prompt integral cubre toda la refactorización agresiva en un solo documento. Está diseñado para que Copilot (o cualquier IA) pueda trabajar sistemáticamente, archivo por archivo, manteniendo consistencia total con el patrón de la cabecera de `organization_dialog.py` mientras respeta todas las convenciones de Pixaro Lab y PEP 8.