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
            hass.states.async_set("sensor.wind_test2","8",wind)
            hass.states.async_set("sensor.lux_test2","2345",{"device_class":"illuminance","state_class":"measurement","unit_of_measurement":"lx"})
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
            assert data["version"]=="1.10.1",data
            assert manager.history_imported,manager.dump()
            assert manager.history.hours,manager.dump()
            assert data["summary"]["frost_hours"]>0,data
            assert data["summary"]["min"]==-2,data
            assert data["summary"]["min_at"] is not None,data
            for interval in (900,3600,10800,21600):
                detail=await manager.analyse({**request,"chart_interval":interval})
                assert detail["chart_interval"]==interval,detail
                assert detail["chart"] and all(point["resolution"]==interval for point in detail["chart"]),detail
                assert detail["summary"]["min"]==-2,detail
            assert manager.dump()["history"]["quarters"]
            assert manager.dump()["history_resolution"]==900
            dashboard_today=await manager.analyse({**request,"chart_interval":900,"window":"day"})
            assert dashboard_today["summary"]["min"]==-2
            assert dashboard_today["summary"]["max"]==12.3
            assert dashboard_today["display_end"]>dashboard_today["end"]
            for window,interval in [("day",900),("week",3600)]:
                rolling=await manager.analyse({**request,"window":window,"chart_interval":interval})
                assert rolling["window"]==window,rolling
                assert rolling["display_end"]>=rolling["end"],rolling
                assert all(point["end"]<=rolling["end"] for point in rolling["chart"]),rolling
                if window=="day":assert datetime.fromtimestamp(rolling["start"],timezone.utc).hour==0
            assert "heating_degree_days" not in data["summary"]
            wind_manager=await ensure_manager(hass,"sensor.wind_test","wind")
            wind_data=await wind_manager.analyse(request)
            assert wind_data["current"]==18,wind_data
            assert wind_data["unit"]=="km/h",wind_data
            assert wind_manager.history_imported,wind_manager.dump()
            lux_manager=await ensure_manager(hass,"sensor.lux_test","illuminance")
            lux_data=await lux_manager.analyse(request)
            assert lux_data["current"]==1234 and lux_data["unit"]=="lx",lux_data
            for weather_manager in (wind_manager,lux_manager):
                intervals=await weather_manager.analyse({**request,"chart_interval":10800,"window":"day"})
                assert all(point["resolution"]==10800 for point in intervals["chart"]),intervals
            assert len(hass.data["weather_analysis"])==3
            hass.data["weather_analysis_settings"]["smoke"]={"entities":["sensor.outdoor_test"],
                "wind_entities":["sensor.wind_test","sensor.wind_test2"],
                "illuminance_entities":["sensor.lux_test","sensor.lux_test2"],
                "sensor_names":{"sensor.wind_test2":"Roof wind"}}
            await hass.data["weather_analysis_store"].async_save(hass.data["weather_analysis_settings"])
            assert await hass.config_entries.async_reload(result["result"].entry_id)
            await hass.async_block_till_done()
            managers={m.entity:m for m in hass.data["weather_analysis"].values()}
            assert len(managers)==5,managers
            assert (await managers["sensor.wind_test2"].analyse(request))["current"]==28.8
            assert (await managers["sensor.lux_test2"].analyse(request))["current"]==2345
            hass.states.async_set("sensor.legacy_lux","1234",{"unit_of_measurement":"Lux","device_class":""})
            hass.states.async_set("sensor.legacy_wind","5",{"unit_of_measurement":" km / h ","device_class":""})
            await hass.async_block_till_done()
            for entity,kind,current in [("sensor.legacy_lux","illuminance",1234),("sensor.legacy_wind","wind",5)]:
                legacy=await ensure_manager(hass,entity,kind)
                assert (await legacy.analyse(request))["current"]==current
            manager=managers["sensor.outdoor_test"]
            hass.states.async_set("sensor.outdoor_test","unavailable",temp)
            await hass.async_block_till_done()
            assert manager.archive.value is None
            duplicate=await hass.config_entries.flow.async_init("weather_analysis",context={"source":"user"})
            assert duplicate["type"]=="abort",duplicate
            print("Real HA smoke test passed: one setup without sensor, multiple temperature/wind/light sensors, reload migration, initial recorder history, frost duration, units, statistics, state event and shutdown.")
        finally:
            await hass.async_stop()


logging.basicConfig(level=logging.WARNING)
asyncio.run(main())
