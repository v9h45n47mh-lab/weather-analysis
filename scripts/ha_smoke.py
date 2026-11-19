"""Run integration setup and native recorder queries in the official HA container."""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import logging
from types import SimpleNamespace

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
            def verify_native_radar():
                import runpy,numpy as np
                fixture=runpy.run_path(str(Path(__file__).resolve().parents[1]/"tests/test_radar.py"))
                from custom_components.weather_analysis.radar_data import metadata,render,PNG
                raw=fixture["hdf"]();reference=fixture["NOW"]-600
                meta=metadata(raw,(reference,0))
                grid=(np.array([[0,0]]),np.array([[0,1]]),np.ones((1,2),dtype=bool))
                image=render(raw,meta,grid,fixture["SCALE"])
                assert image.startswith(PNG) and len(image)>50
            await hass.async_add_executor_job(verify_native_radar)
            print("Native raw DWD decoder and local radar renderer passed")
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
            from custom_components.weather_analysis import ensure_manager, user_position, ws_location, on_home_wifi, ws_save_network, ws_network, ws_warnings, ws_radar, ws_radar_image
            # Native HA states and permission objects; no network or actual user coordinates.
            hass.states.async_set("device_tracker.gps_test","not_home",{"source_type":"gps","latitude":53.55,"longitude":10})
            hass.states.async_set("person.gps_test","not_home",{"user_id":"gps-test","device_trackers":["device_tracker.gps_test"],"source":"device_tracker.gps_test"})
            conn=SimpleNamespace(user=SimpleNamespace(id="gps-test",is_admin=False,permissions=SimpleNamespace(check_entity=lambda entity,policy:True)))
            assert user_position(hass,conn)==(53.55,10.0)
            conn.user.id="another-user"
            assert user_position(hass,conn) is None
            responses=[]
            conn.send_result=lambda request,data:responses.append(data)
            ws_location(hass,conn,{"id":1})
            await hass.async_block_till_done()
            assert not responses[-1]["location"]["is_home"]
            assert not responses[-1]["location"]["position_available"]
            from homeassistant.helpers import entity_registry as er, device_registry as dr
            registry=er.async_get(hass)
            device=dr.async_get(hass).async_get_or_create(config_entry_id=result["result"].entry_id,identifiers={("weather_analysis","wifi-smoke")})
            tracker=registry.async_get_or_create("device_tracker","mobile_app","wifi-smoke-tracker",device_id=device.id,suggested_object_id="wifi_smoke_phone")
            ssid=registry.async_get_or_create("sensor","mobile_app","wifi-smoke_ssid",device_id=device.id,suggested_object_id="wifi_smoke_ssid")
            hass.states.async_set(tracker.entity_id,"not_home",{"source_type":"gps","latitude":53.55,"longitude":10})
            hass.states.async_set(ssid.entity_id,"Home test")
            hass.states.async_set("person.gps_test","not_home",{"user_id":"gps-test","device_trackers":[tracker.entity_id],"source":tracker.entity_id})
            conn.user.is_admin=True
            saved=asyncio.Event()
            def sent_result(request,data):
                responses.append(data)
                if request==3:saved.set()
            conn.send_result=sent_result
            ws_save_network(hass,conn,{"id":3,"home_ssids":["Home test"]})
            await asyncio.wait_for(saved.wait(),10)
            conn.user.is_admin=False
            assert (await hass.data["weather_analysis_network_store"].async_load())["home_ssids"]==["Home test"]
            conn.user.id="gps-test"
            assert on_home_wifi(hass,conn)
            saved.clear()
            def network_result(request,data):
                responses.append(data)
                if request==4:saved.set()
            conn.send_result=network_result
            ws_network(hass,conn,{"id":4})
            await asyncio.wait_for(saved.wait(),10)
            assert responses[-1]["home_wifi"]
            async def warnings_get(*args):return {"status":"ok","alerts":[]}
            hass.data["weather_analysis_warnings"]=SimpleNamespace(get=warnings_get)
            saved.clear()
            def warning_result(request,data):
                responses.append(data)
                if request==5:saved.set()
            conn.send_result=warning_result
            ws_warnings(hass,conn,{"id":5})
            await asyncio.wait_for(saved.wait(),10)
            assert responses[-1]["warnings"]["status"]=="ok"
            async def radar_get(*args):return {"status":"ok","token":"native-smoke"}
            async def radar_image(*args,**kwargs):return "data:image/png;base64,AAAA"
            hass.data["weather_analysis_radar"]=SimpleNamespace(get=radar_get,image=radar_image)
            saved.clear()
            def radar_result(request,data):
                responses.append(data)
                if request==6:saved.set()
            conn.send_result=radar_result
            ws_radar(hass,conn,{"id":6,"zoom":1})
            await asyncio.wait_for(saved.wait(),10)
            assert responses[-1]["radar"]["status"]=="ok"
            saved.clear()
            def image_result(request,data):
                responses.append(data)
                if request==7:saved.set()
            conn.send_result=image_result
            ws_radar_image(hass,conn,{"id":7,"token":"native-smoke","kind":"frame","index":0})
            await asyncio.wait_for(saved.wait(),10)
            assert responses[-1]["image"].startswith("data:image/png")
            ws_location(hass,conn,{"id":2,"card_id":"wifi-smoke"})
            await hass.async_block_till_done()
            assert responses[-1]["location"]["is_home"]
            assert responses[-1]["location"]["via"]=="home_wifi"
            hass.states.async_set(ssid.entity_id,"Hotel test")
            assert not on_home_wifi(hass,conn)
            manager=await ensure_manager(hass,"sensor.outdoor_test","temperature")
            today=datetime.now(timezone.utc).date().isoformat()
            request={"start_date":today,"end_date":today}
            data=await manager.analyse(request)
            assert data["current"]==12.3,data
            assert data["version"]=="1.16.0",data
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
