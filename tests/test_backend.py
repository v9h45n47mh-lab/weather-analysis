"""Exercise the actual HA adapter with small mocks for the host-only interfaces."""
import asyncio
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock


def module(name, **attrs):
    obj=ModuleType(name)
    obj.__dict__.update(attrs)
    sys.modules[name]=obj
    return obj


class Schema:
    def __init__(self,*args,**kwargs): pass
    def __call__(self,value): return value


class Store:
    def __init__(self,*args): self.value=None
    async def async_load(self): return self.value
    async def async_save(self,data): self.value=data
    def async_delay_save(self,*args): pass


module('probatio',Required=lambda x,**kw:x,Optional=lambda x,**kw:x,Schema=Schema,All=Schema,Coerce=Schema,Range=Schema,Length=Schema)
module('homeassistant')
module('homeassistant.auth');module('homeassistant.auth.permissions');module('homeassistant.auth.permissions.const',POLICY_READ='read')
websocket=module('homeassistant.components.websocket_api',websocket_command=lambda *args:lambda f:f,async_response=lambda f:f,async_register_command=lambda *args:None)
frontend=module('homeassistant.components.frontend',add_extra_js_url=lambda *args:None)
module('homeassistant.components',websocket_api=websocket,frontend=frontend)
module('homeassistant.components.http',StaticPathConfig=lambda *args:args)
module('homeassistant.components.recorder');module('homeassistant.components.recorder.statistics',statistics_during_period=lambda *args:{})
module('homeassistant.core',callback=lambda f:f)
module('homeassistant.const',EVENT_HOMEASSISTANT_STOP='stop')
module('homeassistant.helpers');module('homeassistant.helpers.event',async_track_state_change_event=lambda *args:lambda:None,async_track_time_interval=lambda *args:lambda:None)
module('homeassistant.helpers.recorder',get_instance=lambda hass:hass.recorder)
module('homeassistant.helpers.storage',Store=Store)
now=datetime(2026,11,17,12,30,tzinfo=timezone.utc)
dt=module('homeassistant.util.dt',utcnow=lambda:now,UTC=timezone.utc)
module('homeassistant.util',dt=dt)
path=Path(__file__).parents[1]/'custom_components/weather_analysis/__init__.py'
spec=importlib.util.spec_from_file_location('weather_analysis',path,submodule_search_locations=[str(path.parent)])
backend=importlib.util.module_from_spec(spec);sys.modules[spec.name]=backend;spec.loader.exec_module(backend)


class Connection:
    def __init__(self,admin=False,read=True):
        self.user=SimpleNamespace(is_admin=admin,permissions=SimpleNamespace(check_entity=lambda entity,policy:read))
        self.results=[];self.errors=[]
    def send_result(self,*args): self.results.append(args)
    def send_error(self,*args): self.errors.append(args)


class BackendTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.state=SimpleNamespace(name='Test sensor',state='50',attributes={'unit_of_measurement':'°F'},last_updated=now)
        self.hass=SimpleNamespace(config=SimpleNamespace(time_zone='Europe/Berlin'),states=SimpleNamespace(get=lambda entity:self.state),
            data={backend.DOMAIN:{},backend.DOMAIN+'_settings':{},backend.DOMAIN+'_store':Store()})
        self.manager=backend.Manager(self.hass,SimpleNamespace(data={'entity_id':'sensor.test'},entry_id='entry'))
        self.manager.statistics=AsyncMock(return_value=[])
        self.hass.data[backend.DOMAIN]['entry']=self.manager

    async def test_query_uses_existing_sensor_and_converts_fahrenheit(self):
        await self.manager.load()
        self.manager.archive.start(now.timestamp()-3600,10)
        data=await self.manager.analyse({'start_date':'2026-11-17','end_date':'2026-11-17','heating_base':20.,'heating_limit':15.})
        self.assertEqual(data['current'],10.)
        self.assertEqual(data['summary']['mean'],10.)
        self.assertEqual(data['timezone'],'Europe/Berlin')
        self.assertEqual(self.manager.statistics.await_count,4)
        self.assertEqual(data['summary']['exact_seconds'],3600)

    async def test_permission_denied_before_query(self):
        conn=Connection(read=False)
        await backend.ws_analyse(self.hass,conn,{'id':1,'entity_id':'sensor.test'})
        self.assertEqual(conn.errors[0][1],'unauthorized')
        self.manager.statistics.assert_not_awaited()

    async def test_sensor_list_hides_unreadable_sensor_and_settings(self):
        self.hass.data[backend.DOMAIN+'_settings']['card']={'entity':'sensor.test'}
        conn=Connection(read=False)
        await backend.ws_sensors(self.hass,conn,{'id':1,'card_id':'card'})
        self.assertEqual(conn.results[0][1]['sensors'],[])
        self.assertEqual(conn.results[0][1]['settings'],{})

    async def test_only_admin_can_save_settings(self):
        msg={'id':1,'card_id':'card','entity':'sensor.test','title':'Test','heating_base':20.,'heating_limit':15.}
        conn=Connection()
        await backend.ws_save_card(self.hass,conn,msg)
        self.assertEqual(conn.errors[0][1],'unauthorized')
        admin=Connection(admin=True)
        await backend.ws_save_card(self.hass,admin,msg)
        self.assertEqual(self.hass.data[backend.DOMAIN+'_settings']['card']['title'],'Test')

    async def test_invalid_ranges_and_heating_settings_rejected(self):
        for first,last,base,limit in [('2025-01-01','2026-11-17',20,15),('2027-01-01','2027-01-01',20,15),('2026-11-17','2026-11-16',20,15),('2026-11-17','2026-11-17',10,15)]:
            with self.assertRaises(ValueError):
                await self.manager.analyse({'start_date':first,'end_date':last,'heating_base':base,'heating_limit':limit})

    async def test_unknown_sensor_does_not_query_recorder(self):
        conn=Connection()
        await backend.ws_analyse(self.hass,conn,{'id':1,'entity_id':'sensor.other'})
        self.assertEqual(conn.errors[0][1],'not_configured')
        self.manager.statistics.assert_not_awaited()

    async def test_state_event_uses_its_own_snapshot(self):
        await self.manager.load()
        event=SimpleNamespace(time_fired=now,data={'new_state':SimpleNamespace(state='0',attributes={'unit_of_measurement':'°C'})})
        self.manager.state_changed(event)
        self.assertEqual(self.manager.archive.value,0)


if __name__=='__main__':unittest.main()
