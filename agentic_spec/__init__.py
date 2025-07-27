"""
Agentic Programming Specification System

A tool for generating detailed programming specifications from high-level prompts,
with inheritance support and AI-powered review workflows.
"""

from .core import SpecGenerator
from .models import (
    ImplementationStep,
    ProgrammingSpec,
    SpecContext,
    SpecMetadata,
    SpecRequirement,
)

__version__ = "0.1.0"
__all__ = [
    "ImplementationStep",
    "ProgrammingSpec",
    "SpecContext",
    "SpecGenerator",
    "SpecMetadata",
    "SpecRequirement",
]
