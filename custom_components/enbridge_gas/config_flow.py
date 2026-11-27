"""Config flow for the Enbridge Gas integration."""

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class EnbridgeGasConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the Enbridge Gas importer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the single Enbridge Gas import entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Enbridge Gas", data={})
