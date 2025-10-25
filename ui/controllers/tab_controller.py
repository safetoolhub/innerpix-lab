"""Controlador de pestañas: encapsula la creación, navegación y la
disponibilidad de pestañas para separar esa responsabilidad de
`MainWindow`.

Este módulo centraliza:
- creación del widget de pestañas
- mapeo de índices
- estado `tab_availability` expuesto en `window` para compatibilidad
- lógica de actualización de disponibilidad basada en resultados
"""
from typing import Dict

from ui import tabs as tabs_module


class TabController:
    def __init__(self, window):
        self.window = window
        # Fuente única de verdad para la disponibilidad de características.
        # Inicializamos con los valores por defecto (habilitado)
        self.tab_availability: Dict[str, bool] = {
            'live_photos': True,
            'heic': True,
            'unification': True,
            'renaming': True,
            'duplicates': True,
        }

        # Mantener compatibilidad con código que consulta `window.tab_availability`
        setattr(self.window, 'tab_availability', self.tab_availability)

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
        # Aquí se pueden implementar reglas más complejas. Ejemplos simples:
        try:
            # Si no hay live_photos, deshabilitar esa pestaña
            lp_groups = results.get('live_photos', {}).get('groups') or []
            self.tab_availability['live_photos'] = len(lp_groups) > 0

            # Si no hay duplicados HEIC detectados, deshabilitar pestaña
            heic_dups = results.get('heic', {}).get('total_duplicates', 0)
            self.tab_availability['heic'] = heic_dups > 0

            # Unification: habilitar solo si hay archivos a mover
            unif_count = results.get('unification', {}).get('total_files_to_move', 0)
            self.tab_availability['unification'] = unif_count > 0

            # Renaming: habilitar si hay necesidades de renombrado
            need_renaming = results.get('renaming', {}).get('need_renaming', 0)
            self.tab_availability['renaming'] = need_renaming > 0

            # Duplicates tab: habilitar si hay grupos detectados
            dup_groups = results.get('duplicates', {}).get('total_groups', 0)
            self.tab_availability['duplicates'] = dup_groups > 0
        except Exception:
            # En caso de error, mantener los valores por defecto (no bloquear pestañas)
            pass

        # Aplicar los cambios en el widget (delegar a ui.tabs)
        try:
            tabs_module.update_tabs_availability(self.window, results)
        except Exception:
            # Silenciar errores de UI para no romper el flujo
            pass
