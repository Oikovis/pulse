"""Test configuration and fixtures."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Pre-populate sys.modules with mocks for homeassistant submodules before any imports
homeassistant_mocks = [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.core",
    "homeassistant.components",
    "homeassistant.components.panel_custom",
    "homeassistant.components.frontend",
    "homeassistant.components.http",
]

for module_name in homeassistant_mocks:
    sys.modules[module_name] = MagicMock()
