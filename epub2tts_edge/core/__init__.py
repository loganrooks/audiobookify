"""Core business logic for audiobookify.

This module contains the unified pipeline, event system, and supporting classes
that are shared between CLI and TUI interfaces.
"""

from .events import Event, EventBus, EventHandler, EventType
from .output_naming import BookMetadata, OutputNaming, get_naming_preset, list_naming_presets
from .pipeline import ConversionPipeline, PipelineConfig, PipelineResult
from .profiles import (
    BUILTIN_PROFILES,
    ProcessingProfile,
    get_profile,
    get_profile_names,
    list_profiles,
)

__all__ = [
    # Pipeline
    "ConversionPipeline",
    "PipelineConfig",
    "PipelineResult",
    # Events
    "Event",
    "EventBus",
    "EventHandler",
    "EventType",
    # Profiles
    "ProcessingProfile",
    "BUILTIN_PROFILES",
    "get_profile",
    "get_profile_names",
    "list_profiles",
    # Output Naming
    "OutputNaming",
    "BookMetadata",
    "get_naming_preset",
    "list_naming_presets",
]
