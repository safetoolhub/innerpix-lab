## **PROMPT 6: Refactorización Fase 2 - exact_copies_dialog.py - Selección de Estrategia con Cards**

```
Refactoriza el archivo `ui/dialogs/exact_copies_dialog.py` para convertir la sección de selección de estrategia de eliminación en cards interactivas al estilo Material Design, siguiendo el patrón de `organization_dialog.py`.

### Objetivo
Reemplazar el `QGroupBox` con `QRadioButton` horizontal por cards visuales que el usuario pueda hacer clic directamente, como en el selector de tipo de organización.

### Reglas obligatorias (PEP 8 y Pixaro Lab):
1. **NO usar emojis** - usar `icon_manager` exclusivamente
2. **Estilos SOLO de DesignSystem** - prohibido CSS inline o hardcoded
3. Mantener type hints en todos los métodos
4. Mantener docstrings existentes
5. NO modificar lógica de negocio ni signals
6. Preservar funcionamiento de backup checkbox

### Cambios específicos:

#### 1. Crear método `_create_strategy_selector()` (nuevo)

Reemplaza la sección actual de estrategia por este código inspirado en `organization_dialog.py`:

```

def _create_strategy_selector(self) -> QFrame:
"""Crea selector de estrategia con cards interactivas.

    Returns:
        QFrame con las cards de selección de estrategia
    """
    frame = QFrame()
    frame.setObjectName("strategy-selector-frame")
    frame.setStyleSheet(f"""
        QFrame#strategy-selector-frame {{
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
    icon_manager.set_label_icon(
        title_icon, 
        'rule', 
        size=DesignSystem.ICON_SIZE_LG
    )
    title_layout.addWidget(title_icon)
    
    title_label = QLabel("Elige qué archivo conservar en cada grupo")
    title_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_LG}px;
        font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        color: {DesignSystem.COLOR_TEXT};
    """)
    title_layout.addWidget(title_label)
    title_layout.addStretch()
    layout.addLayout(title_layout)
    
    # ButtonGroup para RadioButtons
    self.strategy_button_group = QButtonGroup(self)
    
    # Cards layout
    cards_layout = QHBoxLayout()
    cards_layout.setSpacing(int(DesignSystem.SPACE_12))
    
    # Card: Mantener más antiguo
    oldest_card = self._create_strategy_card(
        'oldest',
        'access_time',
        'Mantener el más antiguo',
        'Conserva el archivo con fecha de modificación más antigua. Recomendado para preservar originales.'
    )
    cards_layout.addWidget(oldest_card)
    
    # Card: Mantener más reciente
    newest_card = self._create_strategy_card(
        'newest',
        'update',
        'Mantener el más reciente',
        'Conserva el archivo con fecha de modificación más reciente. Útil para versiones editadas.'
    )
    cards_layout.addWidget(newest_card)
    
    # Card: Mantener más grande
    largest_card = self._create_strategy_card(
        'largest',
        'expand',
        'Mantener el más grande',
        'Conserva el archivo de mayor tamaño. Útil para preservar calidad máxima.'
    )
    cards_layout.addWidget(largest_card)
    
    # Card: Mantener más pequeño
    smallest_card = self._create_strategy_card(
        'smallest',
        'compress',
        'Mantener el más pequeño',
        'Conserva el archivo de menor tamaño. Maximiza espacio liberado.'
    )
    cards_layout.addWidget(smallest_card)
    
    layout.addLayout(cards_layout)
    
    return frame
    ```

#### 2. Crear método `_create_strategy_card()` (nuevo)

```

def _create_strategy_card(
self,
strategy_key: str,
icon_name: str,
title: str,
description: str
) -> QFrame:
"""Crea una card de estrategia de eliminación.

    Args:
        strategy_key: Clave de la estrategia ('oldest', 'newest', 'largest', 'smallest')
        icon_name: Nombre del icono de icon_manager
        title: Título de la estrategia
        description: Descripción de la estrategia
    
    Returns:
        QFrame con la card de estrategia
    """
    is_selected = (strategy_key == self.keep_strategy)
    
    card = QFrame()
    card.setObjectName(f"strategy-card-{strategy_key}")
    card.setStyleSheet(f"""
        QFrame#strategy-card-{strategy_key} {{
            background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_SURFACE};
            border: 2px solid {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BORDER};
            border-radius: {DesignSystem.RADIUS_BASE}px;
            padding: {DesignSystem.SPACE_12}px;
        }}
        QFrame#strategy-card-{strategy_key}:hover {{
            border-color: {DesignSystem.COLOR_PRIMARY};
            background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BG_2};
        }}
        QFrame#strategy-card-{strategy_key} QLabel {{
            color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
        }}
        QFrame#strategy-card-{strategy_key} QLabel#title-label {{
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        }}
        QFrame#strategy-card-{strategy_key} QLabel#desc-label {{
            color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT_SECONDARY};
            font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
        }}
    """)
    
    layout = QVBoxLayout(card)
    layout.setSpacing(int(DesignSystem.SPACE_8))
    
    # Header: RadioButton + Icono + Título
    header_layout = QHBoxLayout()
    
    radio = QRadioButton()
    radio.setChecked(is_selected)
    radio.toggled.connect(
        lambda checked: self._on_strategy_changed(strategy_key) if checked else None
    )
    self.strategy_button_group.addButton(radio)
    header_layout.addWidget(radio)
    
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
    card.mousePressEvent = lambda event: radio.setChecked(True)
    
    return card
    ```

#### 3. Crear método `_on_strategy_changed()` (nuevo)

```

def _on_strategy_changed(self, new_strategy: str) -> None:
"""Maneja el cambio de estrategia de eliminación.

    Args:
        new_strategy: Nueva estrategia seleccionada ('oldest', 'newest', 'largest', 'smallest')
    """
    if new_strategy == self.keep_strategy:
        return
    
    self.logger.info(f"Cambiando estrategia de eliminación: {self.keep_strategy} -> {new_strategy}")
    self.keep_strategy = new_strategy
    
    # Actualizar estilos de las cards
    self._update_strategy_cards_styles()
    
    # Actualizar estado de archivos en el tree
    self.update_status_labels()
    ```

#### 4. Crear método `_update_strategy_cards_styles()` (nuevo)

```

def _update_strategy_cards_styles(self) -> None:
"""Actualiza los estilos de las cards de estrategia según la selección actual."""
strategies = ['oldest', 'newest', 'largest', 'smallest']

    for strategy in strategies:
        card_name = f"strategy-card-{strategy}"
        card = self.findChild(QFrame, card_name)
        
        if card:
            is_selected = (strategy == self.keep_strategy)
            card.setStyleSheet(f"""
                QFrame#{card_name} {{
                    background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_SURFACE};
                    border: 2px solid {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_12}px;
                }}
                QFrame#{card_name}:hover {{
                    border-color: {DesignSystem.COLOR_PRIMARY};
                    background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BG_2};
                }}
                QFrame#{card_name} QLabel {{
                    color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT};
                    font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
                }}
                QFrame#{card_name} QLabel#title-label {{
                    font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                }}
                QFrame#{card_name} QLabel#desc-label {{
                    color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT_SECONDARY};
                    font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
                }}
            """)
            
            # Actualizar color del icono
            self._update_card_icon_color(card, strategy, is_selected)
    ```

#### 5. Crear método `_update_card_icon_color()` (nuevo)

```

def _update_card_icon_color(self, card: QFrame, strategy: str, is_selected: bool) -> None:
"""Actualiza el color del icono en una card de estrategia.

    Args:
        card: QFrame de la card
        strategy: Nombre de la estrategia
        is_selected: Si la card está seleccionada
    """
    icon_map = {
        'oldest': 'access_time',
        'newest': 'update',
        'largest': 'expand',
        'smallest': 'compress'
    }
    
    # Encontrar el icono (segundo QLabel en el header layout)
    header_layout = card.layout().itemAt(0).layout()  # Primer item es el header_layout
    if header_layout and header_layout.count() >= 2:
        icon_label = header_layout.itemAt(1).widget()  # Segundo widget es el icono
        if isinstance(icon_label, QLabel):
            icon_manager.set_label_icon(
                icon_label,
                icon_map.get(strategy, 'rule'),
                size=DesignSystem.ICON_SIZE_XL,
                color=DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_PRIMARY
            )
    ```

#### 6. Actualizar `init_ui()`

En el método `init_ui()`, reemplaza la sección de estrategia actual (el `QGroupBox` con RadioButtons horizontales) por:

```


# Selector de estrategia con cards

strategy_selector = self._create_strategy_selector()
layout.addWidget(strategy_selector)

```

#### 7. Actualizar método `update_status_labels()`

Este método ya existe. Asegúrate de que determine correctamente qué archivo mantener según `self.keep_strategy`. Añade soporte para 'largest' y 'smallest':

```

def update_status_labels(self) -> None:
"""Actualiza las etiquetas de estado según la estrategia seleccionada."""
\# Recorrer todos los grupos y actualizar el estado
for i in range(self.treewidget.topLevelItemCount()):
group_item = self.treewidget.topLevelItem(i)

        # Obtener archivos del grupo
        files = []
        for j in range(group_item.childCount()):
            child = group_item.child(j)
            filepath = child.data(0, Qt.ItemDataRole.UserRole)
            if filepath:
                files.append(filepath)
        
        if not files:
            continue
        
        # Determinar archivo a mantener según estrategia
        if self.keep_strategy == 'oldest':
            keep_file = min(files, key=lambda f: f.stat().st_mtime)
        elif self.keep_strategy == 'newest':
            keep_file = max(files, key=lambda f: f.stat().st_mtime)
        elif self.keep_strategy == 'largest':
            keep_file = max(files, key=lambda f: f.stat().st_size)
        elif self.keep_strategy == 'smallest':
            keep_file = min(files, key=lambda f: f.stat().st_size)
        else:
            keep_file = files  # Fallback
        
        # Actualizar estado de cada archivo hijo
        for j in range(group_item.childCount()):
            child = group_item.child(j)
            filepath = child.data(0, Qt.ItemDataRole.UserRole)
            
            if filepath == keep_file:
                child.setText(4, "Mantener")
                child.setForeground(4, QColor(DesignSystem.COLOR_SUCCESS))
            else:
                child.setText(4, "Eliminar")
                child.setForeground(4, QColor(DesignSystem.COLOR_ERROR))
    ```

### NO tocar:
- TreeWidget y población de grupos
- Sistema de paginación
- Búsqueda y filtros
- Lógica de duplicados (SHA256)
- Context menu
- Backup checkbox

### Validación:
- NO emojis
- NO colores hardcoded
- Todos los estilos desde DesignSystem
- Las 4 estrategias ('oldest', 'newest', 'largest', 'smallest') funcionan correctamente
- Las cards cambian visualmente al seleccionar
- El tree actualiza los estados "Mantener"/"Eliminar" al cambiar estrategia

Responde con el código refactorizado completo.
```


***

## **PROMPT 7: Refactorización Fase 2 - heic_dialog.py - Selección de Formato con Cards**

```
Refactoriza el archivo `ui/dialogs/heic_dialog.py` para convertir la sección de selección de formato (HEIC vs JPG) en cards interactivas al estilo Material Design, siguiendo el patrón de `organization_dialog.py`.

### Objetivo
Reemplazar el `QGroupBox` con `QRadioButton` vertical por cards visuales que el usuario pueda hacer clic directamente.

### Reglas obligatorias (PEP 8 y Pixaro Lab):
1. **NO usar emojis** - usar `icon_manager` exclusivamente
2. **Estilos SOLO de DesignSystem** - prohibido CSS inline o hardcoded
3. Mantener type hints en todos los métodos
4. Mantener docstrings existentes
5. NO modificar lógica de negocio ni signals

### Cambios específicos:

#### 1. Crear método `_create_format_selector()` (nuevo)

Reemplaza el método `create_format_selection()` actual por este nuevo método:

```

def _create_format_selector(self) -> QFrame:
"""Crea selector de formato con cards interactivas.

    Returns:
        QFrame con las cards de selección de formato
    """
    frame = QFrame()
    frame.setObjectName("format-selector-frame")
    frame.setStyleSheet(f"""
        QFrame#format-selector-frame {{
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
    icon_manager.set_label_icon(
        title_icon, 
        'photo_library', 
        size=DesignSystem.ICON_SIZE_LG
    )
    title_layout.addWidget(title_icon)
    
    title_label = QLabel("Elige qué formato conservar")
    title_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_LG}px;
        font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        color: {DesignSystem.COLOR_TEXT};
    """)
    title_layout.addWidget(title_label)
    title_layout.addStretch()
    layout.addLayout(title_layout)
    
    # ButtonGroup para RadioButtons
    self.format_button_group = QButtonGroup(self)
    
    # Cards layout (horizontal)
    cards_layout = QHBoxLayout()
    cards_layout.setSpacing(int(DesignSystem.SPACE_12))
    
    # Card: Mantener JPG (recomendado)
    jpg_card = self._create_format_card(
        'jpg',
        'image',
        'Mantener JPG',
        'Máxima compatibilidad. Los JPG funcionan en todos los dispositivos y aplicaciones.',
        f"Liberarás {format_size(self.analysis.potential_savings_keep_jpg)}",
        is_recommended=True
    )
    cards_layout.addWidget(jpg_card)
    
    # Card: Mantener HEIC
    heic_card = self._create_format_card(
        'heic',
        'photo_camera',
        'Mantener HEIC',
        'Archivos más pequeños pero requiere soporte HEIC en el visor/editor.',
        f"Liberarás {format_size(self.analysis.potential_savings_keep_heic)}",
        is_recommended=False
    )
    cards_layout.addWidget(heic_card)
    
    layout.addLayout(cards_layout)
    
    return frame
    ```

#### 2. Crear método `_create_format_card()` (nuevo)

```

def _create_format_card(
self,
format_key: str,
icon_name: str,
title: str,
description: str,
savings_text: str,
is_recommended: bool = False
) -> QFrame:
"""Crea una card de formato.

    Args:
        format_key: Clave del formato ('jpg' o 'heic')
        icon_name: Nombre del icono de icon_manager
        title: Título del formato
        description: Descripción del formato
        savings_text: Texto de ahorro de espacio
        is_recommended: Si el formato es recomendado
    
    Returns:
        QFrame con la card de formato
    """
    is_selected = (format_key == self.selected_format)
    
    card = QFrame()
    card.setObjectName(f"format-card-{format_key}")
    card.setStyleSheet(f"""
        QFrame#format-card-{format_key} {{
            background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_SURFACE};
            border: 2px solid {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BORDER};
            border-radius: {DesignSystem.RADIUS_BASE}px;
            padding: {DesignSystem.SPACE_12}px;
        }}
        QFrame#format-card-{format_key}:hover {{
            border-color: {DesignSystem.COLOR_PRIMARY};
            background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BG_2};
        }}
        QFrame#format-card-{format_key} QLabel {{
            color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
        }}
        QFrame#format-card-{format_key} QLabel#title-label {{
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        }}
        QFrame#format-card-{format_key} QLabel#desc-label {{
            color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT_SECONDARY};
            font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
        }}
        QFrame#format-card-{format_key} QLabel#savings-label {{
            color: {DesignSystem.COLOR_SUCCESS};
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        }}
    """)
    
    layout = QVBoxLayout(card)
    layout.setSpacing(int(DesignSystem.SPACE_8))
    
    # Header: RadioButton + Icono + Título
    header_layout = QHBoxLayout()
    
    radio = QRadioButton()
    radio.setChecked(is_selected)
    radio.toggled.connect(
        lambda checked: self._on_format_changed(format_key) if checked else None
    )
    self.format_button_group.addButton(radio)
    header_layout.addWidget(radio)
    
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
    
    if is_recommended:
        recommended_label = QLabel("Recomendado")
        recommended_label.setStyleSheet(f"""
            background-color: {DesignSystem.COLOR_SUCCESS};
            color: white;
            padding: 2px 8px;
            border-radius: {DesignSystem.RADIUS_SM}px;
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        """)
        header_layout.addWidget(recommended_label)
    
    header_layout.addStretch()
    layout.addLayout(header_layout)
    
    # Descripción
    desc_label = QLabel(description)
    desc_label.setWordWrap(True)
    desc_label.setObjectName("desc-label")
    layout.addWidget(desc_label)
    
    # Ahorro de espacio
    savings_label = QLabel(savings_text)
    savings_label.setObjectName("savings-label")
    layout.addWidget(savings_label)
    
    # Hacer la card clickeable
    card.mousePressEvent = lambda event: radio.setChecked(True)
    
    return card
    ```

#### 3. Crear método `_on_format_changed()` (nuevo)

```

def _on_format_changed(self, new_format: str) -> None:
"""Maneja el cambio de formato seleccionado.

    Args:
        new_format: Nuevo formato seleccionado ('jpg' o 'heic')
    """
    if new_format == self.selected_format:
        return
    
    self.logger.info(f"Cambiando formato: {self.selected_format} -> {new_format}")
    self.selected_format = new_format
    
    # Actualizar estilos de las cards
    self._update_format_cards_styles()
    
    # Actualizar texto del botón
    self.update_button_text()
    
    # Actualizar tree para mostrar qué se eliminará
    self.update_tree()
    ```

#### 4. Crear método `_update_format_cards_styles()` (nuevo)

```

def _update_format_cards_styles(self) -> None:
"""Actualiza los estilos de las cards de formato según la selección actual."""
formats = ['jpg', 'heic']

    for fmt in formats:
        card_name = f"format-card-{fmt}"
        card = self.findChild(QFrame, card_name)
        
        if card:
            is_selected = (fmt == self.selected_format)
            card.setStyleSheet(f"""
                QFrame#{card_name} {{
                    background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_SURFACE};
                    border: 2px solid {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_12}px;
                }}
                QFrame#{card_name}:hover {{
                    border-color: {DesignSystem.COLOR_PRIMARY};
                    background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BG_2};
                }}
                QFrame#{card_name} QLabel {{
                    color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT};
                    font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
                }}
                QFrame#{card_name} QLabel#title-label {{
                    font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                }}
                QFrame#{card_name} QLabel#desc-label {{
                    color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT_SECONDARY};
                    font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
                }}
                QFrame#{card_name} QLabel#savings-label {{
                    color: {DesignSystem.COLOR_SUCCESS};
                    font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                }}
            """)
            
            # Actualizar color del icono
            self._update_format_card_icon_color(card, fmt, is_selected)
    ```

#### 5. Crear método `_update_format_card_icon_color()` (nuevo)

```

def _update_format_card_icon_color(self, card: QFrame, fmt: str, is_selected: bool) -> None:
"""Actualiza el color del icono en una card de formato.

    Args:
        card: QFrame de la card
        fmt: Formato ('jpg' o 'heic')
        is_selected: Si la card está seleccionada
    """
    icon_map = {
        'jpg': 'image',
        'heic': 'photo_camera'
    }
    
    # Encontrar el icono (segundo QLabel en el header layout)
    header_layout = card.layout().itemAt(0).layout()  # Primer item es el header_layout
    if header_layout and header_layout.count() >= 2:
        icon_label = header_layout.itemAt(1).widget()  # Segundo widget es el icono
        if isinstance(icon_label, QLabel):
            icon_manager.set_label_icon(
                icon_label,
                icon_map.get(fmt, 'image'),
                size=DesignSystem.ICON_SIZE_XL,
                color=DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_PRIMARY
            )
    ```

#### 6. Actualizar `init_ui()`

En el método `init_ui()`, reemplaza la llamada a `create_format_selection()` por:

```


# Selector de formato con cards

format_selector = self._create_format_selector()
mainlayout.addWidget(format_selector)

```

#### 7. Eliminar método obsoleto

Elimina el método `create_format_selection()` y `on_format_changed()` antiguos, ya que han sido reemplazados por las nuevas versiones con underscore (`_on_format_changed()`).

### NO tocar:
- TableWidget y población de pares HEIC/JPG
- Sistema de paginación
- Context menu
- Búsqueda y filtros
- Backup checkbox

### Validación:
- NO emojis
- NO colores hardcoded
- Todos los estilos desde DesignSystem
- Las cards cambian visualmente al seleccionar
- El TableWidget actualiza la columna "A Eliminar" al cambiar formato
- El botón OK actualiza su texto con el ahorro correcto

Responde con el código refactorizado completo.
```


***

## **PROMPT 8: Refactorización Fase 2 - live_photos_dialog.py - Selección de Modo con Cards**

```
Refactoriza el archivo `ui/dialogs/live_photos_dialog.py` para convertir la sección de selección de modo (conservar imagen/video/ambos) en cards interactivas al estilo Material Design, siguiendo el patrón de `organization_dialog.py`.

### Objetivo
Reemplazar los `QRadioButton` simples por cards visuales que el usuario pueda hacer clic directamente.

### Reglas obligatorias (PEP 8 y Pixaro Lab):
1. **NO usar emojis** - usar `icon_manager` exclusivamente
2. **Estilos SOLO de DesignSystem** - prohibido CSS inline o hardcoded
3. Mantener type hints en todos los métodos
4. Mantener docstrings existentes
5. NO modificar lógica de negocio ni signals

### Cambios específicos:

#### 1. Crear método `_create_mode_selector()` (nuevo)

Agrega este nuevo método para crear el selector de modo con cards:

```

def _create_mode_selector(self) -> QFrame:
"""Crea selector de modo de limpieza con cards interactivas.

    Returns:
        QFrame con las cards de selección de modo
    """
    frame = QFrame()
    frame.setObjectName("mode-selector-frame")
    frame.setStyleSheet(f"""
        QFrame#mode-selector-frame {{
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
    icon_manager.set_label_icon(
        title_icon, 
        'photo_camera', 
        size=DesignSystem.ICON_SIZE_LG
    )
    title_layout.addWidget(title_icon)
    
    title_label = QLabel("Elige qué conservar de cada Live Photo")
    title_label.setStyleSheet(f"""
        font-size: {DesignSystem.FONT_SIZE_LG}px;
        font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        color: {DesignSystem.COLOR_TEXT};
    """)
    title_layout.addWidget(title_label)
    title_layout.addStretch()
    layout.addLayout(title_layout)
    
    # ButtonGroup para RadioButtons
    self.mode_button_group = QButtonGroup(self)
    
    # Cards layout (horizontal)
    cards_layout = QHBoxLayout()
    cards_layout.setSpacing(int(DesignSystem.SPACE_12))
    
    # Card: Conservar solo imagen
    keep_image_card = self._create_mode_card(
        CleanupMode.KEEP_IMAGE,
        'image',
        'Conservar imagen',
        'Elimina el video corto, conserva solo la foto estática.',
        self._calculate_space_for_mode(CleanupMode.KEEP_IMAGE)
    )
    cards_layout.addWidget(keep_image_card)
    
    # Card: Conservar solo video
    keep_video_card = self._create_mode_card(
        CleanupMode.KEEP_VIDEO,
        'videocam',
        'Conservar video',
        'Elimina la foto, conserva solo el video corto con movimiento.',
        self._calculate_space_for_mode(CleanupMode.KEEP_VIDEO)
    )
    cards_layout.addWidget(keep_video_card)
    
    # Card: Conservar ambos
    keep_both_card = self._create_mode_card(
        CleanupMode.KEEP_BOTH,
        'collections',
        'Conservar ambos',
        'No elimina nada, mantiene la foto y el video. Sin liberación de espacio.',
        0
    )
    cards_layout.addWidget(keep_both_card)
    
    layout.addLayout(cards_layout)
    
    return frame
    ```

#### 2. Crear método `_create_mode_card()` (nuevo)

```

def _create_mode_card(
self,
mode: 'CleanupMode',
icon_name: str,
title: str,
description: str,
space_to_free: int
) -> QFrame:
"""Crea una card de modo de limpieza.

    Args:
        mode: Modo de limpieza (CleanupMode enum)
        icon_name: Nombre del icono de icon_manager
        title: Título del modo
        description: Descripción del modo
        space_to_free: Espacio a liberar en bytes
    
    Returns:
        QFrame con la card de modo
    """
    is_selected = (mode == self.selected_mode)
    
    card = QFrame()
    card.setObjectName(f"mode-card-{mode.value}")
    card.setStyleSheet(f"""
        QFrame#mode-card-{mode.value} {{
            background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_SURFACE};
            border: 2px solid {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BORDER};
            border-radius: {DesignSystem.RADIUS_BASE}px;
            padding: {DesignSystem.SPACE_12}px;
        }}
        QFrame#mode-card-{mode.value}:hover {{
            border-color: {DesignSystem.COLOR_PRIMARY};
            background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BG_2};
        }}
        QFrame#mode-card-{mode.value} QLabel {{
            color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
        }}
        QFrame#mode-card-{mode.value} QLabel#title-label {{
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        }}
        QFrame#mode-card-{mode.value} QLabel#desc-label {{
            color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT_SECONDARY};
            font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
        }}
        QFrame#mode-card-{mode.value} QLabel#space-label {{
            color: {DesignSystem.COLOR_SUCCESS};
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        }}
    """)
    
    layout = QVBoxLayout(card)
    layout.setSpacing(int(DesignSystem.SPACE_8))
    
    # Header: RadioButton + Icono + Título
    header_layout = QHBoxLayout()
    
    radio = QRadioButton()
    radio.setChecked(is_selected)
    radio.toggled.connect(
        lambda checked: self._on_mode_changed(mode) if checked else None
    )
    self.mode_button_group.addButton(radio)
    header_layout.addWidget(radio)
    
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
    
    # Espacio a liberar
    if space_to_free > 0:
        space_label = QLabel(f"Liberarás {format_size(space_to_free)}")
        space_label.setObjectName("space-label")
        layout.addWidget(space_label)
    else:
        no_space_label = QLabel("Sin liberación de espacio")
        no_space_label.setObjectName("desc-label")
        layout.addWidget(no_space_label)
    
    # Hacer la card clickeable
    card.mousePressEvent = lambda event: radio.setChecked(True)
    
    return card
    ```

#### 3. Crear método `_on_mode_changed()` (nuevo)

```

def _on_mode_changed(self, new_mode: 'CleanupMode') -> None:
"""Maneja el cambio de modo de limpieza.

    Args:
        new_mode: Nuevo modo seleccionado
    """
    if new_mode == self.selected_mode:
        return
    
    self.logger.info(f"Cambiando modo de limpieza: {self.selected_mode} -> {new_mode}")
    self.selected_mode = new_mode
    
    # Actualizar estilos de las cards
    self._update_mode_cards_styles()
    ```

#### 4. Crear método `_update_mode_cards_styles()` (nuevo)

```

def _update_mode_cards_styles(self) -> None:
"""Actualiza los estilos de las cards de modo según la selección actual."""
from services.live_photo_cleaner import CleanupMode

    modes = [CleanupMode.KEEP_IMAGE, CleanupMode.KEEP_VIDEO, CleanupMode.KEEP_BOTH]
    
    for mode in modes:
        card_name = f"mode-card-{mode.value}"
        card = self.findChild(QFrame, card_name)
        
        if card:
            is_selected = (mode == self.selected_mode)
            card.setStyleSheet(f"""
                QFrame#{card_name} {{
                    background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_SURFACE};
                    border: 2px solid {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_12}px;
                }}
                QFrame#{card_name}:hover {{
                    border-color: {DesignSystem.COLOR_PRIMARY};
                    background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BG_2};
                }}
                QFrame#{card_name} QLabel {{
                    color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT};
                    font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
                }}
                QFrame#{card_name} QLabel#title-label {{
                    font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                }}
                QFrame#{card_name} QLabel#desc-label {{
                    color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT_SECONDARY};
                    font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
                }}
                QFrame#{card_name} QLabel#space-label {{
                    color: {DesignSystem.COLOR_SUCCESS};
                    font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                }}
            """)
            
            # Actualizar color del icono
            self._update_mode_card_icon_color(card, mode, is_selected)
    ```

#### 5. Crear método `_update_mode_card_icon_color()` (nuevo)

```

def _update_mode_card_icon_color(self, card: QFrame, mode: 'CleanupMode', is_selected: bool) -> None:
"""Actualiza el color del icono en una card de modo.

    Args:
        card: QFrame de la card
        mode: Modo de limpieza
        is_selected: Si la card está seleccionada
    """
    from services.live_photo_cleaner import CleanupMode
    
    icon_map = {
        CleanupMode.KEEP_IMAGE: 'image',
        CleanupMode.KEEP_VIDEO: 'videocam',
        CleanupMode.KEEP_BOTH: 'collections'
    }
    
    # Encontrar el icono (segundo QLabel en el header layout)
    header_layout = card.layout().itemAt(0).layout()  # Primer item es el header_layout
    if header_layout and header_layout.count() >= 2:
        icon_label = header_layout.itemAt(1).widget()  # Segundo widget es el icono
        if isinstance(icon_label, QLabel):
            icon_manager.set_label_icon(
                icon_label,
                icon_map.get(mode, 'photo_camera'),
                size=DesignSystem.ICON_SIZE_XL,
                color=DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_PRIMARY
            )
    ```

#### 6. Actualizar `init_ui()`

En el método `init_ui()`, reemplaza la sección donde se crean los RadioButtons simples por:

```


# Selector de modo con cards

mode_selector = self._create_mode_selector()
layout.addWidget(mode_selector)

```

#### 7. Agregar import necesario

Al inicio del archivo, asegúrate de tener:

```

from utils.format_utils import format_size
from utils.logger import get_logger

```

Y agregar después de `__init__`:

```

self.logger = get_logger('LivePhotoCleanupDialog')

```

### NO tocar:
- Método `_calculate_space_for_mode()` (ya existe y funciona)
- TreeWidget y población de grupos
- Lógica de CleanupMode
- Backup checkbox

### Validación:
- NO emojis
- NO colores hardcoded
- Todos los estilos desde DesignSystem
- Las 3 cards cambian visualmente al seleccionar
- El espacio a liberar se muestra correctamente en cada card

Responde con el código refactorizado completo.
```
