"""One integration entry per existing temperature sensor."""
try:
    import probatio as vol
except ImportError:  # HA before its validation-library rename
    import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from .analytics import celsius

DOMAIN = "weather_analysis"


class WeatherAnalysisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            entity = user_input["entity_id"]
            state = self.hass.states.get(entity)
            unit = state.attributes.get("unit_of_measurement") if state else None
            if not state or unit not in ("°C", "°F", "K"):
                errors["entity_id"] = "invalid_temperature"
            else:
                await self.async_set_unique_id(entity)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=state.name, data={"entity_id": entity})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("entity_id"): selector.EntitySelector(selector.EntitySelectorConfig(
                domain="sensor", device_class="temperature"))
        }), errors=errors)
