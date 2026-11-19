"""Actual GRIB decoding, geographical alignment, forecast cadence and source isolation."""
import asyncio,unittest
import base64,json
from pathlib import Path
import numpy as np
from datetime import datetime,timezone
from unittest.mock import AsyncMock
from test_radar import r,d,SCALE,rgba,NOW
from radar_test_package import radar_model as m

UUID='c6b12daa91ad64045b26c1b6452a2a20'
def grib(parameter='TOT_PR',values=None,reference=NOW-3600,lead=180):
    fixtures=json.loads((Path(__file__).parent/'fixtures/ruc-grib.json').read_text())
    raw=bytearray(base64.b64decode(fixtures[parameter]));offset=16
    date=datetime.fromtimestamp(reference,timezone.utc)
    while offset<len(raw)-4:
        length=int.from_bytes(raw[offset:offset+4],'big');section=raw[offset+4]
        if section==1:raw[offset+12:offset+19]=date.year.to_bytes(2,'big')+bytes((date.month,date.day,date.hour,date.minute,date.second))
        if section==4:raw[offset+17]=0;raw[offset+18:offset+22]=lead.to_bytes(4,'big')
        offset+=length
    return bytes(raw)

class ModelDataTests(unittest.TestCase):
    def test_real_grib_units_missing_values_and_run_are_verified(self):
        meta,rate=m.decode(grib(),'TOT_PR',NOW-3600,NOW-3600+180*60)
        self.assertEqual(meta['uuid'],UUID);self.assertAlmostEqual(float(rate[1]),3.6,places=3);self.assertTrue(np.isnan(rate[2]))
        with self.assertRaises(ValueError):m.decode(grib(),'TOT_PR',NOW,NOW+180*60)
        with self.assertRaises(ValueError):m.decode(grib(),'CLAT')
        with self.assertRaises(ValueError):m.decode(grib()+b'extra','TOT_PR')

    def test_native_grid_and_image_share_coordinates_and_blue_scale(self):
        grid=m.native_grid(grib('CLAT',[49,49,49.04,49.04],lead=0),grib('CLON',[8,8.04,8,8.04],lead=0),UUID)
        index,known=m.model_sampling(grid,r.map_box(49,8,3),size=1)
        self.assertEqual(int(index[0,0]),0);self.assertTrue(known[0,0])
        sampling=(np.array([[0,1],[2,3]]),np.ones((2,2),dtype=bool))
        image=rgba(m.model_image(grib(),NOW-3600,NOW-3600+10800,grid,sampling,SCALE))
        self.assertEqual(int(image[0,0,3]),0);self.assertEqual(int(image[1,0,3]),65)
        colour=next(item['color'] for item in reversed(SCALE) if item['min']<=3.6)
        self.assertEqual(image[0,1,:3].tolist(),[int(colour[i:i+2],16) for i in (1,3,5)])
        _,covered=m.model_sampling(grid,r.map_box(53,-3,3),size=2);self.assertFalse(covered.any())

    def test_location_is_exactly_centered_at_every_zoom_and_forecast_horizon(self):
        for lat,lon in [(49.38,8.3),(53.55,10),(47.27,11),(57.5,13)]:
            for zoom in range(4):
                result=d.project_map(r.map_box(lat,lon,zoom),{'lines':[{'kind':'river','points':[[lon,lat],[lon+.001,lat]]}],'places':[]})
                self.assertEqual(result['lines'][0]['points'][0],[256,256])

    def test_continuous_future_changes_from_five_to_thirty_minutes_after_first_hour(self):
        now=NOW+137;frames=r.frame_window({'reference':NOW-600},now,12,{'reference':NOW-3600})
        future=[f for f in frames if f['time']>now]
        self.assertGreaterEqual(future[-1]['time'],now+43200)
        transition=((int(now)+3600+299)//300)*300
        near=[f for f in future if f['time']<=transition];far=[f for f in future if f['time']>transition]
        self.assertTrue(all(b['time']-a['time']==300 for a,b in zip(near,near[1:])))
        self.assertTrue(all(b['time']-a['time']==1800 for a,b in zip([near[-1]]+far,far)))
        self.assertEqual(len(far),22)
        self.assertEqual(len({f['time'] for f in frames}),len(frames))
        self.assertTrue(all(f['kind']=='model' and f['reference']==NOW-3600 for f in future if f['time']>transition))
        short=r.frame_window({'reference':NOW-600},now,1)
        self.assertTrue(all(b['time']-a['time']==300 for a,b in zip(short,short[1:])))
        self.assertFalse(any(f['kind']=='model' for f in short))

class ModelStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):self.store=m.ModelRadarStore(None,clock=lambda:NOW)
    async def asyncTearDown(self):await self.store.close()

    async def test_metadata_is_lightweight_and_requires_complete_fresh_coverage(self):
        root='2026-11-19T11%3A00/'
        steps=' '.join(f'PT{lead//60:03}H{lead%60:02}M.grib2' for lead in range(0,1621,5))
        self.store._download=AsyncMock(side_effect=[root.encode(),steps.encode()])
        self.store.ensure();await self.store.refresh
        self.assertEqual(self.store.available()['reference'],NOW-3600);self.assertEqual(self.store._download.await_count,2)
        self.assertEqual(self.store.fields,{})
        self.store.clock=lambda:NOW+15000;self.assertIsNone(self.store.available())

    async def test_same_model_field_is_shared_and_wrong_run_is_rejected(self):
        self.store._download=AsyncMock(return_value=grib(lead=90))
        values=await asyncio.gather(*(self.store.get_field(NOW-3600,90) for _ in range(3)))
        self.assertEqual(values[0],values[-1]);self.store._download.assert_awaited_once()
        with self.assertRaises(m.RadarUnavailable):await self.store.get_field(NOW,90)

    async def test_model_unavailability_keeps_near_radar_independent(self):
        self.store._download=AsyncMock(side_effect=OSError('offline'))
        self.store.ensure();await self.store.refresh
        self.assertIsNone(self.store.available());self.assertIn('nicht verfügbar',self.store.error)
        client=r.RadarClient(None,clock=lambda:NOW)
        try:
            client.model._download=self.store._download
            short=await client.get('alice',49.38,8.3,horizon=1)
            self.assertEqual(short['horizon'],1);self.assertIsNone(client.model.refresh)
        finally:await client.close()
