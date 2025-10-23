"""Utilidades para formateo reutilizables en todo el proyecto.

Contiene funciones puras: format_size, format_file_count, format_percentage,
y truncate_path. Estas funciones no dependen de la UI y pueden importarse desde
`utils.format_utils` en cualquier módulo.
"""
from pathlib import Path
from typing import Optional


def format_size(bytes_size: Optional[float]) -> str:
    """Formatea un tamaño en bytes a una cadena legible.

    Soporta B, KB, MB, GB usando potencias de 1024.
    Maneja None y valores inválidos devolviendo '0 B'. Mantiene el signo para
    valores negativos.
    """
    try:
        if bytes_size is None:
            return "0 B"
        size = float(bytes_size)
    except Exception:
        return "0 B"

    if size < 0:
        return f"-{format_size(abs(size))}"

    if size < 1024:
        return f"{int(size)} B"

    kb = size / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"

    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f} MB"

    gb = mb / 1024
    return f"{gb:.2f} GB"


def format_file_count(count: Optional[int]) -> str:
    """Formatea un recuento de archivos con separador de miles.

    - Si count es None o inválido devuelve '0'.
    - Mantiene formateo con coma como separador de miles.
    """
    try:
        if count is None:
            return "0"
        return f"{int(count):,}"
    except Exception:
        return "0"


def format_percentage(numerator: float, denominator: float) -> str:
    """Devuelve un porcentaje formateado 'xx.x%'.

    - Si denominator es 0 devuelve '0%'.
    - Maneja entradas inválidas devolviendo '0%'.
    """
    try:
        if denominator == 0:
            return "0%"
        pct = (float(numerator) / float(denominator)) * 100
        return f"{pct:.1f}%"
    except Exception:
        return "0%"


def truncate_path(path: str, max_length: int = 40) -> str:
    """Trunca rutas largas insertando '...' en el centro para ajustarse a max_length.

    - Si la longitud de la ruta es menor o igual a max_length devuelve la ruta tal cual.
    - Intenta preservar el inicio y el final de la ruta.
    """
    try:
        if path is None:
            return ""
        s = str(path)
        if len(s) <= max_length:
            return s
        if max_length <= 6:
            return s[:max_length]

        part = (max_length - 3) // 2
        return f"{s[:part]}...{s[-part:]}"
    except Exception:
        return ""
