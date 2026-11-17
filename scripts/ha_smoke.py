"""Load the real integration in a clean HA instance; used by GitHub Actions."""
import asyncio
from datetime import datetime
from pathlib import Path
import shutil
import tempfile

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


async def main():
    with tempfile.TemporaryDirectory() as directory:
        target=Path(directory)/'custom_components'/'weather_analysis'
        shutil.copytree(Path(__file__).resolve().parents[1]/'custom_components'/'weather_analysis',target)
        hass=HomeAssistant(directory)
        try:
            assert await async_setup_component(hass,'weather_analysis',{'http':{'server_port':0},'recorder':{}})
            await hass.async_start()
            hass.states.async_set('sensor.outdoor_test','12.3',{'device_class':'temperature','state_class':'measurement','unit_of_measurement':'°C','friendly_name':'Outdoor smoke test'})
            result=await hass.config_entries.flow.async_init('weather_analysis',context={'source':'user'})
            assert result['type']=='form',result
            result=await hass.config_entries.flow.async_configure(result['flow_id'],{'entity_id':'sensor.outdoor_test'})
            assert result['type']=='create_entry',result
            await hass.async_block_till_done()
            manager=hass.data['weather_analysis'][result['result'].entry_id]
            today=datetime.now().date().isoformat()
            data=await manager.analyse({'start_date':today,'end_date':today,'heating_base':20.,'heating_limit':15.})
            assert data['current']==12.3,data
            assert data['version']=='1.0.0',data
            hass.states.async_set('sensor.outdoor_test','unavailable',{'device_class':'temperature','unit_of_measurement':'°C'})
            await hass.async_block_till_done()
            assert manager.archive.value is None
            print('Real Home Assistant smoke test passed: setup, config flow, native sensor, statistics, state event and shutdown.')
        finally:
            await hass.async_stop()


asyncio.run(main())
