"""
Crea la card de Renombrar para el grid de herramientas.
"""

from ui.screens.tool_card import ToolCard
from ui.tools_definitions import TOOL_FILE_RENAMER


def create_file_renamer_card(on_click_callback) -> ToolCard:
    """
    Crea la card de Renombrar

    Args:
        on_click_callback: Callback para manejar el clic en la card

    Returns:
        ToolCard configurada
    """
    card = ToolCard(
        icon_name=TOOL_FILE_RENAMER.icon_name,
        title=TOOL_FILE_RENAMER.title,
        description=TOOL_FILE_RENAMER.long_description,
        action_text='Renombrar ahora'
    )

    # Esta herramienta no requiere análisis previo
    card.set_status_ready("Listo para renombrar archivos")
    card.clicked.connect(lambda: on_click_callback('file_renamer'))
    return card
