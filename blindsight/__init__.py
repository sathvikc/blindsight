"""Blindsight — classical image-to-text descriptor for LLM consumption.

Public API:

    from blindsight import extract
    descriptor = extract("photo.jpg")
    print(descriptor.to_text())
    print(descriptor.to_json())
"""

from .descriptor import ImageDescriptor, ModuleResult
from .extractor import extract

__all__ = ["extract", "ImageDescriptor", "ModuleResult"]
__version__ = "0.1.0"
