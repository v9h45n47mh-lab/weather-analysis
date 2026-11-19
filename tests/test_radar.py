"""DWD validity, projection, cold startup and shared raw-data cache."""
import asyncio
from datetime import datetime,timezone
import io,json,struct,tarfile,tempfile,zlib
from pathlib import Path
from types import ModuleType
import sys,unittest
import h5py,numpy as np
from pyproj import Transformer
root=Path(__file__).parents[1]/'custom_components/weather_analysis'
pkg=ModuleType('radar_test_package');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
from radar_test_package import radar as r,radar_data as d
from radar_test_package.radar_store import RawRadarStore
NOW=int(datetime(2026,11,19,12,tzinfo=timezone.utc).timestamp())
PROJECTION='+proj=stere +lat_ts=60 +lat_0=90 +lon_0=10 +x_0=543196.83521776402 +y_0=3622588.8619310022 +units=m +a=6378137 +b=6356752.3142451802 +no_defs'
SCALE=json.loads((root/'frontend/family-ui/1.16.0/radar-scale.json').read_text())
def hdf(reference=NOW-600,lead=0,quantity='ACRR'):
 values=np.asarray([[0,1001,4294967295,1]]*4,dtype='uint32');height,width=values.shape;out=io.BytesIO()
 inverse=Transformer.from_crs(PROJECTION,'EPSG:4326',always_xy=True)
 with h5py.File(out,'w') as f:
  f.create_group('what').attrs.update(date=datetime.fromtimestamp(reference,timezone.utc).strftime('%Y%m%d').encode(),time=datetime.fromtimestamp(reference,timezone.utc).strftime('%H%M%S').encode())
  where=f.create_group('where');where.attrs.update(xsize=width,ysize=height,xscale=1000.,yscale=1000.,projdef=PROJECTION.encode())
  for name,x,y in [('UL',-500,500),('UR',width*1000-500,500),('LL',-500,500-height*1000),('LR',width*1000-500,500-height*1000)]:
   lon,lat=inverse.transform(x,y);where.attrs[name+'_lon']=lon;where.attrs[name+'_lat']=lat
  valid=reference+lead*60;start=datetime.fromtimestamp(valid-300,timezone.utc);end=datetime.fromtimestamp(valid,timezone.utc)
  f.create_group('dataset1/what').attrs.update(startdate=start.strftime('%Y%m%d').encode(),starttime=start.strftime('%H%M%S').encode(),enddate=end.strftime('%Y%m%d').encode(),endtime=end.strftime('%H%M%S').encode())
  f.create_group('dataset1/data1/what').attrs.update(quantity=quantity.encode(),gain=.001,offset=-.001,nodata=4294967295.,undetect=0.)
  f.create_dataset('dataset1/data1/data',data=values,compression='gzip')
 return out.getvalue()
def archive(reference=NOW-600):
 out=io.BytesIO()
 with tarfile.open(fileobj=out,mode='w') as tar:
  for lead in range(0,121,5):
   raw=hdf(reference,lead);name=datetime.fromtimestamp(reference,timezone.utc).strftime('composite_rv_%Y%m%d_%H%M_')+f'{lead:03}-hd5'
   member=tarfile.TarInfo(name);member.size=len(raw);tar.addfile(member,io.BytesIO(raw))
 return out.getvalue()
def rgba(png):
 offset=8;data=b'';size=None
 while offset<len(png):
  length=int.from_bytes(png[offset:offset+4],'big');kind=png[offset+4:offset+8];part=png[offset+8:offset+8+length]
  if kind==b'IHDR':size=struct.unpack('>II',part[:8])
  if kind==b'IDAT':data+=part
  offset+=12+length
 raw=zlib.decompress(data);width,height=size
 return np.array([list(raw[row*(width*4+1)+1:(row+1)*(width*4+1)]) for row in range(height)],dtype='uint8').reshape(height,width,4)
class Response:
 def __init__(self,data,status=200,headers=None):self.data=data;self.status=status;self.headers=headers or {}
 async def __aenter__(self):return self
 async def __aexit__(self,*args):pass
 def raise_for_status(self):pass
 async def read(self):await asyncio.sleep(0);return self.data
class Session:
 def __init__(self):self.calls=[];self.raw=archive();self.fail=False;self.gate=None
 def get(self,url,headers=None):
  self.calls.append((url,headers))
  if self.fail:raise OSError('offline')
  raw=self.raw;status=200;response_headers={}
  if headers and headers.get('Range'):
   first,last=map(int,headers['Range'][6:].split('-'));status=206;response_headers={'Content-Range':f'bytes {first}-{min(last,len(raw)-1)}/{len(raw)}'};raw=raw[first:last+1]
  response=Response(raw,status,response_headers)
  if self.gate:
   async def read():await self.gate.wait();return raw
   response.read=read
  return response
class DataTests(unittest.TestCase):
 def test_actual_reference_and_five_minute_accumulation_are_required(self):
  raw=hdf();meta=d.metadata(raw,(NOW-600,0));self.assertEqual(meta['gain'],.001);self.assertEqual(meta['reference'],NOW-600)
  with self.assertRaises(ValueError):d.metadata(raw,(NOW-300,0))
  with self.assertRaises(ValueError):d.metadata(hdf(quantity='DBZH'),(NOW-600,0))
 def test_archive_members_are_bounded_and_never_extracted(self):
  raw=archive();fields=d.archive_fields(raw);self.assertEqual(len(fields),25);key,size=d.first_member(raw)
  self.assertEqual(key,(NOW-600,0));self.assertEqual(raw[512:512+size],fields[key])
  with self.assertRaises(ValueError):d.member_key('../secret')
  with self.assertRaises(ValueError):d.member_key('composite_rv_20261119_1200_125-hd5')
  with self.assertRaises(ValueError):d.first_member(raw[:100])
 def test_projection_uses_actual_upper_left_and_north_down_rows(self):
  meta=d.metadata(hdf(),(NOW-600,0));self.assertAlmostEqual(meta['origin_x'],-500,places=4);self.assertAlmostEqual(meta['origin_y'],500,places=4)
  x,y=Transformer.from_crs(PROJECTION,'EPSG:3857',always_xy=True).transform(1000,-1000)
  grid=d.sampling_grid(meta,f'{x-1},{y-1},{x+1},{y+1}',size=1)
  self.assertEqual(int(grid[0][0,0]),1);self.assertEqual(int(grid[1][0,0]),1);self.assertTrue(grid[2][0,0])
 def test_units_dry_and_missing_data_are_distinct(self):
  raw=hdf();meta=d.metadata(raw,(NOW-600,0));grid=(np.array([[0,0],[0,0]]),np.array([[0,1],[2,3]]),np.ones((2,2),dtype=bool))
  image=rgba(d.render(raw,meta,grid,SCALE));self.assertEqual(int(image[0,0,3]),0)
  expected=next(item for item in reversed(SCALE) if item['min']<=12)
  self.assertEqual(image[0,1,:3].tolist(),[int(expected['color'][i:i+2],16) for i in (1,3,5)],'1 mm in five minutes equals 12 mm/h')
  self.assertEqual(int(image[1,0,3]),65,'No-data is hatched');self.assertEqual(int(image[1,1,3]),0,'Apply offset before colouring')
  with self.assertRaises(ValueError):d.render(raw,meta,(grid[0],grid[1],np.zeros((2,2),dtype=bool)),SCALE)
 def test_two_hour_history_and_full_hour_prediction_are_preserved(self):
  meta=d.metadata(hdf(),(NOW-600,0))
  for now in (NOW,NOW+25,NOW+299):
   frames=r.frame_window(meta,now);self.assertLessEqual(frames[0]['time'],now-7200);self.assertGreaterEqual(frames[-1]['time'],now+3600)
   self.assertTrue(all(f['reference']==f['time'] for f in frames if f['kind']=='observation'))
   self.assertTrue(all(f['reference']==NOW-600 for f in frames if f['kind']=='prediction'))
  with self.assertRaises(r.RadarUnavailable):r.frame_window(meta,NOW+3000)
 def test_background_has_four_labels_and_no_detailed_layers(self):
  data=json.loads((root/'data/radar-map.json').read_text());view=d.project_map(r.map_box(49.38,8.3,3),data)
  self.assertLessEqual(len(view['places']),4);self.assertTrue(all(line['kind'] in ('river','border') for line in view['lines']))
class StoreTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):self.session=Session();self.store=RawRadarStore(None,self.session,clock=lambda:NOW);self.store._warm_history=lambda:asyncio.sleep(0)
 async def asyncTearDown(self):await self.store.close()
 async def test_one_download_supplies_every_forecast(self):
  self.store.ensure();await self.store.refresh;self.assertEqual(self.store.latest['reference'],NOW-600)
  await asyncio.gather(*(self.store.get_field(NOW-600,lead) for lead in (0,5,10,60,75)))
  self.assertEqual(len(self.session.calls),1)
 async def test_history_uses_range_and_shared_requests(self):
  fields=await asyncio.gather(*(self.store.get_field(NOW-600,0) for _ in range(3)))
  self.assertEqual(fields[0],fields[1]);self.assertEqual(len(self.session.calls),1);self.assertIn('Range',self.session.calls[0][1])
 async def test_persisted_public_data_is_available_during_slow_refresh(self):
  with tempfile.TemporaryDirectory() as directory:
   self.store.directory=Path(directory);await self.store.execute(self.store._save_disk,{(NOW-600,0):hdf()})
   self.session.gate=asyncio.Event();self.store.ensure()
   for _ in range(100):
    if self.store.latest:break
    await asyncio.sleep(.005)
   self.assertEqual(self.store.latest['reference'],NOW-600);self.assertFalse(self.store.refresh.done())
 async def test_failure_never_creates_dry_weather(self):
  self.session.fail=True;self.store.ensure();await self.store.refresh
  self.assertIsNone(self.store.latest);self.assertTrue(self.store.error);self.assertEqual(self.store.fields,{})
class ClientTests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):self.session=Session();self.client=r.RadarClient(None,self.session,clock=lambda:NOW);self.client.store._warm_history=lambda:asyncio.sleep(0)
 async def asyncTearDown(self):await self.client.close()
 async def test_cold_map_does_not_wait_for_provider(self):
  self.session.gate=asyncio.Event();data=await asyncio.wait_for(self.client.get('alice',49.38,8.3),1)
  self.assertEqual(data['status'],'loading');self.assertEqual(data['zoom'],2);self.assertIn('basemap',data);self.assertLessEqual(len(data['basemap']['places']),4)
 async def test_owner_binding_and_token_expiry(self):
  self.client.store.ensure();await self.client.store.refresh;meta=self.client.store.latest
  data=await self.client.get('alice',(meta['north']+meta['south'])/2,(meta['east']+meta['west'])/2);self.assertEqual(data['status'],'ok')
  with self.assertRaises(r.RadarUnavailable):await self.client.image('bob',data['token'],'frame',0)
  with self.assertRaises(ValueError):await self.client.image('alice',data['token'],'frame',999)
  self.client.clock=lambda:NOW+901
  with self.assertRaises(r.RadarUnavailable):await self.client.image('alice',data['token'],'frame',0)
 async def test_outside_and_invalid_points(self):
  self.assertEqual((await self.client.get('alice',35,139))['status'],'outside')
  for point in [(91,0),(float('nan'),8)]:
   with self.assertRaises(ValueError):await self.client.get('alice',*point)
