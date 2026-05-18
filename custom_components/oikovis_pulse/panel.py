"""Panel registration for Oikovis Pulse."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    FRONTEND_SCRIPT_URL,
    PANEL_COMPONENT_NAME,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL,
    STATIC_PATH,
)

_LOGGER = logging.getLogger(__name__)


async def async_register(hass: HomeAssistant) -> None:
    """Register the static asset path and the custom panel."""
    frontend_dir = Path(__file__).parent / "frontend"

    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_PATH, str(frontend_dir), cache_headers=False)]
    )

    await panel_custom.async_register_panel(
        hass=hass,
        webcomponent_name=PANEL_COMPONENT_NAME,
        frontend_url_path=PANEL_URL,
        module_url=FRONTEND_SCRIPT_URL,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=False,
        embed_iframe=False,
    )

    _LOGGER.debug("Pulse panel registered at /%s", PANEL_URL)


async def async_unregister(hass: HomeAssistant) -> None:
    """Remove the custom panel. Static paths are cleared on restart."""
    async_remove_panel(hass, PANEL_URL)
    _LOGGER.debug("Pulse panel unregistered")
