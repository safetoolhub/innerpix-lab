"""
Crea la card de Organizar para el grid de herramientas.
"""

from ui.screens.tool_card import ToolCard
from ui.tools_definitions import TOOL_FILE_ORGANIZER


def create_file_organizer_card(on_click_callback) -> ToolCard:
    """
    Crea la card de Organizar

    Args:
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    card = ToolCard(
        icon_name=TOOL_FILE_ORGANIZER.icon_name,
        title=TOOL_FILE_ORGANIZER.title,
        description=TOOL_FILE_ORGANIZER.long_description,
        action_text='Organizar ahora'
    )


    # Esta herramienta no requiere análisis previo
    card.set_status_ready("Listo para organizar archivos")
    card.clicked.connect(lambda: on_click_callback('file_organizer'))
    return card
