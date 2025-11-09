# PROMPT COMPLETO: Implementación de Análisis de Duplicados Similares con Diálogos Material Design

## Contexto del Proyecto

Pixaro Lab es una aplicación de escritorio multiplataforma (Linux, Windows, macOS) desarrollada en Python con PyQt6 para analizar y gestionar colecciones de imágenes y vídeos, principalmente orientada a fotos iOS.[^8]

En Stage 3, se muestran 6 herramientas mediante cards. Cinco de ellas ya tienen resultados listos del análisis inicial, pero **"Duplicados Similares" requiere un análisis previo** con parámetro de sensibilidad que puede tardar varios minutos.[^9]

## Objetivo

Implementar un flujo UX profesional con dos diálogos modales **Material Design 3** para:

1. Configurar y lanzar el análisis de duplicados similares
2. Mostrar el progreso del análisis en tiempo real (bloqueante)
3. Actualizar la card con los resultados al completar

## Arquitectura y Estructura del Proyecto

```
pixaro-lab/
├── main.py
├── config.py
├── ui/
│   ├── stages/
│   │   └── stage3window.py          # Modificar: añadir lógica para similares
│   ├── dialogs/
│   │   ├── similardialog.py         # Ya existe: gestión de resultados
│   │   ├── similarityconfigdialog.py    # NUEVO: configuración
│   │   └── similarityprogressdialog.py  # NUEVO: progreso bloqueante
│   ├── widgets/
│   │   └── toolcard.py              # Modificar: añadir método para link
│   └── styles/
│       └── designsystem.py          # Ya existe: colores y constantes
├── services/
│   └── duplicatesimilardetector.py  # Ya existe: lógica de análisis
└── utils/
    ├── icons.py                     # Ya existe: iconos Material Design
    └── formatutils.py               # Ya existe: formateo de tamaños
```


## Especificaciones de Diseño Material Design 3

### Principios de Diseño

Todos los diálogos deben seguir **Material Design 3** specifications:[^10][^11][^1][^2][^6]

- **Elevación**: Dialogs tienen elevation 24dp (box-shadow: 0 11px 15px rgba(0,0,0,0.2))
- **Border radius**: 28px para diálogos (radius-2xl en design system)
- **Padding estándar**: 24dp (24px) para contenido
- **Espaciado vertical**: 16dp entre secciones
- **Tipografía**: Roboto o sistema nativo, con jerarquía clara
- **Colores**: Usar variables del design system existente
- **Accesibilidad**: ARIA roles correctos, focus trap, navegación con teclado[^11][^10]


### Paleta de Colores (del Design System)

```python
# Referencia desde ui/styles/designsystem.py
color-primary: #1976D2          # Azul principal
color-primary-hover: #1565C0    # Azul hover
color-secondary: #757575        # Gris secundario
color-success: #4CAF50          # Verde éxito
color-warning: #FF9800          # Naranja advertencia
color-error: #F44336            # Rojo error
color-background: #FAFAFA       # Fondo claro
color-surface: #FFFFFF          # Superficie de cards/dialogs
color-text: #212121             # Texto principal
color-text-secondary: #757575   # Texto secundario
color-border: #E0E0E0           # Bordes sutiles
color-card-border: #EEEEEE      # Bordes de cards
```


### Iconografía Material Design

Usar iconos del sistema existente (`utils/icons.py`) basados en Material Design Icons:

- `image-search` o `compare`: Header de duplicados similares
- `cog` o `tune`: Configuración
- `play-circle`: Iniciar análisis
- `loading` o `sync`: Spinner animado
- `clock-outline`: Tiempo estimado
- `chart-bar`: Estadísticas
- `check-circle`: Éxito
- `alert-circle`: Advertencia
- `information`: Información
- `close`: Cerrar diálogos

***

## PARTE 1: Modificación de la Card de Duplicados Similares (Stage 3)

### Estado Inicial: Sin Análisis

La card debe mantener consistencia visual con las otras 5, pero comunicar que requiere configuración.[^8]

**Archivo**: `ui/stages/stage3window.py` o donde se generen las cards

**Layout visual de la card**:

```
┌─────────────────────────────────────────┐
│ 🔍 Duplicados Similares                 │  ← Header con icono Material
│                                         │
│ Detecta fotos visualmente similares    │  ← Descripción (4 líneas máx)
│ pero no idénticas: recortes, rotacio-  │
│ nes, ediciones. Personaliza la sensi-  │
│ bilidad antes de analizar.              │
│                                         │
│ ─────────────────────────────────────── │  ← Separador sutil
│                                         │
│ ⚙️  Requiere configuración              │  ← Icono + estado
│    Este análisis se personaliza según  │
│    el nivel de similitud deseado.      │
│                                         │
│         [Configurar y analizar]         │  ← Botón secundario
└─────────────────────────────────────────┘
```

**Especificaciones CSS/QSS**:

```css
/* Card container */
QFrame#similar_duplicates_card {
    background-color: #FFFFFF;
    border: 1px solid #EEEEEE;
    border-radius: 12px;
    padding: 20px;
    min-width: 320px;
    max-width: 380px;
}

/* Header con icono */
QLabel#card_header {
    font-size: 18px;
    font-weight: 600;
    color: #212121;
    padding-bottom: 12px;
}

/* Descripción */
QLabel#card_description {
    font-size: 14px;
    color: #757575;
    line-height: 1.5;
    padding-bottom: 16px;
}

/* Separador */
QFrame#separator {
    height: 1px;
    background-color: #E0E0E0;
    margin: 16px 0;
}

/* Sección de estado */
QLabel#status_label {
    font-size: 13px;
    font-weight: 500;
    color: #212121;
}

QLabel#status_description {
    font-size: 13px;
    color: #757575;
    padding-left: 24px; /* Alinear con icono */
    line-height: 1.4;
}

/* Botón de acción */
QPushButton#configure_button {
    background-color: transparent;
    border: 2px solid #1976D2;
    color: #1976D2;
    font-size: 14px;
    font-weight: 500;
    padding: 10px 24px;
    border-radius: 20px;
    min-width: 200px;
}

QPushButton#configure_button:hover {
    background-color: rgba(25, 118, 210, 0.08);
}

QPushButton#configure_button:pressed {
    background-color: rgba(25, 118, 210, 0.16);
}
```

**Comportamiento**: Al hacer clic en el botón o en toda la card, abrir `SimilarityConfigDialog`.

***

## PARTE 2: Diálogo de Configuración (Material Design 3)

### Archivo Nuevo: `ui/dialogs/similarityconfigdialog.py`

**Propósito**: Diálogo modal compacto para configurar la sensibilidad del análisis.

**Layout visual completo**:

```
╔═══════════════════════════════════════════════════════╗
║  Configurar Análisis de Duplicados Similares      [×] ║  ← Header MD3 con elevation
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  Ajusta la sensibilidad del análisis de similitud    ║  ← Texto intro
║  para detectar imágenes parecidas:                   ║
║                                                       ║
║  ┌─────────────────────────────────────────────────┐ ║
║  │ Sensibilidad de detección                       │ ║  ← Card interna
║  │                                                 │ ║
║  │  Menos estricto                  Más estricto   │ ║
║  │       30%  ◄────────●──────────►  100%         │ ║  ← Slider MD3
║  │                    85%                          │ ║
║  │                                                 │ ║
║  │  🎯 Valor seleccionado: 85%                    │ ║  ← Display dinámico
║  └─────────────────────────────────────────────────┘ ║
║                                                       ║
║  ℹ️  ¿Qué significa esto?                             ║  ← Sección info
║                                                       ║
║  • 30-60%: Detecta solo imágenes muy similares      ║
║    (mismo objeto, ángulos ligeramente diferentes)    ║
║                                                       ║
║  • 60-85%: Balance recomendado (predeterminado)     ║
║    Detecta recortes, rotaciones, ajustes            ║
║                                                       ║
║  • 85-100%: Detecta similitudes más amplias         ║
║    (misma escena, objetos o sujetos parecidos)      ║
║                                                       ║
║  ───────────────────────────────────────────────────  ║  ← Separador
║                                                       ║
║  ⏱️  Tiempo estimado: ~3-5 min (2,847 archivos)     ║  ← Info temporal
║                                                       ║
║  ⚠️  El análisis se ejecutará en modo bloqueante.    ║  ← Advertencia
║     No podrás usar la aplicación hasta que termine.  ║
║                                                       ║
║  ───────────────────────────────────────────────────  ║
║                                                       ║
║                       [Cancelar]  [Iniciar análisis] ║  ← Botones MD3
╚═══════════════════════════════════════════════════════╝
```


### Especificaciones Técnicas del Diálogo

**Dimensiones Material Design**:

- Ancho: 600px
- Alto: variable (aproximadamente 580px)
- **Modal**: Sí, bloquea interacción (QDialog.Modal)[^1][^2]
- **Centrado**: Sobre la ventana principal
- **Elevation**: 24dp (box-shadow: 0 11px 15px rgba(0,0,0,0.2))
- **Border radius**: 28px (Material Design 3)[^1]
- **Min distance from screen edges**: 48dp[^6]

**Estructura del código**:

```python
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QPushButton, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from utils.icons import get_icon
from ui.styles.designsystem import DesignSystem

class SimilarityConfigDialog(QDialog):
    """
    Diálogo Material Design 3 para configurar análisis de duplicados similares.
    Modal bloqueante.
    """
    
    def __init__(self, parent=None, file_count: int = 0, previous_sensitivity: int = 85):
        super().__init__(parent)
        self.file_count = file_count
        self.sensitivity_value = previous_sensitivity
        self._setup_ui()
        self._apply_material_design_styles()
        self._connect_signals()
        
    def _setup_ui(self):
        """Configura la interfaz del diálogo."""
        # Configuración del diálogo
        self.setWindowTitle("Configurar Análisis de Duplicados Similares")
        self.setModal(True)  # Bloqueante
        self.setFixedWidth(600)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | 
                           Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # --- SECCIÓN 1: Texto introductorio ---
        intro_label = QLabel(
            "Ajusta la sensibilidad del análisis de similitud\n"
            "para detectar imágenes parecidas:"
        )
        intro_label.setObjectName("intro_text")
        intro_label.setWordWrap(True)
        main_layout.addWidget(intro_label)
        
        # --- SECCIÓN 2: Card de configuración del slider ---
        config_card = self._create_slider_card()
        main_layout.addWidget(config_card)
        
        # --- SECCIÓN 3: Información "¿Qué significa esto?" ---
        info_section = self._create_info_section()
        main_layout.addWidget(info_section)
        
        # --- SEPARADOR ---
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setObjectName("separator")
        main_layout.addWidget(separator1)
        
        # --- SECCIÓN 4: Tiempo estimado ---
        time_label = self._create_time_estimate_label()
        main_layout.addWidget(time_label)
        
        # --- SECCIÓN 5: Advertencia de modo bloqueante ---
        warning_label = self._create_warning_label()
        main_layout.addWidget(warning_label)
        
        # --- SEPARADOR ---
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setObjectName("separator")
        main_layout.addWidget(separator2)
        
        # --- SECCIÓN 6: Botones de acción ---
        buttons_layout = self._create_buttons()
        main_layout.addLayout(buttons_layout)
        
    def _create_slider_card(self) -> QFrame:
        """Crea la card interna con el slider de sensibilidad."""
        card = QFrame()
        card.setObjectName("slider_card")
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(16)
        card_layout.setContentsMargins(20, 20, 20, 20)
        
        # Título de la card
        title = QLabel("Sensibilidad de detección")
        title.setObjectName("card_title")
        card_layout.addWidget(title)
        
        # Slider horizontal
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setMinimum(30)
        self.sensitivity_slider.setMaximum(100)
        self.sensitivity_slider.setValue(self.sensitivity_value)
        self.sensitivity_slider.setTickInterval(5)
        self.sensitivity_slider.setSingleStep(5)
        self.sensitivity_slider.setPageStep(10)
        self.sensitivity_slider.setObjectName("sensitivity_slider")
        card_layout.addWidget(self.sensitivity_slider)
        
        # Labels del slider (min, center, max)
        labels_layout = QHBoxLayout()
        labels_layout.setSpacing(0)
        
        min_label = QLabel("Menos estricto\n30%")
        min_label.setObjectName("slider_label")
        min_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        max_label = QLabel("Más estricto\n100%")
        max_label.setObjectName("slider_label")
        max_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        labels_layout.addWidget(min_label)
        labels_layout.addStretch()
        labels_layout.addWidget(max_label)
        card_layout.addLayout(labels_layout)
        
        # Display del valor actual (actualización dinámica)
        value_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(get_icon("target", 16, "#1976D2").pixmap(16, 16))
        
        self.value_display = QLabel(f"Valor seleccionado: {self.sensitivity_value}%")
        self.value_display.setObjectName("value_display")
        
        value_layout.addWidget(icon_label)
        value_layout.addWidget(self.value_display)
        value_layout.addStretch()
        
        card_layout.addLayout(value_layout)
        
        return card
        
    def _create_info_section(self) -> QFrame:
        """Crea la sección informativa "¿Qué significa esto?"."""
        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Título con icono
        title_layout = QHBoxLayout()
        info_icon = QLabel()
        info_icon.setPixmap(get_icon("information", 18, "#1976D2").pixmap(18, 18))
        
        title = QLabel("¿Qué significa esto?")
        title.setObjectName("info_title")
        
        title_layout.addWidget(info_icon)
        title_layout.addWidget(title)
        title_layout.addStretch()
        info_layout.addLayout(title_layout)
        
        # Lista de explicaciones
        explanations = [
            "• 30-60%: Detecta solo imágenes muy similares\n"
            "  (mismo objeto, ángulos ligeramente diferentes)",
            
            "• 60-85%: Balance recomendado (predeterminado)\n"
            "  Detecta recortes, rotaciones, ajustes",
            
            "• 85-100%: Detecta similitudes más amplias\n"
            "  (misma escena, objetos o sujetos parecidos)"
        ]
        
        for explanation in explanations:
            label = QLabel(explanation)
            label.setObjectName("explanation_text")
            label.setWordWrap(True)
            info_layout.addWidget(label)
        
        return info_frame
        
    def _create_time_estimate_label(self) -> QFrame:
        """Crea el label con tiempo estimado."""
        container = QFrame()
        container.setObjectName("time_container")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        icon = QLabel()
        icon.setPixmap(get_icon("clock-outline", 16, "#757575").pixmap(16, 16))
        
        # Calcular tiempo estimado basado en file_count
        estimated_minutes = max(2, self.file_count // 1000)
        time_text = QLabel(f"Tiempo estimado: ~{estimated_minutes}-{estimated_minutes+2} min ({self.file_count:,} archivos)")
        time_text.setObjectName("time_text")
        
        layout.addWidget(icon)
        layout.addWidget(time_text)
        layout.addStretch()
        
        return container
        
    def _create_warning_label(self) -> QFrame:
        """Crea el label de advertencia de modo bloqueante."""
        container = QFrame()
        container.setObjectName("warning_container")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        icon = QLabel()
        icon.setPixmap(get_icon("alert-circle-outline", 16, "#FF9800").pixmap(16, 16))
        
        warning_text = QLabel(
            "El análisis se ejecutará en modo bloqueante.\n"
            "No podrás usar la aplicación hasta que termine."
        )
        warning_text.setObjectName("warning_text")
        warning_text.setWordWrap(True)
        
        layout.addWidget(icon)
        layout.addWidget(warning_text)
        
        return container
        
    def _create_buttons(self) -> QHBoxLayout:
        """Crea los botones de acción Material Design."""
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        # Botón Cancelar (secundario)
        cancel_button = QPushButton("Cancelar")
        cancel_button.setObjectName("cancel_button")
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)
        
        # Botón Iniciar análisis (primario)
        start_button = QPushButton()
        start_button.setText("Iniciar análisis")
        start_button.setIcon(get_icon("play-circle", 16, "#FFFFFF"))
        start_button.setObjectName("start_button")
        start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        start_button.clicked.connect(self.accept)
        
        buttons_layout.addWidget(cancel_button)
        buttons_layout.addWidget(start_button)
        
        return buttons_layout
        
    def _connect_signals(self):
        """Conecta las señales del slider."""
        self.sensitivity_slider.valueChanged.connect(self._on_slider_changed)
        
    def _on_slider_changed(self, value: int):
        """Actualiza el display cuando el slider cambia."""
        self.sensitivity_value = value
        self.value_display.setText(f"Valor seleccionado: {value}%")
        
    def get_sensitivity_value(self) -> int:
        """Retorna el valor de sensibilidad seleccionado."""
        return self.sensitivity_value
        
    def _apply_material_design_styles(self):
        """Aplica estilos Material Design 3 al diálogo."""
        self.setStyleSheet("""
            /* Diálogo principal */
            QDialog {
                background-color: #FFFFFF;
                border-radius: 28px;
            }
            
            /* Texto introductorio */
            QLabel#intro_text {
                font-size: 14px;
                color: #212121;
                line-height: 1.5;
            }
            
            /* Card del slider */
            QFrame#slider_card {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 16px;
            }
            
            QLabel#card_title {
                font-size: 15px;
                font-weight: 600;
                color: #212121;
            }
            
            /* Slider Material Design 3 */
            QSlider#sensitivity_slider {
                height: 24px;
            }
            
            QSlider#sensitivity_slider::groove:horizontal {
                background: #E0E0E0;
                height: 4px;
                border-radius: 2px;
            }
            
            QSlider#sensitivity_slider::handle:horizontal {
                background: #1976D2;
                width: 20px;
                height: 20px;
                margin: -8px 0;
                border-radius: 10px;
                border: 2px solid #FFFFFF;
            }
            
            QSlider#sensitivity_slider::handle:horizontal:hover {
                background: #1565C0;
                width: 24px;
                height: 24px;
                margin: -10px 0;
                border-radius: 12px;
            }
            
            QSlider#sensitivity_slider::sub-page:horizontal {
                background: #1976D2;
                border-radius: 2px;
            }
            
            /* Labels del slider */
            QLabel#slider_label {
                font-size: 12px;
                color: #757575;
                line-height: 1.3;
            }
            
            /* Display del valor */
            QLabel#value_display {
                font-size: 14px;
                font-weight: 600;
                color: #1976D2;
            }
            
            /* Sección informativa */
            QLabel#info_title {
                font-size: 14px;
                font-weight: 600;
                color: #212121;
            }
            
            QLabel#explanation_text {
                font-size: 13px;
                color: #757575;
                line-height: 1.5;
            }
            
            /* Separadores */
            QFrame#separator {
                background-color: #E0E0E0;
                max-height: 1px;
            }
            
            /* Tiempo estimado */
            QFrame#time_container {
                background-color: rgba(240, 240, 240, 0.5);
                border-radius: 8px;
            }
            
            QLabel#time_text {
                font-size: 13px;
                color: #212121;
            }
            
            /* Advertencia */
            QFrame#warning_container {
                background-color: rgba(255, 152, 0, 0.08);
                border-radius: 8px;
                border: 1px solid rgba(255, 152, 0, 0.2);
            }
            
            QLabel#warning_text {
                font-size: 13px;
                color: #757575;
                line-height: 1.4;
            }
            
            /* Botones Material Design 3 */
            QPushButton#cancel_button {
                background-color: transparent;
                color: #1976D2;
                font-size: 14px;
                font-weight: 500;
                padding: 10px 24px;
                border: none;
                border-radius: 20px;
                min-width: 100px;
            }
            
            QPushButton#cancel_button:hover {
                background-color: rgba(25, 118, 210, 0.08);
            }
            
            QPushButton#cancel_button:pressed {
                background-color: rgba(25, 118, 210, 0.16);
            }
            
            QPushButton#start_button {
                background-color: #1976D2;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 500;
                padding: 10px 24px;
                border: none;
                border-radius: 20px;
                min-width: 140px;
            }
            
            QPushButton#start_button:hover {
                background-color: #1565C0;
            }
            
            QPushButton#start_button:pressed {
                background-color: #0D47A1;
            }
        """)
```

**Accesibilidad (ARIA/WAI)**:[^10][^11]

- El diálogo captura el foco automáticamente al abrirse
- Tab/Shift+Tab navegan entre slider y botones
- Escape cierra el diálogo (igual que "Cancelar")
- Enter desde el slider ejecuta "Iniciar análisis"
- El slider tiene incrementos claros (5%)

***

## PARTE 3: Diálogo de Progreso Bloqueante (Material Design 3)

### Archivo Nuevo: `ui/dialogs/similarityprogressdialog.py`

**Propósito**: Diálogo **modal bloqueante** que muestra el progreso del análisis en tiempo real.[^2][^5][^1]

**Layout visual completo**:

```
╔═══════════════════════════════════════════════╗
║  Analizando Duplicados Similares         [×] ║  ← Header MD3
╠═══════════════════════════════════════════════╣
║                                               ║
║  ⟳  Detectando imágenes similares...         ║  ← Spinner + estado
║                                               ║
║  ━━━━━━━━━━━━━━━━━━━━━━━░░░░░░░  68%        ║  ← Progress bar MD3
║                                               ║
║  📊 1,938 de 2,847 archivos procesados       ║  ← Estadísticas
║                                               ║
║  ⏱️  Tiempo transcurrido: 2m 15s             ║  ← Tiempos
║  ⏱️  Tiempo estimado restante: ~1m 30s       ║
║                                               ║
║  ───────────────────────────────────────────  ║  ← Separador
║                                               ║
║  ℹ️  El análisis está en progreso. La        ║  ← Info
║     ventana se cerrará automáticamente al     ║
║     completarse.                              ║
║                                               ║
║                            [Cancelar análisis]║  ← Botón cancelar
╚═══════════════════════════════════════════════╝
```


### Especificaciones Técnicas del Diálogo de Progreso

**Dimensiones Material Design**:

- Ancho: 520px
- Alto: 380px (fijo)
- **Modal**: Sí, bloquea interacción completa[^3][^2][^1]
- **Centrado**: Sobre la ventana principal
- **Elevation**: 24dp
- **Border radius**: 28px (Material Design 3)
- **No se puede cerrar con [X]**: Solo con botón "Cancelar análisis"

**Estructura del código**:

```python
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QTime
from PyQt6.QtGui import QMovie
from utils.icons import get_icon
from utils.formatutils import format_file_count

class SimilarityProgressDialog(QDialog):
    """
    Diálogo Material Design 3 para mostrar progreso de análisis.
    Modal bloqueante con actualización en tiempo real.
    """
    
    cancel_requested = pyqtSignal()  # Señal para cancelar análisis
    
    def __init__(self, parent=None, total_files: int = 0):
        super().__init__(parent)
        self.total_files = total_files
        self.current_files = 0
        self.start_time = QTime.currentTime()
        self._setup_ui()
        self._apply_material_design_styles()
        self._start_timer()
        
    def _setup_ui(self):
        """Configura la interfaz del diálogo."""
        # Configuración del diálogo
        self.setWindowTitle("Analizando Duplicados Similares")
        self.setModal(True)  # Bloqueante total
        self.setFixedSize(520, 380)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | 
                           Qt.WindowType.WindowTitleHint)  # Sin botón [X]
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(32, 32, 32, 32)
        
        # --- SECCIÓN 1: Estado actual con spinner ---
        status_layout = QHBoxLayout()
        status_layout.setSpacing(12)
        
        # Spinner animado
        self.spinner_label = QLabel()
        self.spinner_movie = QMovie(get_icon_path("loading_spinner.gif"))  # Animated GIF
        self.spinner_label.setMovie(self.spinner_movie)
        self.spinner_movie.start()
        
        self.status_text = QLabel("Detectando imágenes similares...")
        self.status_text.setObjectName("status_text")
        
        status_layout.addWidget(self.spinner_label)
        status_layout.addWidget(self.status_text)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)
        
        # Espaciado
        main_layout.addSpacing(8)
        
        # --- SECCIÓN 2: Barra de progreso Material Design 3 ---
        progress_container = QFrame()
        progress_container.setObjectName("progress_container")
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)  # Texto separado
        self.progress_bar.setFixedHeight(8)
        
        # Porcentaje grande a la derecha
        self.percentage_label = QLabel("0%")
        self.percentage_label.setObjectName("percentage_label")
        self.percentage_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.percentage_label)
        
        main_layout.addWidget(progress_container)
        
        # --- SECCIÓN 3: Estadísticas en tiempo real ---
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(8)
        
        # Archivos procesados
        files_layout = QHBoxLayout()
        files_icon = QLabel()
        files_icon.setPixmap(get_icon("chart-bar", 16, "#757575").pixmap(16, 16))
        
        self.files_label = QLabel(f"0 de {self.total_files:,} archivos procesados")
        self.files_label.setObjectName("stats_text")
        
        files_layout.addWidget(files_icon)
        files_layout.addWidget(self.files_label)
        files_layout.addStretch()
        
        # Tiempo transcurrido
        elapsed_layout = QHBoxLayout()
        elapsed_icon = QLabel()
        elapsed_icon.setPixmap(get_icon("clock-outline", 16, "#757575").pixmap(16, 16))
        
        self.elapsed_label = QLabel("Tiempo transcurrido: 0s")
        self.elapsed_label.setObjectName("stats_text")
        
        elapsed_layout.addWidget(elapsed_icon)
        elapsed_layout.addWidget(self.elapsed_label)
        elapsed_layout.addStretch()
        
        # Tiempo estimado restante
        remaining_layout = QHBoxLayout()
        remaining_icon = QLabel()
        remaining_icon.setPixmap(get_icon("clock-fast", 16, "#757575").pixmap(16, 16))
        
        self.remaining_label = QLabel("Tiempo estimado restante: calculando...")
        self.remaining_label.setObjectName("stats_text")
        
        remaining_layout.addWidget(remaining_icon)
        remaining_layout.addWidget(self.remaining_label)
        remaining_layout.addStretch()
        
        stats_layout.addLayout(files_layout)
        stats_layout.addLayout(elapsed_layout)
        stats_layout.addLayout(remaining_layout)
        
        main_layout.addLayout(stats_layout)
        
        # --- SEPARADOR ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        main_layout.addWidget(separator)
        
        # --- SECCIÓN 4: Información ---
        info_container = QFrame()
        info_container.setObjectName("info_container")
        
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(8)
        
        info_icon = QLabel()
        info_icon.setPixmap(get_icon("information", 16, "#1976D2").pixmap(16, 16))
        
        info_text = QLabel(
            "El análisis está en progreso. La ventana se\n"
            "cerrará automáticamente al completarse."
        )
        info_text.setObjectName("info_text")
        info_text.setWordWrap(True)
        
        info_layout.addWidget(info_icon)
        info_layout.addWidget(info_text)
        
        main_layout.addWidget(info_container)
        
        # Espaciador
        main_layout.addStretch()
        
        # --- SECCIÓN 5: Botón cancelar ---
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancelar análisis")
        self.cancel_button.setIcon(get_icon("stop", 16, "#F44336"))
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        
        buttons_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(buttons_layout)
        
    def _start_timer(self):
        """Inicia el timer para actualizar tiempo transcurrido."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_elapsed_time)
        self.timer.start(1000)  # Actualizar cada segundo
        
    def _update_elapsed_time(self):
        """Actualiza el label de tiempo transcurrido."""
        elapsed_seconds = self.start_time.secsTo(QTime.currentTime())
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        
        if minutes > 0:
            self.elapsed_label.setText(f"Tiempo transcurrido: {minutes}m {seconds}s")
        else:
            self.elapsed_label.setText(f"Tiempo transcurrido: {seconds}s")
            
    def update_progress(self, current: int, total: int, percentage: int):
        """
        Actualiza el progreso del análisis.
        
        Args:
            current: Archivos procesados actualmente
            total: Total de archivos
            percentage: Porcentaje de progreso (0-100)
        """
        self.current_files = current
        self.progress_bar.setValue(percentage)
        self.percentage_label.setText(f"{percentage}%")
        self.files_label.setText(f"{current:,} de {total:,} archivos procesados")
        
        # Calcular tiempo estimado restante
        if percentage > 0:
            elapsed_seconds = self.start_time.secsTo(QTime.currentTime())
            total_estimated = int(elapsed_seconds / (percentage / 100))
            remaining_seconds = total_estimated - elapsed_seconds
            
            if remaining_seconds > 0:
                remaining_minutes = remaining_seconds // 60
                remaining_secs = remaining_seconds % 60
                
                if remaining_minutes > 0:
                    self.remaining_label.setText(
                        f"Tiempo estimado restante: ~{remaining_minutes}m {remaining_secs}s"
                    )
                else:
                    self.remaining_label.setText(
                        f"Tiempo estimado restante: ~{remaining_secs}s"
                    )
        
    def _on_cancel_clicked(self):
        """Maneja el clic en cancelar con confirmación."""
        current_percentage = self.progress_bar.value()
        
        # Mostrar diálogo de confirmación
        reply = QMessageBox.question(
            self,
            "¿Cancelar análisis?",
            f"Se perderá el progreso actual ({current_percentage}% completado).\n\n"
            "¿Estás seguro de que deseas cancelar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.cancel_requested.emit()
            self.reject()
            
    def _apply_material_design_styles(self):
        """Aplica estilos Material Design 3 al diálogo."""
        self.setStyleSheet("""
            /* Diálogo principal */
            QDialog {
                background-color: #FFFFFF;
                border-radius: 28px;
            }
            
            /* Texto de estado */
            QLabel#status_text {
                font-size: 16px;
                font-weight: 500;
                color: #212121;
            }
            
            /* Barra de progreso Material Design 3 */
            QProgressBar#progress_bar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 4px;
                text-align: center;
            }
            
            QProgressBar#progress_bar::chunk {
                background-color: #1976D2;
                border-radius: 4px;
            }
            
            /* Porcentaje */
            QLabel#percentage_label {
                font-size: 32px;
                font-weight: 700;
                color: #1976D2;
            }
            
            /* Textos de estadísticas */
            QLabel#stats_text {
                font-size: 13px;
                color: #757575;
            }
            
            /* Separador */
            QFrame#separator {
                background-color: #E0E0E0;
                max-height: 1px;
            }
            
            /* Información */
            QFrame#info_container {
                background-color: rgba(25, 118, 210, 0.08);
                border-radius: 8px;
            }
            
            QLabel#info_text {
                font-size: 13px;
                color: #757575;
                line-height: 1.4;
            }
            
            /* Botón cancelar */
            QPushButton#cancel_button {
                background-color: transparent;
                color: #F44336;
                font-size: 14px;
                font-weight: 500;
                padding: 10px 24px;
                border: 1px solid rgba(244, 67, 54, 0.3);
                border-radius: 20px;
                min-width: 140px;
            }
            
            QPushButton#cancel_button:hover {
                background-color: rgba(244, 67, 54, 0.08);
                border: 1px solid rgba(244, 67, 54, 0.5);
            }
            
            QPushButton#cancel_button:pressed {
                background-color: rgba(244, 67, 54, 0.16);
            }
        """)
```

**Nota importante**: Si no tienes un GIF animado para el spinner, puedes usar un `QLabel` con el icono `sync` y aplicar una animación de rotación con `QPropertyAnimation`:

```python
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QTransform

# En _setup_ui, reemplazar el spinner por:
self.spinner_label = QLabel()
self.spinner_label.setPixmap(get_icon("sync", 24, "#1976D2").pixmap(24, 24))

# Crear animación de rotación
self.rotation_animation = QPropertyAnimation(self.spinner_label, b"rotation")
self.rotation_animation.setDuration(1000)  # 1 segundo por rotación
self.rotation_animation.setStartValue(0)
self.rotation_animation.setEndValue(360)
self.rotation_animation.setEasingCurve(QEasingCurve.Type.Linear)
self.rotation_animation.setLoopCount(-1)  # Infinito
self.rotation_animation.start()
```


***

## PARTE 4: Integración en Stage 3

### Modificaciones en `ui/stages/stage3window.py`

**Añadir los siguientes métodos**:

```python
from ui.dialogs.similarityconfigdialog import SimilarityConfigDialog
from ui.dialogs.similarityprogressdialog import SimilarityProgressDialog
from services.duplicatesimilardetector import DuplicateSimilarDetector
from PyQt6.QtCore import QThread, pyqtSignal

class SimilarityAnalysisWorker(QThread):
    """Worker thread para análisis de duplicados similares."""
    
    progress_updated = pyqtSignal(int, int, int)  # current, total, percentage
    analysis_completed = pyqtSignal(object)  # results
    analysis_error = pyqtSignal(str)  # error_message
    
    def __init__(self, workspace_path: str, sensitivity: int):
        super().__init__()
        self.workspace_path = workspace_path
        self.sensitivity = sensitivity
        self._is_cancelled = False
        
    def run(self):
        """Ejecuta el análisis en background."""
        try:
            detector = DuplicateSimilarDetector()
            
            def progress_callback(current, total):
                if self._is_cancelled:
                    raise InterruptedError("Análisis cancelado por el usuario")
                percentage = int((current / total) * 100)
                self.progress_updated.emit(current, total, percentage)
            
            results = detector.find_similar_duplicates(
                self.workspace_path,
                sensitivity=self.sensitivity,
                progress_callback=progress_callback
            )
            
            self.analysis_completed.emit(results)
            
        except InterruptedError:
            pass  # Cancelación controlada
        except Exception as e:
            self.analysis_error.emit(str(e))
            
    def cancel(self):
        """Cancela el análisis en curso."""
        self._is_cancelled = True


class Stage3Window(QWidget):
    """Ventana del Stage 3 con las 6 herramientas."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.similarity_results = None
        self.similarity_worker = None
        self.progress_dialog = None
        # ... resto de inicialización
        
    def _on_similar_duplicates_clicked(self):
        """Maneja el clic en la card de duplicados similares."""
        # Obtener file count del análisis previo
        file_count = self.analysis_results.get("total_files", 0)
        
        # Abrir diálogo de configuración
        config_dialog = SimilarityConfigDialog(
            self,
            file_count=file_count,
            previous_sensitivity=self.similarity_results.sensitivity if self.similarity_results else 85
        )
        
        result = config_dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            sensitivity = config_dialog.get_sensitivity_value()
            self._start_similarity_analysis(sensitivity, file_count)
            
    def _start_similarity_analysis(self, sensitivity: int, file_count: int):
        """Inicia el análisis de duplicados similares."""
        # Crear worker thread
        self.similarity_worker = SimilarityAnalysisWorker(
            self.current_workspace_path,
            sensitivity
        )
        
        # Crear diálogo de progreso (modal bloqueante)
        self.progress_dialog = SimilarityProgressDialog(self, total_files=file_count)
        
        # Conectar señales
        self.similarity_worker.progress_updated.connect(
            self.progress_dialog.update_progress
        )
        self.similarity_worker.analysis_completed.connect(
            self._on_similarity_analysis_completed
        )
        self.similarity_worker.analysis_error.connect(
            self._on_similarity_analysis_error
        )
        self.progress_dialog.cancel_requested.connect(
            self._on_similarity_analysis_cancelled
        )
        
        # Iniciar thread
        self.similarity_worker.start()
        
        # Mostrar diálogo (bloqueante hasta que termine o se cancele)
        self.progress_dialog.exec()
        
    def _on_similarity_analysis_completed(self, results):
        """Maneja la finalización exitosa del análisis."""
        # Almacenar resultados
        self.similarity_results = results
        
        # Cerrar diálogo de progreso
        if self.progress_dialog:
            self.progress_dialog.accept()
            self.progress_dialog = None
            
        # Actualizar la card
        self._update_similar_duplicates_card(results)
        
        # Mostrar mensaje de éxito
        QMessageBox.information(
            self,
            "Análisis completado",
            f"✓ Se detectaron {results.group_count} grupos de imágenes similares.\n\n"
            f"Espacio recuperable: {format_size(results.recoverable_space)}",
            QMessageBox.StandardButton.Ok
        )
        
    def _on_similarity_analysis_error(self, error_message: str):
        """Maneja errores durante el análisis."""
        # Cerrar diálogo de progreso
        if self.progress_dialog:
            self.progress_dialog.reject()
            self.progress_dialog = None
            
        # Mostrar error
        QMessageBox.critical(
            self,
            "Error en el análisis",
            f"Se produjo un error durante el análisis:\n\n{error_message}",
            QMessageBox.StandardButton.Ok
        )
        
    def _on_similarity_analysis_cancelled(self):
        """Maneja la cancelación del análisis por el usuario."""
        if self.similarity_worker:
            self.similarity_worker.cancel()
            self.similarity_worker.wait()  # Esperar a que termine
            
    def _update_similar_duplicates_card(self, results):
        """Actualiza la card con los resultados del análisis."""
        card = self.tool_cards["similar_duplicates"]
        
        # Cambiar a estado "listo"
        card.set_status_ready()
        
        # Actualizar información
        card.set_info_lines([
            (f"✓ {results.group_count} grupos detectados", "check-circle", "#4CAF50"),
            (f"💾 {format_size(results.recoverable_space)} recuperables", "harddisk", "#757575"),
            (f"🔄 Sensibilidad usada: {results.sensitivity}%", "tune", "#757575")
        ])
        
        # Añadir link de reconfiguración
        card.add_action_link("Reconfigurar...", self._on_reconfigure_similarity)
        
        # Cambiar botón a "Gestionar ahora"
        card.set_button_text("Gestionar ahora")
        card.set_button_style("primary")
        card.set_button_callback(lambda: self._open_similarity_dialog(results))
        
    def _on_reconfigure_similarity(self):
        """Permite reconfigurar y reanalizar."""
        # Volver a abrir el diálogo de configuración
        self._on_similar_duplicates_clicked()
        
    def _open_similarity_dialog(self, results):
        """Abre el diálogo de gestión de duplicados similares."""
        from ui.dialogs.similardialog import SimilarDialog
        
        dialog = SimilarDialog(self, results)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Re-analizar workspace si se ejecutaron acciones
            self._trigger_workspace_reanalysis()
```


***

## PARTE 5: Validación y Testing

### Casos de Prueba

1. **Flujo completo exitoso**:
    - Abrir Stage 3
    - Clic en card "Duplicados Similares"
    - Ajustar slider a 70%
    - Iniciar análisis
    - Ver progreso hasta 100%
    - Verificar que la card se actualiza correctamente
    - Abrir "Gestionar ahora" y verificar resultados
2. **Cancelación durante el análisis**:
    - Iniciar análisis
    - A mitad del progreso (50%), hacer clic en "Cancelar análisis"
    - Confirmar cancelación
    - Verificar que el worker se detiene
    - Verificar que la card permanece en estado "Requiere configuración"
3. **Reconfiguración**:
    - Después de un análisis exitoso con sensibilidad 85%
    - Clic en "Reconfigurar..."
    - Cambiar a 95%
    - Iniciar análisis
    - Verificar que los nuevos resultados reemplazan a los anteriores
4. **Error en el análisis**:
    - Simular un error en `DuplicateSimilarDetector`
    - Verificar que se muestra el diálogo de error
    - Verificar que la card no cambia de estado

### Accesibilidad

- Verificar navegación con Tab en ambos diálogos
- Verificar que Escape cierra el diálogo de configuración
- Verificar que Enter desde el slider inicia el análisis
- Verificar que los diálogos tienen títulos y roles ARIA correctos

***

## PARTE 6: Resumen de Archivos a Modificar/Crear

### Archivos Nuevos

1. **`ui/dialogs/similarityconfigdialog.py`** (completo arriba)
2. **`ui/dialogs/similarityprogressdialog.py`** (completo arriba)

### Archivos a Modificar

1. **`ui/stages/stage3window.py`**:
    - Añadir import de los nuevos diálogos
    - Añadir clase `SimilarityAnalysisWorker`
    - Añadir métodos listados en PARTE 4
    - Conectar señal de clic de la card de similares
2. **`ui/widgets/toolcard.py`** (si existe):
    - Añadir método `add_action_link(text, callback)`
    - Añadir método `set_info_lines(lines)`
    - Añadir método `set_status_ready()`
3. **`services/duplicatesimilardetector.py`**:
    - Verificar que `find_similar_duplicates()` acepta `progress_callback`
    - Asegurar que retorna objeto con atributos:
        - `group_count: int`
        - `recoverable_space: int`
        - `sensitivity: int`
        - `groups: List[SimilarGroup]`

***

## PARTE 7: Notas Finales de Implementación

### Consideraciones

1. **Threading seguro**: El worker debe ser PyQt-free en su lógica interna[^8]
2. **Cancelación limpia**: El worker debe verificar `_is_cancelled` periódicamente
3. **Memoria**: Liberar recursos al cerrar diálogos
4. **Consistencia**: Todos los textos en español
5. **Material Design 3**: Seguir especificaciones de elevation, border-radius, colores[^2][^6][^1]

### Ventajas del Diseño Bloqueante

- **Enfoque claro**: El usuario no se pierde entre múltiples tareas[^4][^3]
- **Expectativa cumplida**: Los análisis costosos suelen ser bloqueantes en aplicaciones profesionales[^5]
- **Feedback directo**: Progreso visible y resultados inmediatos[^1][^2]
- **Simplicidad**: Menos estados y condiciones de carrera que gestionar
- **UX tradicional**: Patrón familiar para los usuarios[^3][^4]


### Material Design 3 Aplicado

- **Elevaciones correctas**: 24dp para diálogos modales[^2][^1]
- **Border radius**: 28px para diálogos principales, 20px para botones[^1]
- **Colores semánticos**: Primary (\#1976D2), Error (\#F44336), Success (\#4CAF50)[^2]
- **Tipografía jerárquica**: Tamaños y pesos claramente diferenciados
- **Espaciado consistente**: 16px-24px entre secciones
- **Progress bar moderno**: 4-8px de altura, bordes redondeados, gap visual[^7]
- **Botones con estados**: Hover y pressed claramente diferenciados[^1]
