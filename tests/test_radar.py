"""DWD run selection, real UTC windows, image validation, caching and user isolation."""
import asyncio
from datetime import datetime,timezone
import importlib.util
from pathlib import Path
from types import ModuleType
import sys,unittest
root=Path(__file__).parents[1]/'custom_components/weather_analysis'
pkg=ModuleType('radar_test_package');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
spec=importlib.util.spec_from_file_location('radar_test_package.radar',root/'radar.py')
r=importlib.util.module_from_spec(spec);sys.modules[spec.name]=r;spec.loader.exec_module(r)
NOW=int(datetime(2026,11,19,12,tzinfo=timezone.utc).timestamp())
def metadata():
 return {'refs':set(range(NOW-10800,NOW-599,300)),'latest':NOW-600,'first':NOW-10800,'last':NOW+6600,'coverage':(45,1,56,19)}
def xml():
 m=metadata();refs=','.join(r.iso(t) for t in sorted(m['refs']))
 return f'''<WMS_Capabilities xmlns="http://www.opengis.net/wms"><Capability><Layer><Layer><Name>{r.LAYER}</Name><BoundingBox CRS="EPSG:4326" minx="45" miny="1" maxx="56" maxy="19"/><Dimension name="time">{r.iso(m['first'])}/{r.iso(m['last'])}/PT5M</Dimension><Dimension name="REFERENCE_TIME" default="{r.iso(m['latest'])}">{refs}</Dimension></Layer></Layer></Capability></WMS_Capabilities>'''.encode()
class Response:
 def __init__(self,data):self.data=data
 async def __aenter__(self):return self
 async def __aexit__(self,*args):pass
 def raise_for_status(self):pass
 async def read(self):await asyncio.sleep(0);return self.data
class Session:
 def __init__(self):self.calls=[];self.fail=False;self.invalid=False
 def get(self,url,params):
  self.calls.append((url,params))
  if self.fail:raise OSError('offline')
  return Response(xml() if params['request']=='GetCapabilities' else b'<ServiceException/>' if self.invalid else r.PNG+b'test-image')
class WindowTests(unittest.TestCase):
 def test_capabilities_reads_dynamic_bbox_and_latest_run(self):
  self.assertEqual(r.capabilities(xml()),metadata())
 def test_two_hour_history_and_one_hour_forecast_even_between_grid_points(self):
  for offset in (0,25,299):
   frames=r.frame_window(metadata(),NOW+offset)
   self.assertLessEqual(frames[0]['time'],NOW+offset-7200)
   self.assertGreaterEqual(frames[-1]['time'],NOW+offset+3600)
   self.assertTrue(all(b['time']-a['time']==300 for a,b in zip(frames,frames[1:])))
   self.assertTrue(all(f['reference']==f['time'] for f in frames if f['kind']=='observation'))
   self.assertTrue(all(f['reference']==NOW-600 for f in frames if f['kind']=='prediction'))
   self.assertEqual(next(f for f in frames if f['time']==NOW)['kind'],'prediction','Delayed observations must not relabel nowcasts as measurements')
 def test_stale_missing_and_short_forecasts_cannot_claim_full_coverage(self):
  for meta in ({**metadata(),'latest':NOW-3000},{**metadata(),'last':NOW+3300}):
   with self.assertRaises(r.RadarUnavailable):r.frame_window(meta,NOW)
  m=metadata();m['refs'].remove(NOW-1800)
  self.assertNotIn(NOW-1800,[f['time'] for f in r.frame_window(m,NOW)])
 def test_image_requests_fix_provider_projection_and_exact_reference(self):
  window={'bbox':r.map_box(49.38,8.3,1),'frames':r.frame_window(metadata(),NOW)}
  for index in [0,len(window['frames'])-1]:
   url,p=r.image_request(window,'frame',index)
   self.assertEqual(url,r.API_URL);self.assertEqual(p['crs'],'EPSG:3857')
   self.assertEqual(p['time'],r.iso(window['frames'][index]['time']))
   self.assertEqual(p['dim_REFERENCE_TIME'],r.iso(window['frames'][index]['reference']))
  a=[float(v) for v in r.map_box(49.38,8.3,1).split(',')];b=[float(v) for v in r.map_box(49.38,8.3,2).split(',')]
  self.assertAlmostEqual(a[2]-a[0],2*(b[2]-b[0]),places=1)
class ClientTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):self.session=Session();self.now=NOW;self.client=r.RadarClient(None,self.session,clock=lambda:self.now)
 async def test_cache_singleflight_and_user_bound_token(self):
  data=await self.client.get('alice',49.38,8.3);token=data['token']
  await self.client.get('alice',49.38,8.3)
  self.assertEqual(len(self.session.calls),1)
  images=await asyncio.gather(*(self.client.image('alice',token,'frame',0) for _ in range(4)))
  self.assertTrue(all(image.startswith('data:image/png;base64,') for image in images));self.assertEqual(len(self.session.calls),2)
  await self.client.image('alice',token,'frame',0);self.assertEqual(len(self.session.calls),2)
  with self.assertRaises(r.RadarUnavailable):await self.client.image('bob',token,'frame',0)
  for kind,index in [('frame',-1),('frame',999),('url',0)]:
   with self.assertRaises(ValueError):await self.client.image('alice',token,kind,index)
  self.now+=901
  with self.assertRaises(r.RadarUnavailable):await self.client.image('alice',token,'frame',0)
 async def test_invalid_wms_png_and_outage_do_not_become_dry_images(self):
  data=await self.client.get('alice',49.38,8.3);self.session.invalid=True
  with self.assertRaises(r.RadarUnavailable):await self.client.image('alice',data['token'],'frame',0)
  self.assertEqual(len(self.client.images),0)
  self.session.invalid=False;self.session.fail=True;self.now+=121
  with self.assertRaises(r.RadarUnavailable):await self.client.get('alice',49.38,8.3)
  calls=len(self.session.calls)
  with self.assertRaises(r.RadarUnavailable):await self.client.get('alice',49.38,8.3)
  self.assertEqual(len(self.session.calls),calls)
 async def test_cancelled_waiter_does_not_leave_completed_image_tasks(self):
  data=await self.client.get('alice',49.38,8.3)
  waiter=asyncio.create_task(self.client.image('alice',data['token'],'frame',0))
  await asyncio.sleep(0);waiter.cancel()
  with self.assertRaises(asyncio.CancelledError):await waiter
  await asyncio.sleep(0);await asyncio.sleep(0);await asyncio.sleep(0)
  self.assertEqual(self.client.inflight,{})
  self.assertEqual(len(self.client.images),1)
 async def test_dynamic_coverage_and_bounded_tokens(self):
  self.assertEqual((await self.client.get('alice',35,139))['status'],'outside')
  for _ in range(132):await self.client.get('alice',49.38,8.3)
  self.assertEqual(len(self.client.windows),128)
  for coords in [(91,0),(float('nan'),8)]:
   with self.assertRaises(ValueError):await self.client.get('alice',*coords)
