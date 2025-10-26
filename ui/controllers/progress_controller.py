from PyQt5.QtCore import QTimer


class ProgressController:
    """Controlador independiente de la UI de progreso.

    Ahora usa el área de progreso integrada en el SummaryPanel para
    evitar desplazamientos verticales del interfaz.

    Métodos públicos:
    - show_progress(maximum, message)
    - hide_progress()
    - update_progress(current, total, message)
    """

    def __init__(self, parent):
        """Inicializa el controlador usando los widgets del summary panel.

        Args:
            parent: MainWindow que debe tener los atributos:
                - summary_progress_area
                - summary_progress_label
                - summary_progress_bar
                - summary_progress_detail
        """
        self.parent = parent
        # Referencias a los widgets creados en SummaryPanel
        self.label = getattr(parent, 'summary_progress_label', None)
        self.bar = getattr(parent, 'summary_progress_bar', None)
        self.detail = getattr(parent, 'summary_progress_detail', None)

    def show_progress(self, maximum, message="Procesando"):
        """Muestra el área de progreso en el panel de resumen.

        - Si maximum > 0: se establece en modo determinate con ese máximo.
        - Si maximum <= 0 o None: se pone en modo indeterminado (busy).
        """
        if self.label:
            self.label.setVisible(True)
            self.label.setText(f"⏳ {message}")

        if self.bar:
            self.bar.setVisible(True)
            if maximum and maximum > 0:
                self.bar.setMaximum(maximum)
                self.bar.setValue(0)
            else:
                # Modo indeterminado
                self.bar.setMaximum(0)

        if self.detail:
            self.detail.setVisible(True)
            self.detail.setText("")

    def hide_progress(self):
        """Oculta el contenido del área de progreso con un pequeño retraso."""

        def _hide():
            if self.bar:
                self.bar.setMaximum(100)
                self.bar.setValue(0)
                self.bar.setVisible(False)
            if self.label:
                self.label.setText("✅ Listo")
                self.label.setVisible(False)
            if self.detail:
                self.detail.setText("")
                self.detail.setVisible(False)

        QTimer.singleShot(1000, _hide)

    def update_progress(self, current: int, total: int, message: str = None):
        """Actualiza el estado de la barra y la etiqueta.

        Si total>0 se muestra progreso determinístico; si no, se mantiene
        en modo indeterminado. message es opcional.
        """
        if self.bar and total and total > 0:
            self.bar.setMaximum(total)
            self.bar.setValue(min(current, total))
        elif self.bar:
            self.bar.setMaximum(0)

        if message is not None and self.label:
            # Añadir emoji de procesamiento si no lo tiene
            if not message.startswith('⏳') and not message.startswith('📂') and not message.startswith('📝') and not message.startswith('📱') and not message.startswith('📁') and not message.startswith('🖼️'):
                self.label.setText(f"⏳ {message}")
            else:
                self.label.setText(message)

        # Mostrar detalles adicionales si hay progreso numérico
        if self.detail and total and total > 0:
            percentage = int((current / total) * 100) if total > 0 else 0
            self.detail.setText(f"📊 {current:,} / {total:,} ({percentage}%)")

