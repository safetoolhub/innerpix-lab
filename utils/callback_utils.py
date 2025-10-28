"""
Utilidades para manejo seguro de callbacks de progreso.

Este módulo proporciona helpers para ejecutar callbacks de progreso
de forma segura, evitando que errores en callbacks detengan procesos críticos.
"""

from typing import Callable, Optional, Any
from utils.logger import get_logger

logger = get_logger('callback_utils')


def safe_progress_callback(
    callback: Optional[Callable[[int, int, str], None]],
    current: int,
    total: int,
    message: str
) -> None:
    """
    Ejecuta callback de progreso de forma segura.

    Args:
        callback: Función callback a ejecutar (current, total, message)
        current: Valor actual del progreso
        total: Valor total del progreso
        message: Mensaje descriptivo del estado actual

    Note:
        Si el callback falla, se registra un warning pero no se detiene el proceso.
        Esto evita que errores en la UI/callbacks rompan operaciones críticas.
    """
    if callback and callable(callback):
        try:
            callback(current, total, message)
        except Exception as e:
            logger.warning(f"Error en progress callback: {e}")


def create_safe_callback(
    callback: Optional[Callable[[int, int, str], None]]
) -> Callable[[int, int, str], None]:
    """
    Crea una versión segura de un callback que puede ser None.

    Args:
        callback: Callback original (puede ser None)

    Returns:
        Función que ejecuta el callback de forma segura o no hace nada si callback es None

    Example:
        >>> safe_cb = create_safe_callback(progress_callback)
        >>> safe_cb(50, 100, "Processing...")  # Siempre seguro llamar
    """
    def safe_wrapper(current: int, total: int, message: str) -> None:
        safe_progress_callback(callback, current, total, message)

    return safe_wrapper
