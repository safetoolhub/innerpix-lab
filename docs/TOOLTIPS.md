# Sistema de Tooltips - Pixaro Lab

## Descripción

El sistema de tooltips está completamente integrado en el `DesignSystem` y se aplica automáticamente a nivel global en toda la aplicación a través de QSS (Qt Style Sheets).

## Características Visuales

Los tooltips tienen un diseño profesional, ligero y consistente con la paleta blanca/azulada de la aplicación. Características principales:

- **Fondo claro translúcido**: `rgba(255, 255, 255, 0.98)` para un aspecto ligero y moderno
- **Texto oscuro azulado**: `#0f172a` (alto contraste y tono cercano a la familia de azules de la app)
- **Borde azul suave**: `rgba(37, 99, 235, 0.12)` que utiliza el color primario en baja opacidad
- **Padding cómodo**: `8px 12px` para espaciado adecuado
- **Tipografía**: Tamaño de fuente `13px` (ligeramente más pequeño que el texto base)
- **Radio de borde**: `8px` para esquinas más suaves

## Uso

### En cualquier widget de PyQt6

```python
widget.setToolTip("Texto del tooltip")
```

### Ejemplos

```python
# En un botón
button = QPushButton("Guardar")
button.setToolTip("Guarda los cambios realizados")

# En un label
label = QLabel("Campo obligatorio")
label.setToolTip("Este campo no puede estar vacío")

# En un widget personalizado (como DropzoneWidget)
dropzone = DropzoneWidget()
dropzone.setToolTip("Arrastra una carpeta aquí o usa el botón de debajo para seleccionar")

# Tooltips multilínea
widget.setToolTip("Primera línea\nSegunda línea\nTercera línea")
```

## Configuración

Los tokens de diseño están definidos en `ui/styles/design_system.py`:

```python
# ==================== TOOLTIPS ====================

TOOLTIP_BG = "rgba(255, 255, 255, 0.98)"
TOOLTIP_TEXT = "#0f172a"
TOOLTIP_BORDER = "rgba(37, 99, 235, 0.12)"
TOOLTIP_PADDING = "8px 12px"
TOOLTIP_FONT_SIZE = 13
TOOLTIP_BORDER_RADIUS = 8
```

## Aplicación Global

El estilo de tooltips se aplica automáticamente en el método `DesignSystem.get_stylesheet()` que es llamado en `MainWindow._apply_stylesheet()`:

```python
def _apply_stylesheet(self):
    """Aplica estilos globales a la aplicación"""
    self.setStyleSheet(DesignSystem.get_stylesheet())
```

Esto significa que **todos los tooltips en toda la aplicación** tendrán automáticamente el estilo profesional definido, sin necesidad de configuración adicional en cada widget.

## Prueba

Para probar visualmente los tooltips, ejecuta:

```bash
python test_tooltips.py
```

Esto abrirá una ventana de demostración con varios widgets que muestran tooltips con el estilo configurado.

## Ventajas del Sistema

1. **Consistencia**: Todos los tooltips se ven igual en toda la aplicación
2. **Mantenibilidad**: Un solo lugar para cambiar el estilo de todos los tooltips
3. **Simplicidad**: Uso estándar de PyQt6 sin código extra
4. **Profesionalidad**: Diseño elegante y moderno
5. **Accesibilidad**: Alto contraste para mejor legibilidad

## Notas

- Los tooltips no requieren importación de ningún módulo especial más allá de PyQt6
- El estilo se aplica mediante QSS, por lo que es multiplataforma
- Los tooltips respetan la jerarquía de widgets (heredan el estilo del parent)
- Se pueden personalizar tooltips individuales si es necesario usando `setStyleSheet()` en el widget específico (no recomendado)
