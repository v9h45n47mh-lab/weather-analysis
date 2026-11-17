"""Run integration setup and native recorder queries in the official HA container."""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import logging

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant import bootstrap, loader
from homeassistant.helpers.recorder import get_instance


async def main():
    with tempfile.TemporaryDirectory() as directory:
        target=Path(directory)/"custom_components"/"weather_analysis"
        shutil.copytree(Path(__file__).resolve().parents[1]/"custom_components"/"weather_analysis",target)
        hass=HomeAssistant(directory)
        loader.async_setup(hass)
        try:
            config={"homeassistant":{"latitude":0,"longitude":0,"elevation":0,"time_zone":"UTC","unit_system":"metric"},"http":{"server_port":8123},"recorder":{}}
            assert await bootstrap.async_from_config_dict(config,hass) is hass
            assert await async_setup_component(hass,"weather_analysis",config)
            await hass.async_start()
            temp={"device_class":"temperature","state_class":"measurement","unit_of_measurement":"°C","friendly_name":"Thermometer"}
            wind={"device_class":"wind_speed","state_class":"measurement","unit_of_measurement":"m/s","friendly_name":"Wind"}
            hass.states.async_set("sensor.outdoor_test","-2",temp)
            hass.states.async_set("sensor.wind_test","5",wind)
            hass.states.async_set("sensor.lux_test","1234",{"device_class":"illuminance","state_class":"measurement","unit_of_measurement":"lx"})
            await hass.async_block_till_done()
            await get_instance(hass).async_block_till_done()
            await asyncio.sleep(.1)
            hass.states.async_set("sensor.outdoor_test","12.3",temp)
            await hass.async_block_till_done()
            await get_instance(hass).async_block_till_done()
            await asyncio.sleep(.1)
            result=await hass.config_entries.flow.async_init("weather_analysis",context={"source":"user"})
            assert result["type"]=="form",result
            assert not result["data_schema"].schema,result
            result=await hass.config_entries.flow.async_configure(result["flow_id"],{})
            assert result["type"]=="create_entry",result
            assert result["title"]=="Weather Analysis",result
            await hass.async_block_till_done()
            from custom_components.weather_analysis import ensure_manager
            manager=await ensure_manager(hass,"sensor.outdoor_test","temperature")
            today=datetime.now(timezone.utc).date().isoformat()
            request={"start_date":today,"end_date":today}
            data=await manager.analyse(request)
            assert data["current"]==12.3,data
            assert data["version"]=="1.2.0",data
            assert manager.history_imported,manager.dump()
            assert manager.history.hours,manager.dump()
            assert data["summary"]["frost_hours"]>0,data
            assert data["summary"]["min"]==-2,data
            assert data["summary"]["min_at"] is not None,data
            assert "heating_degree_days" not in data["summary"]
            wind_manager=await ensure_manager(hass,"sensor.wind_test","wind")
            wind_data=await wind_manager.analyse(request)
            assert wind_data["current"]==18,wind_data
            assert wind_data["unit"]=="km/h",wind_data
            assert wind_manager.history_imported,wind_manager.dump()
            lux_manager=await ensure_manager(hass,"sensor.lux_test","illuminance")
            lux_data=await lux_manager.analyse(request)
            assert lux_data["current"]==1234 and lux_data["unit"]=="lx",lux_data
            assert len(hass.data["weather_analysis"])==3
            hass.states.async_set("sensor.outdoor_test","unavailable",temp)
            await hass.async_block_till_done()
            assert manager.archive.value is None
            duplicate=await hass.config_entries.flow.async_init("weather_analysis",context={"source":"user"})
            assert duplicate["type"]=="abort",duplicate
            print("Real HA smoke test passed: one setup without sensor, dynamic temperature and wind, initial recorder history, frost duration, units, statistics, state event and shutdown.")
        finally:
            await hass.async_stop()


logging.basicConfig(level=logging.WARNING)
asyncio.run(main())
