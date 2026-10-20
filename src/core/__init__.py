"""Core package init"""
from .models import CoilInputs, CoilOutputs, DFMCheckResult, WindingMode
from .physics_engine import CoilPhysicsEngine

__all__ = [
    "CoilInputs",
    "CoilOutputs",
    "DFMCheckResult",
    "WindingMode",
    "CoilPhysicsEngine",
]
