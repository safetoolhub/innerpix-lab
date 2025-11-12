"""
Decoradores utilitarios para Pixaro Lab.

Incluye decoradores para deprecación de métodos y funciones.
"""

import warnings
import functools
from typing import Callable, Any


def deprecated(reason: str = "", replacement: str = "") -> Callable:
    """
    Decorador para marcar funciones/métodos como deprecated.
    
    Emite una DeprecationWarning cuando se llama al método decorado.
    
    Args:
        reason: Razón de la deprecación
        replacement: Nombre del método/función de reemplazo sugerido
        
    Example:
        @deprecated(reason="Nomenclatura inconsistente", replacement="analyze()")
        def analyze_directory(self, directory: Path):
            return self.analyze(directory)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Construir mensaje de warning
            msg = f"{func.__name__} está deprecated"
            if reason:
                msg += f": {reason}"
            if replacement:
                msg += f". Use {replacement} en su lugar"
            
            warnings.warn(
                msg,
                category=DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        
        # Marcar función como deprecated para introspección
        wrapper.__deprecated__ = True
        wrapper.__deprecated_reason__ = reason
        wrapper.__deprecated_replacement__ = replacement
        
        return wrapper
    return decorator
