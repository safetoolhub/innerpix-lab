from pathlib import Path

from PyQt5.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt

from ui import styles


class ActionButtons:
    """Contenedor que agrupa los botones de acción que reemplazan al
    `analyze_btn` tras completarse un análisis.

    Esta clase crea un `QFrame` con un `QHBoxLayout` y añade los botones:
    - usa el `analyze_btn` ya creado por `SearchBar` (se lo pasa en runtime)
    - crea `reanalyze_btn` y `change_dir_btn`

    Para compatibilidad con el código existente de `MainWindow`, la
    instancia registra los widgets relevantes directamente en el padre
    (por ejemplo `parent.reanalyze_btn`).
    """

    def __init__(self, parent, search_bar):
        self.parent = parent
        self.search_bar = search_bar

        # Crear contenedor transparente para alojar los botones
        self.container = QFrame(parent)
        self.container.setFrameStyle(QFrame.NoFrame)
        self.container.setStyleSheet(styles.STYLE_ACTIONS_CONTAINER)
        self.container.setAttribute(Qt.WA_TranslucentBackground)

        self.layout = QHBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Reusar el analyze_btn creado por el SearchBar
        self.analyze_btn = getattr(search_bar, "analyze_btn", None)
        if self.analyze_btn is not None:
            # Mover el botón existente al nuevo contenedor
            self.layout.addWidget(self.analyze_btn)

        # Botones alternativos que aparecerán tras el análisis
        self.reanalyze_btn = QPushButton("🔄 Re-analizar", parent)
        self.reanalyze_btn.setVisible(False)
        self.reanalyze_btn.setMinimumWidth(200)
        self.reanalyze_btn.setFixedHeight(42)
        self.reanalyze_btn.setCursor(Qt.PointingHandCursor)
        if self.analyze_btn is not None:
            self.reanalyze_btn.setStyleSheet(self.analyze_btn.styleSheet())
        self.reanalyze_btn.clicked.connect(parent._reanalyze_same_directory)

        self.change_dir_btn = QPushButton("📂 Cambiar directorio", parent)
        self.change_dir_btn.setVisible(False)
        self.change_dir_btn.setMinimumWidth(200)
        self.change_dir_btn.setFixedHeight(42)
        self.change_dir_btn.setCursor(Qt.PointingHandCursor)
        if self.analyze_btn is not None:
            self.change_dir_btn.setStyleSheet(self.analyze_btn.styleSheet())
        self.change_dir_btn.clicked.connect(parent._change_directory_after_analysis)

        # Añadir los botones al layout
        self.layout.addWidget(self.reanalyze_btn)
        self.layout.addWidget(self.change_dir_btn)

        # Inyectar el contenedor dentro del SearchBar
        search_bar.add_actions_widget(self.container)

        # Exponer atributos en el parent para mantener compatibilidad
        # con el código existente en MainWindow
        parent.actions_container = self.container
        parent.actions_layout = self.layout
        # `analyze_btn` ya proviene del search_bar
        if self.analyze_btn is not None:
            parent.analyze_btn = self.analyze_btn
        parent.reanalyze_btn = self.reanalyze_btn
        parent.change_dir_btn = self.change_dir_btn

    # Métodos de utilidad para manipular visibilidad desde otros módulos
    def show_alternatives(self):
        self.reanalyze_btn.setVisible(True)
        self.change_dir_btn.setVisible(True)

    def hide_alternatives(self):
        self.reanalyze_btn.setVisible(False)
        self.change_dir_btn.setVisible(False)

    # Flujo / helpers para la gestión de visibilidad usada por MainWindow
    def after_analysis(self):
        """Acciones visuales a realizar cuando termina un análisis.

        - Cambia el texto del `analyze_btn` a 'Re-analizar'
        - Intenta quitar el `analyze_btn` del layout para que no ocupe espacio
        - Muestra y habilita los botones alternativos
        """
        try:
            if self.analyze_btn is not None:
                self.analyze_btn.setText("🔄 Re-analizar")
                try:
                    # intentar quitar del layout para dejar sitio a los alternativos
                    self.analyze_btn.setParent(None)
                except Exception:
                    self.analyze_btn.setVisible(False)
        except Exception:
            pass

        self.reanalyze_btn.setVisible(True)
        self.change_dir_btn.setVisible(True)
        self.reanalyze_btn.setEnabled(True)
        self.change_dir_btn.setEnabled(True)

    def before_reanalyze(self):
        """Estado antes de reiniciar el análisis en el mismo directorio.

        Mantiene visibles las alternativas pero deshabilitadas para evitar
        que el `analyze_btn` reaparezca temporalmente.
        """
        self.reanalyze_btn.setVisible(True)
        self.change_dir_btn.setVisible(True)
        self.reanalyze_btn.setEnabled(False)
        self.change_dir_btn.setEnabled(False)

    def hide_alternatives_and_enable_analyze(self):
        """Oculta los botones alternativos y vuelve a habilitar el analyze_btn."""
        self.reanalyze_btn.setVisible(False)
        self.change_dir_btn.setVisible(False)
        if self.analyze_btn is not None:
            self.analyze_btn.setEnabled(True)

    def show_alternatives_disabled(self):
        """Muestra las alternativas pero las deja deshabilitadas.

        Útil cuando se inicia un nuevo análisis automáticamente tras cambiar
        el directorio.
        """
        self.reanalyze_btn.setVisible(True)
        self.change_dir_btn.setVisible(True)
        self.reanalyze_btn.setEnabled(False)
        self.change_dir_btn.setEnabled(False)

    def update_after_analysis(self, results):
        """Actualiza el estado visual tras completarse un análisis.

        Encapsula:
        - acciones visuales generales (texto/retirada de analyze_btn)
        - habilitación/deshabilitación de botones según los `results`
        """
        # 1) comportamiento visual general
        self.after_analysis()

        # 2) habilitar/deshabilitar botones principales según resultados
        parent = self.parent

        # Preview rename
        if results.get('renaming') and results['renaming'].get('need_renaming', 0) > 0:
            parent.preview_rename_btn.setEnabled(True)
        else:
            parent.preview_rename_btn.setEnabled(False)

        # Live Photos
        if results.get('live_photos') and len(results['live_photos'].get('groups', [])) > 0:
            parent.exec_lp_btn.setEnabled(True)
        else:
            parent.exec_lp_btn.setEnabled(False)

        # Organización de archivos
        if results.get('organization') and results['organization'].get('total_files_to_move', 0) > 0:
            parent.exec_org_btn.setEnabled(True)
        else:
            parent.exec_org_btn.setEnabled(False)

        # HEIC duplicates
        if results.get('heic') and results['heic'].get('total_duplicates', 0) > 0:
            parent.exec_heic_btn.setEnabled(True)
        else:
            parent.exec_heic_btn.setEnabled(False)

