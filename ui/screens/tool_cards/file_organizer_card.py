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
        title='Organizar',
        description='Organiza tus fotos en carpetas por fecha (año/mes o año/mes/día). '
                   'Reorganiza tu biblioteca de forma automática y mantén todo ordenado.',
        action_text='Organizar ahora'
    )

    # Esta herramienta no requiere análisis previo
    card.set_status_ready("Listo para organizar archivos")
    card.clicked.connect(lambda: on_click_callback('folder-move'))
    return card
