"""
Definiciones centralizadas de todas las herramientas de InnerPix Lab.

Este archivo es la única fuente de verdad para nombres, descripciones e iconos
de las herramientas. Cualquier cambio en nomenclatura debe hacerse aquí.

Preparado para futura internacionalización (i18n).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ToolDefinition:
    """Definición inmutable de una herramienta."""
    id: str
    title: str
    short_description: str
    long_description: str
    icon_name: str


@dataclass(frozen=True)
class ToolCategory:
    """Definición inmutable de una categoría de herramientas."""
    id: str
    title: str
    description: str
    tool_ids: tuple  # Tupla de IDs de herramientas en esta categoría


# =============================================================================
# DEFINICIONES DE HERRAMIENTAS
# =============================================================================

TOOL_ZERO_BYTE = ToolDefinition(
    id='zero_byte',
    title='Archivos vacíos',
    short_description='Estos archivos ocupan 0 bytes y no contienen información. Es 100% seguro eliminarlos',
    long_description=(
        'Escanea sus carpetas en busca de "archivos fantasma" (archivos de 0 bytes) '
        'que no contienen datos útiles. Elimínalos de forma segura.'
    ),
    icon_name='file-x'
)

TOOL_LIVE_PHOTOS = ToolDefinition(
    id='live_photos',
    title='Live Photos',
    short_description='Live Photos de iPhone (Imagen + MOV). Los videos MOV serán eliminados para liberar espacio',
    long_description=(
        'Las Live Photos de iPhone constan de una imagen y vídeo corto. '
        'Esta herramienta detecta estos pares y te permite decidir si deseas conservar ambos, '
        'o limpiar el componente de video para ahorrar espacio si solo te interesa la fotografía estática.'
    ),
    icon_name='camera-burst'
)

TOOL_HEIC = ToolDefinition(
    id='heic',
    title='Duplicados HEIC/JPG',
    short_description='Fotos HEIC con versiones JPG idénticas. Elige qué formato conservar y libera espacio',
    long_description=(
        'Encuentra casos donde tienes la misma fotografía en dos formatos: HEIC (usado por iPhones) '
        'y el tradicional JPG. La herramienta le ayuda a identificar estos duplicados y eliminar '
        'las versiones redundantes para liberar espacio.'
    ),
    icon_name='file-image'
)

TOOL_DUPLICATES_EXACT = ToolDefinition(
    id='duplicates_exact',
    title='Copias exactas',
    short_description='Archivos 100% idénticos aunque tengan nombres diferentes. Es totalmente seguro borrarlos',
    long_description=(
        'Analiza tu colección para encontrar archivos que son matemáticamente idénticos. '
        'Es la forma más segura de limpieza, ya que garantiza que no estás borrando una foto "parecida", '
        'sino exactamente el mismo archivo repetido en diferentes carpetas (aunque tenga distinto nombre).'
    ),
    icon_name='content-copy'
)

TOOL_VISUAL_IDENTICAL = ToolDefinition(
    id='visual_identical',
    title='Copias visualmente idénticas',
    short_description='Archivos visualmente idénticos, pero con diferentes datos internos. Sucede en fotos enviadas por WhatsApp o redimensionadas.',
    long_description=(
        'Identifica imágenes (videos en próximas versiones) que son visualmente indistinguibles para el ojo humano, '
        'aunque técnicamente sean archivos diferentes (por ejemplo, una copia descargada de internet, '
        'o la misma foto guardada en diferentes fechas). Ideal para eliminar copias de WhatsApp, '
        'screenshots repetidos o imágenes redimensionadas.'
    ),
    icon_name='image-multiple'
)

TOOL_DUPLICATES_SIMILAR = ToolDefinition(
    id='duplicates_similar',
    title='Archivos similares',
    short_description='Detecta imágenes similares pero no iguales (ediciones, recortes, distinta resolución...)',
    long_description=(
        'Detecta fotos (videos en próximas versiones) que son muy parecidos pero no idénticos. Esto es perfecto para:\n'
        '• Seleccionar la mejor toma de una ráfaga de fotos.\n'
        '• Eliminar versiones ligeramente editadas o recortadas que ya no necesita.\n'
        '• Detectar copias de baja resolución.'
    ),
    icon_name='image-search'
)

TOOL_FILE_ORGANIZER = ToolDefinition(
    id='file_organizer',
    title='Organización inteligente',
    short_description='Organiza las imágenes y videos en una nueva estructura de carpetas',
    long_description=(
        'Esta herramienta analiza tus archivos y propone una nueva estructura de carpetas organizada '
        'lógicamente (por ejemplo, por Año/Mes), permitiendo reubicar miles de fotos con un solo clic '
        'y mantener la biblioteca impecable.'
    ),
    icon_name='folder-move'
)

TOOL_FILE_RENAMER = ToolDefinition(
    id='file_renamer',
    title='Renombrado completo',
    short_description='Los archivos se renombrarán al formato YYYY-MM-DD_HH-MM-SS_<PHOTO|VIDEO> usando su fecha de creación',
    long_description=(
        'Estandariza los nombres de tus archivos de forma profesional. Puedes cambiar nombres crípticos '
        'como "IMG_8823.JPG" a formatos útiles y legibles como "20241231_112300_PHOTO.jpg", '
        'utilizando fechas y secuencias automáticas para evitar conflictos de nombres.'
    ),
    icon_name='rename-box'
)


# =============================================================================
# CATEGORÍAS DE HERRAMIENTAS
# =============================================================================

CATEGORY_CLEANUP = ToolCategory(
    id='cleanup',
    title='Limpieza y espacio',
    description='Libera espacio eliminando archivos innecesarios',
    tool_ids=('zero_byte', 'live_photos', 'heic', 'duplicates_exact')
)

CATEGORY_VISUAL = ToolCategory(
    id='visual',
    title='Detección visual',
    description='Encuentra imágenes visualmente similares',
    tool_ids=('visual_identical', 'duplicates_similar')
)

CATEGORY_ORGANIZATION = ToolCategory(
    id='organization',
    title='Organización',
    description='Ordena y renombra tu colección',
    tool_ids=('file_organizer', 'file_renamer')
)

# Lista ordenada de categorías
TOOL_CATEGORIES: List[ToolCategory] = [
    CATEGORY_CLEANUP,
    CATEGORY_VISUAL,
    CATEGORY_ORGANIZATION,
]


# =============================================================================
# REGISTRO DE HERRAMIENTAS
# =============================================================================

# Diccionario con todas las herramientas indexadas por ID
TOOLS: Dict[str, ToolDefinition] = {
    tool.id: tool for tool in [
        TOOL_ZERO_BYTE,
        TOOL_LIVE_PHOTOS,
        TOOL_HEIC,
        TOOL_DUPLICATES_EXACT,
        TOOL_VISUAL_IDENTICAL,
        TOOL_DUPLICATES_SIMILAR,
        TOOL_FILE_ORGANIZER,
        TOOL_FILE_RENAMER,
    ]
}


# =============================================================================
# FUNCIONES DE ACCESO
# =============================================================================

def get_tool(tool_id: str) -> Optional[ToolDefinition]:
    """
    Obtiene la definición de una herramienta por su ID.
    
    Args:
        tool_id: Identificador de la herramienta (ej: 'zero_byte', 'live_photos')
        
    Returns:
        ToolDefinition o None si no existe
    """
    return TOOLS.get(tool_id)


def get_tool_title(tool_id: str) -> str:
    """
    Obtiene el título de una herramienta por su ID.
    
    Args:
        tool_id: Identificador de la herramienta
        
    Returns:
        Título de la herramienta o el ID si no existe
    """
    tool = TOOLS.get(tool_id)
    return tool.title if tool else tool_id


def get_tool_short_description(tool_id: str) -> str:
    """
    Obtiene la descripción corta de una herramienta por su ID.
    
    Args:
        tool_id: Identificador de la herramienta
        
    Returns:
        Descripción corta o string vacío si no existe
    """
    tool = TOOLS.get(tool_id)
    return tool.short_description if tool else ''


def get_tool_long_description(tool_id: str) -> str:
    """
    Obtiene la descripción larga de una herramienta por su ID.
    
    Args:
        tool_id: Identificador de la herramienta
        
    Returns:
        Descripción larga o string vacío si no existe
    """
    tool = TOOLS.get(tool_id)
    return tool.long_description if tool else ''


def get_all_tool_ids() -> list:
    """
    Obtiene la lista de todos los IDs de herramientas.
    
    Returns:
        Lista de IDs de herramientas
    """
    return list(TOOLS.keys())


def get_tools_by_category(category_id: str) -> List[ToolDefinition]:
    """
    Obtiene las herramientas de una categoría específica.
    
    Args:
        category_id: Identificador de la categoría ('cleanup', 'visual', 'organization')
        
    Returns:
        Lista de ToolDefinition de esa categoría
    """
    for category in TOOL_CATEGORIES:
        if category.id == category_id:
            return [TOOLS[tool_id] for tool_id in category.tool_ids if tool_id in TOOLS]
    return []


def get_category(category_id: str) -> Optional[ToolCategory]:
    """
    Obtiene una categoría por su ID.
    
    Args:
        category_id: Identificador de la categoría
        
    Returns:
        ToolCategory o None si no existe
    """
    for category in TOOL_CATEGORIES:
        if category.id == category_id:
            return category
    return None


def get_all_categories() -> List[ToolCategory]:
    """
    Obtiene todas las categorías de herramientas.
    
    Returns:
        Lista de ToolCategory ordenada
    """
    return TOOL_CATEGORIES
