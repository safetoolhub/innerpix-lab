"""Controlador de pestañas: encapsula la creación, navegación y la
disponibilidad de pestañas para separar esa responsabilidad de
`MainWindow`.

Este módulo centraliza:
- creación del widget de pestañas
- mapeo de índices
- estado `tab_availability` centralizado en la propia instancia de
    `TabController` (no se inyecta en `window`)
- lógica de actualización de disponibilidad basada en resultados
"""
from typing import Dict

from ui import tabs as tabs_module
from utils.logger import get_logger


class TabController:
    def __init__(self, window):
        self.window = window
        self.logger = get_logger('TabController')
        # Fuente única de verdad para la disponibilidad de características.
        # Inicializamos con los valores por defecto (habilitado)
        self.tab_availability: Dict[str, bool] = {
            'live_photos': True,
            'heic': True,
            'organization': True,
            'renaming': True,
            'duplicates': True,
        }

    # Nota: ya no inyectamos `tab_availability` en `window`.
    # El código debe consultar `window.tab_controller.tab_availability`.

        self.tabs_widget = None

    def create_tabs_widget(self):
        """Crea y devuelve el widget de pestañas, delegando en `ui.tabs`.

        Guarda la referencia en el controlador para posteriores operaciones.
        """
        self.tabs_widget = tabs_module.create_tabs_widget(self.window)
        # Asegurar que window tenga referencia directa como antes
        setattr(self.window, 'tabs_widget', self.tabs_widget)
        return self.tabs_widget

    def open_summary_action(self, label_substr: str):
        """Navega a la pestaña asociada con la acción del summary panel."""
        return tabs_module.open_summary_action(self.window, label_substr)

    def update_tabs_availability(self, results: dict):
        """Actualizar la disponibilidad de pestañas según `results`.

        Actualmente aplica reglas sencillas y delega en `ui.tabs.update_tabs_availability`
        para aplicar el estado sobre el widget.
        """
        self.logger.debug("Actualizando disponibilidad de pestañas")
        
        # Si no hay live_photos, deshabilitar esa pestaña
        lp_groups = results.get('live_photos', {}).get('groups') or []
        self.tab_availability['live_photos'] = len(lp_groups) > 0
        self.logger.debug(f"Live Photos: {len(lp_groups)} grupos - {'habilitado' if self.tab_availability['live_photos'] else 'deshabilitado'}")

        # Si no hay duplicados HEIC detectados, deshabilitar pestaña
        heic_dups = results.get('heic', {}).get('total_duplicates', 0)
        self.tab_availability['heic'] = heic_dups > 0
        self.logger.debug(f"HEIC: {heic_dups} duplicados - {'habilitado' if self.tab_availability['heic'] else 'deshabilitado'}")

        # Organización: habilitar solo si hay archivos a mover
        org_count = results.get('organization', {}).get('total_files_to_move', 0)
        self.tab_availability['organization'] = org_count > 0
        self.logger.debug(f"Organización: {org_count} archivos - {'habilitado' if self.tab_availability['organization'] else 'deshabilitado'}")

        # Renaming: habilitar si hay necesidades de renombrado
        need_renaming = results.get('renaming', {}).get('need_renaming', 0)
        self.tab_availability['renaming'] = need_renaming > 0
        self.logger.debug(f"Renombrado: {need_renaming} archivos - {'habilitado' if self.tab_availability['renaming'] else 'deshabilitado'}")

        # Duplicates tab: habilitar si hay grupos detectados
        dup_groups = results.get('duplicates', {}).get('total_groups', 0)
        self.tab_availability['duplicates'] = dup_groups > 0
        self.logger.debug(f"Duplicados: {dup_groups} grupos - {'habilitado' if self.tab_availability['duplicates'] else 'deshabilitado'}")

        # Aplicar los cambios en el widget
        tabs_module.update_tabs_availability(self.window, results)

