"""One shared integration; sensors are selected only in the dashboard card."""
try:
    import probatio as vol
except ImportError:
    import voluptuous as vol

from homeassistant import config_entries

DOMAIN = "weather_analysis"


class WeatherAnalysisConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Temperaturanalyse", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
