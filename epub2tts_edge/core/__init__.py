"""Core business logic for audiobookify.

This module contains the unified pipeline, event system, and supporting classes
that are shared between CLI and TUI interfaces.
"""

from .events import Event, EventBus, EventHandler, EventType
from .pipeline import ConversionPipeline, PipelineConfig, PipelineResult

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
]
