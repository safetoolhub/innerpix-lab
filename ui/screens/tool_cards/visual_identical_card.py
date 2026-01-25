"""
Crea la card de Copias Visuales Idénticas para el grid de herramientas.
"""

from typing import Callable, Optional, Any

from ui.screens.tool_card import ToolCard
from utils.format_utils import format_size


def create_visual_identical_card(
    analysis_results: Optional[Any],
    on_click_callback: Callable[[str], None]
) -> ToolCard:
    """
    Crea la card de Copias visuales idénticas.
    
    Esta tool detecta archivos visualmente IDÉNTICOS (100% similitud perceptual)
    aunque tengan diferente resolución, compresión o metadatos.
    
    Casos de uso:
    - Fotos enviadas por WhatsApp (comprimidas)
    - Screenshots repetidos
    - Copias redimensionadas
    
    Args:
        analysis_results: Resultados del análisis inicial (puede ser None)
        on_click_callback: Callback para manejar el clic en la card
    
    Returns:
        ToolCard configurada
    """
    card = ToolCard(
        icon_name='image-multiple',
        title='Copias visuales idénticas',
        description='Detecta fotos visualmente idénticas aunque tengan diferente '
                   'resolución o metadatos. Ideal para eliminar copias de WhatsApp, '
                   'screenshots repetidos o imágenes redimensionadas.',
        action_text='Analizar ahora'
    )
    
    # Por defecto está pendiente (requiere análisis)
    card.set_status_pending(
        "Analiza imágenes para encontrar copias visuales idénticas. "
        "Este análisis puede tardar según la cantidad de archivos."
    )
    
    card.clicked.connect(lambda: on_click_callback('visual_identical'))
    
    return card


def update_visual_identical_card(
    card: ToolCard,
    analysis_result: Any
) -> None:
    """
    Actualiza la card con los resultados del análisis.
    
    Args:
        card: La ToolCard a actualizar
        analysis_result: VisualIdenticalAnalysisResult
    """
    if not analysis_result:
        card.set_status_no_results("No se encontraron copias visuales idénticas")
        return
    
    if analysis_result.total_groups > 0:
        size_text = format_size(analysis_result.space_recoverable)
        card.set_status_with_results(
            f"{analysis_result.total_groups} grupos detectados",
            f"~{size_text} recuperables",
            badge_count=analysis_result.total_duplicates
        )
        card.action_button.setText("Gestionar ahora")
    else:
        card.set_status_no_results(
            "No se encontraron copias visuales idénticas. "
            "Todas las imágenes son únicas."
        )
