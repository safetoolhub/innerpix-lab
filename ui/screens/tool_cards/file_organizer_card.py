"""
Crea la card de Organizar para el grid de herramientas.
"""

from ui.screens.tool_card import ToolCard


def create_file_organizer_card(on_click_callback) -> ToolCard:
    """
    Crea la card de Organizar

    Args:
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    card = ToolCard(
        icon_name='folder-move',
        title='Organización inteligente',
        description='Organiza tus archivos en una estructura de carpetas organizada lógicamente (por ejemplo, por Año/mes) '
                   'Reubica miles de fotos con un solo clic y mantén todo ordenado.',
        action_text='Organizar ahora'
    )


    # Esta herramienta no requiere análisis previo
    card.set_status_ready("Listo para organizar archivos")
    card.clicked.connect(lambda: on_click_callback('file_organizer'))
    return card
