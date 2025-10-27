# 🎨 Referencia de Paleta de Colores - PhotoKit Manager

Este documento contiene la referencia completa de la paleta de colores centralizada del proyecto.

## 📋 Índice
- [Colores Primarios](#colores-primarios)
- [Colores de Estado](#colores-de-estado)
- [Colores de UI](#colores-de-ui)
- [Grises y Neutrales](#grises-y-neutrales)
- [Bordes](#bordes)
- [Fondos](#fondos)
- [Colores Específicos](#colores-específicos)
- [Uso en el Código](#uso-en-el-código)

---

## 🎯 Colores Primarios

| Variable | Valor | Uso |
|----------|-------|-----|
| `COLORS['primary']` | `#2196F3` | Color principal de la aplicación |
| `COLORS['primary_hover']` | `#1976D2` | Estado hover de elementos primarios |
| `COLORS['primary_pressed']` | `#0D47A1` | Estado pressed de elementos primarios |
| `COLORS['primary_light']` | `#64B5F6` | Variante clara del color primario |

**Ejemplo visual:**
- Botón "Analizar"
- Tabs seleccionadas
- Enlaces y elementos interactivos principales

---

## ✅ Colores de Estado

### Success (Verde)
| Variable | Valor | Uso |
|----------|-------|-----|
| `COLORS['success']` | `#28a745` | Acciones exitosas |
| `COLORS['success_hover']` | `#218838` | Hover de botones de éxito |
| `COLORS['success_pressed']` | `#1e7e34` | Pressed de botones de éxito |
| `COLORS['success_light']` | `#d4edda` | Fondos de mensajes exitosos |

### Danger (Rojo)
| Variable | Valor | Uso |
|----------|-------|-----|
| `COLORS['danger']` | `#dc3545` | Advertencias y errores |
| `COLORS['danger_hover']` | `#c82333` | Hover de botones peligrosos |
| `COLORS['danger_light']` | `#f8d7da` | Fondos de advertencias |
| `COLORS['danger_border']` | `#f5c6cb` | Bordes de advertencias |

### Warning (Amarillo)
| Variable | Valor | Uso |
|----------|-------|-----|
| `COLORS['warning']` | `#ffc107` | Avisos importantes |
| `COLORS['warning_hover']` | `#e0a800` | Hover de warnings |
| `COLORS['warning_pressed']` | `#d39e00` | Pressed de warnings |
| `COLORS['warning_light']` | `#fff3cd` | Fondos de avisos |
| `COLORS['warning_dark']` | `#856404` | Texto de avisos |
| `COLORS['warning_border']` | `#ffeeba` | Bordes de avisos |

### Info (Cyan)
| Variable | Valor | Uso |
|----------|-------|-----|
| `COLORS['info']` | `#17a2b8` | Información y preview |
| `COLORS['info_hover']` | `#138496` | Hover de info |
| `COLORS['info_pressed']` | `#0f6674` | Pressed de info |
| `COLORS['info_light']` | `#e7f3ff` | Fondos informativos |
| `COLORS['info_border']` | `#b3d9ff` | Bordes informativos |

---

## 🖌️ Colores de UI

| Variable | Valor | Uso |
|----------|-------|-----|
| `COLORS['blue']` | `#007bff` | Botones de acción secundarios |
| `COLORS['blue_hover']` | `#0056b3` | Hover de botones azules |
| `COLORS['blue_pressed']` | `#004085` | Pressed de botones azules |
| `COLORS['blue_light']` | `#0066cc` | Enlaces y texto azul claro |
| `COLORS['cyan']` | `#17a2b8` | Elementos de información |
| `COLORS['orange']` | `#FFA500` | Alertas naranjas |
| `COLORS['green']` | `#28a745` | Confirmaciones |

---

## ⬜ Grises y Neutrales

| Variable | Valor | Uso |
|----------|-------|-----|
| `COLORS['text_primary']` | `#212529` | Texto principal |
| `COLORS['text_secondary']` | `#495057` | Texto secundario |
| `COLORS['text_muted']` | `#6c757d` | Texto apagado/deshabilitado |
| `COLORS['text_light']` | `#7F8C8D` | Texto claro |
| `COLORS['text_dark']` | `#2c3e50` | Texto oscuro |
| `COLORS['text_darker']` | `#2C3E50` | Texto más oscuro |
| `COLORS['text_danger']` | `#721c24` | Texto de error |

---

## 🔲 Bordes

| Variable | Valor | Uso |
|----------|-------|-----|
| `COLORS['border_light']` | `#dee2e6` | Bordes estándar |
| `COLORS['border_medium']` | `#ced4da` | Bordes medios |
| `COLORS['border_dark']` | `#adb5bd` | Bordes oscuros |
| `COLORS['border_info']` | `#d1e3f5` | Bordes informativos |
| `COLORS['border_success']` | `#c3e6cb` | Bordes de éxito |
| `COLORS['border_danger']` | `#f5c6cb` | Bordes de peligro |

---

## 🎨 Fondos

| Variable | Valor | Uso |
|----------|-------|-----|
| `COLORS['bg_white']` | `#ffffff` | Fondo blanco |
| `COLORS['bg_light']` | `#f8f9fa` | Fondo claro |
| `COLORS['bg_lighter']` | `#f8fafc` | Fondo más claro |
| `COLORS['bg_medium']` | `#e9ecef` | Fondo medio |
| `COLORS['bg_dark']` | `#e9eef4` | Fondo oscuro |
| `COLORS['bg_info']` | `#e7f3ff` | Fondo informativo |
| `COLORS['bg_info_alt']` | `#f5f8fc` | Fondo info alternativo |
| `COLORS['bg_success']` | `#f4fcf7` | Fondo de éxito |
| `COLORS['bg_warning']` | `#fff3cd` | Fondo de aviso |
| `COLORS['bg_danger']` | `#f8d7da` | Fondo de peligro |
| `COLORS['bg_disabled']` | `#BDBDBD` | Fondo deshabilitado |
| `COLORS['bg_gray']` | `#F5F5F5` | Fondo gris |
| `COLORS['bg_card']` | `#F8F9FA` | Fondo de tarjetas |

---

## 🎯 Colores Específicos

| Variable | Valor | Uso |
|----------|-------|-----|
| `COLORS['gray']` | `gray` | Gris genérico |
| `COLORS['gray_light']` | `#CCC` | Gris claro |
| `COLORS['gray_medium']` | `#DDD` | Gris medio |
| `COLORS['red_light']` | `#FF6B6B` | Rojo claro para selecciones |
| `COLORS['red_bg']` | `#FFE5E5` | Fondo rojo claro |
| `COLORS['disabled_text']` | `#EEEEEE` | Texto deshabilitado |
| `COLORS['disabled_bg']` | `#757575` | Fondo de elementos deshabilitados |

---

## 💻 Uso en el Código

### Importar la paleta
```python
from ui.styles import COLORS
```

### Usar en estilos estáticos
```python
STYLE_CUSTOM = f"""
    QLabel {{
        color: {COLORS['text_primary']};
        background-color: {COLORS['bg_light']};
        border: 1px solid {COLORS['border_light']};
    }}
"""
```

### Usar en estilos dinámicos
```python
def create_custom_widget():
    widget = QWidget()
    widget.setStyleSheet(f"""
        QWidget {{
            background: {COLORS['bg_white']};
            color: {COLORS['text_secondary']};
        }}
    """)
    return widget
```

### Usar con get_button_style()
```python
# Usando color directo
button.setStyleSheet(styles.get_button_style(COLORS['success']))

# Usando código hex (retrocompatible)
button.setStyleSheet(styles.get_button_style("#28a745"))
```

---

## 🎨 Mejores Prácticas

1. **Siempre usa la paleta** - No uses códigos de color directos
2. **Consistencia** - Usa los mismos colores para elementos similares
3. **Accesibilidad** - Verifica el contraste entre texto y fondo
4. **Semántica** - Usa colores de estado apropiadamente (success, danger, etc.)
5. **Documentación** - Comenta por qué usas un color específico si no es obvio

---

## 📝 Añadir Nuevos Colores

Si necesitas añadir un nuevo color:

1. Añádelo a `COLORS` en `ui/styles.py`
2. Usa un nombre descriptivo y consistente
3. Actualiza este documento
4. Añade comentarios explicando su uso

```python
# En ui/styles.py
COLORS = {
    # ... colores existentes ...
    'nuevo_color': '#123456',  # Descripción del uso
}
```

---

## 🔄 Migración de Colores Legacy

Si encuentras estilos con colores hardcoded:

❌ **Antes:**
```python
widget.setStyleSheet("QLabel { color: #495057; }")
```

✅ **Después:**
```python
widget.setStyleSheet(f"QLabel {{ color: {COLORS['text_secondary']}; }}")
```

---

Última actualización: 27 de octubre de 2025
