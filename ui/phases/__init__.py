"""
Módulos de fases de la interfaz de usuario de Pixaro Lab.
Cada fase representa una etapa diferente de la aplicación.
"""

from .base_phase import BasePhase
from .phase_1 import Phase1
from .phase_2 import Phase2
from .phase_3 import Phase3

__all__ = ['BasePhase', 'Phase1', 'Phase2', 'Phase3']