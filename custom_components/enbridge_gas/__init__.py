"""Import Enbridge Gas billing history into Home Assistant statistics."""

from datetime import tzinfo
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.recorder.models import (
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import VolumeConverter

from .const import DOMAIN, PANEL_PATH, STATIC_PATH, STATISTIC_ID
from .parser import ExportError, build_hourly_statistics, parse_export

MAX_UPLOAD_BYTES = 2 * 1024 * 1024


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the import panel and its authenticated WebSocket command."""
    websocket_api.async_register_command(hass, websocket_import)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                f"{STATIC_PATH}/enbridge-gas-panel.js",
                str(Path(__file__).parent / "www" / "enbridge-gas-panel.js"),
                cache_headers=False,
            )
        ]
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Register the admin-only Enbridge upload panel."""
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name="enbridge-gas-panel",
        module_url=f"{STATIC_PATH}/enbridge-gas-panel.js",
        sidebar_title="Enbridge Gas",
        sidebar_icon="mdi:fire",
        require_admin=True,
        config_panel_domain=DOMAIN,
        config={"entry_id": entry.entry_id},
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove the upload panel when the integration is unloaded."""
    frontend.async_remove_panel(hass, PANEL_PATH)
    return True


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/import",
        vol.Required("entry_id"): str,
        vol.Required("filename"): str,
        vol.Required("contents"): str,
    }
)
@websocket_api.async_response
async def websocket_import(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Parse an uploaded statement and add its history as gas statistics."""
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(
            msg["id"], "invalid_entry", "Integration entry not found"
        )
        return

    contents = msg["contents"]
    if len(contents.encode("utf-8")) > MAX_UPLOAD_BYTES:
        connection.send_error(
            msg["id"], "file_too_large", "Files must be 2 MB or smaller"
        )
        return

    if "recorder" not in hass.config.components:
        connection.send_error(
            msg["id"],
            "recorder_not_loaded",
            "Home Assistant Recorder is required",
        )
        return

    try:
        periods = parse_export(msg["filename"], contents)
        timezone: tzinfo | None = dt_util.get_time_zone(hass.config.time_zone)
        if timezone is None:
            raise ExportError(
                "Set a valid Home Assistant time zone before importing"
            )
        statistics = build_hourly_statistics(periods, timezone)
    except ExportError as err:
        connection.send_error(msg["id"], "invalid_file", str(err))
        return

    metadata: StatisticMetaData = {
        "source": DOMAIN,
        "name": "Enbridge Gas consumption",
        "statistic_id": STATISTIC_ID,
        "unit_class": VolumeConverter.UNIT_CLASS,
        "unit_of_measurement": UnitOfVolume.CUBIC_METERS,
        "mean_type": StatisticMeanType.NONE,
        "has_sum": True,
    }
    async_add_external_statistics(hass, metadata, statistics)
    connection.send_result(
        msg["id"],
        {
            "periods": len(periods),
            "hours": len(statistics),
            "total_m3": sum(
                float(period.consumption_m3) for period in periods
            ),
            "statistic_id": STATISTIC_ID,
        },
    )
