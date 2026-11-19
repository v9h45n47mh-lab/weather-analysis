"""DWD spatial query, CAP metadata, validity and failure semantics."""
import asyncio
from datetime import datetime,timedelta,timezone
import importlib.util
from pathlib import Path
from types import ModuleType
import sys,unittest
import xml.etree.ElementTree as ET
root=Path(__file__).parents[1]/'custom_components/weather_analysis'
pkg=ModuleType('dwd_test_package');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
spec=importlib.util.spec_from_file_location('dwd_test_package.warnings',root/'warnings.py')
w=importlib.util.module_from_spec(spec);sys.modules[spec.name]=w;spec.loader.exec_module(w)
NOW=datetime(2026,11,19,12,tzinfo=timezone.utc)
def feature(id='warning-1',level='Moderate',start=-1,end=3,**props):
 p={'IDENTIFIER':id,'STATUS':'Actual','SCOPE':'Public','MSGTYPE':'Alert','LANGUAGE':'de-DE','SEVERITY':level,
    'ONSET':(NOW+timedelta(hours=start)).isoformat(),'EXPIRES':(NOW+timedelta(hours=end)).isoformat(),
    'SENT':(NOW-timedelta(hours=2)).isoformat(),'HEADLINE':'Amtliche Warnung · synthetischer Test','EVENT':'STURM',
    'DESCRIPTION':'Synthetische Beschreibung <b>bleibt Text</b>.','INSTRUCTION':'Testhinweis\nZweite Zeile','NAME':'Gemeinde Test'}
 p.update(props);return {'type':'Feature','properties':p}
def payload(*features):return {'type':'FeatureCollection','numberMatched':len(features),'features':list(features)}
class Response:
 def __init__(self,data):self.data=data
 async def __aenter__(self):return self
 async def __aexit__(self,*args):pass
 def raise_for_status(self):pass
 async def json(self):return self.data
class Session:
 def __init__(self,data):self.data=data;self.calls=[];self.failure=None
 def get(self,url,**kwargs):
  self.calls.append((url,kwargs))
  if self.failure:raise self.failure
  return Response(self.data)
class ParseTests(unittest.TestCase):
 def test_current_future_levels_and_verbatim_metadata(self):
  data=w.parse_warnings(payload(feature('mild','Minor'),feature('severe','Severe',start=1)),NOW)
  self.assertEqual([x['id'] for x in data],['severe','mild'])
  self.assertEqual(data[0]['level_label'],'Unwetter');self.assertTrue(data[0]['upcoming'])
  self.assertEqual(data[1]['instruction'],'Testhinweis\nZweite Zeile')
  self.assertIn('<b>',data[1]['description'])
 def test_expired_test_cancelled_and_other_languages_are_excluded(self):
  data=w.parse_warnings(payload(feature('expired',start=-3,end=-1),feature('test',STATUS='Test'),feature('cancel',MSGTYPE='Cancel'),feature('english',LANGUAGE='en-US')),NOW)
  self.assertEqual(data,[])
 def test_updates_are_deduplicated_and_preliminary_is_explicit(self):
  older=feature(HEADLINE='Alt');new=feature(MSGTYPE='Update',SENT=NOW.isoformat(),HEADLINE='Vorabinformation Unwetter')
  data=w.parse_warnings(payload(older,new),NOW);self.assertEqual(len(data),1);self.assertTrue(data[0]['preliminary'])
 def test_malformed_or_truncated_responses_never_become_all_clear(self):
  for data in ({},{'type':'FeatureCollection','features':None},payload({'properties':None}),payload(feature(ONSET='bad')),payload(feature(EXPIRES='2026-11-19T18:00:00')),{**payload(),'numberMatched':1}):
   with self.assertRaises(ValueError):w.parse_warnings(data,NOW)
class ClientTests(unittest.IsolatedAsyncioTestCase):
 async def test_spatial_filter_uses_longitude_then_latitude_and_shared_cache(self):
  s=Session(payload(feature()));c=w.WarningsClient(None,s,lambda:NOW)
  values=await asyncio.gather(*(c.get(49.3806,8.3039) for _ in range(5)))
  self.assertEqual(len(s.calls),1);self.assertTrue(all(v['status']=='ok' for v in values))
  filter=ET.fromstring(s.calls[0][1]['params']['FILTER'])
  point=filter.find('.//{http://www.opengis.net/gml/3.2}Point')
  self.assertEqual(point.attrib['srsName'],'urn:ogc:def:crs:OGC:1.3:CRS84')
  self.assertEqual(point[0].text,'8.3039 49.3806')
  self.assertNotIn('CQL_FILTER',s.calls[0][1]['params'])
  self.assertEqual(s.calls[0][1]['params']['typeNames'],'dwd:Warnungen_Gemeinden')
 async def test_empty_success_and_network_error_are_distinct(self):
  clock=[NOW];s=Session(payload());c=w.WarningsClient(None,s,lambda:clock[0])
  first=await c.get(49.38,8.3);self.assertEqual(first['alerts'],[])
  clock[0]+=timedelta(seconds=121);s.failure=OSError('offline')
  with self.assertRaises(w.WarningsUnavailable):await c.get(49.38,8.3)
  with self.assertRaises(w.WarningsUnavailable):await c.get(49.38,8.3)
  self.assertEqual(len(s.calls),2)
 async def test_cache_is_by_location_and_does_not_keep_expired_alerts(self):
  clock=[NOW];s=Session(payload(feature(end=.01)));c=w.WarningsClient(None,s,lambda:clock[0])
  await c.get(49.38,8.3);await c.get(53.55,10)
  self.assertEqual(len(s.calls),2)
  clock[0]+=timedelta(seconds=40);self.assertEqual((await c.get(49.38,8.3))['alerts'],[])
  self.assertEqual(len(s.calls),2)
 async def test_outside_unknown_and_invalid_coordinates_do_not_query_dwd(self):
  s=Session(payload());c=w.WarningsClient(None,s,lambda:NOW)
  self.assertEqual((await c.get(35,139,'jp'))['status'],'outside')
  self.assertEqual((await c.get(49,8,''))['status'],'unknown')
  with self.assertRaises(ValueError):await c.get(91,8)
  self.assertEqual(s.calls,[])
 async def test_provider_schema_failure_and_cancellation(self):
  s=Session({});c=w.WarningsClient(None,s,lambda:NOW)
  with self.assertRaises(w.WarningsUnavailable):await c.get(49,8)
  s=Session(payload());s.failure=asyncio.CancelledError()
  with self.assertRaises(asyncio.CancelledError):await w.WarningsClient(None,s,lambda:NOW).get(49,8)
