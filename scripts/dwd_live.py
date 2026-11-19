"""Verify DWD spatial filtering with a live warning's own municipality polygon."""
from urllib.request import urlopen
from urllib.parse import urlencode
from pathlib import Path
import importlib.util,json,sys
from types import ModuleType
from datetime import datetime,timezone
root=Path(__file__).parents[1]/'custom_components/weather_analysis'
pkg=ModuleType('live_dwd');pkg.__path__=[str(root)];sys.modules['live_dwd']=pkg
spec=importlib.util.spec_from_file_location('live_dwd.warnings',root/'warnings.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def get(params):
 with urlopen(m.API_URL+'?'+urlencode(params),timeout=25) as response:return json.load(response)
def inside(x,y,ring):
 value=False
 for a,b in zip(ring,ring[1:]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:value=not value
 return value
home=get(m.query_params(49.3806,8.3039));alerts=m.parse_warnings(home,datetime.now(timezone.utc))
print('Live DWD explicit-CRS query verified: Böhl-Iggelheim; warnings:',len(alerts),flush=True)
sample=get({'service':'WFS','version':'2.0.0','request':'GetFeature','typeNames':'dwd:Warnungen_Gemeinden','outputFormat':'application/json','srsName':'EPSG:4326','count':1})
if sample['features']:
 f=sample['features'][0];g=f['geometry'];polygons=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
 candidates=[]
 for rings in polygons:
  xs=[p[0] for p in rings[0]];ys=[p[1] for p in rings[0]]
  for i in range(1,11):
   for j in range(1,11):
    x=round(min(xs)+(max(xs)-min(xs))*i/11,4);y=round(min(ys)+(max(ys)-min(ys))*j/11,4)
    if inside(x,y,rings[0]) and not any(inside(x,y,hole) for hole in rings[1:]):candidates.append((x,y))
  if candidates:break
 assert candidates,'No interior probe point'
 lon,lat=candidates[len(candidates)//2];data=get(m.query_params(lat,lon))
 assert data['features'],'Spatial filter lost a live warned municipality'
 assert any(record['properties']['NAME']==f['properties']['NAME'] for record in data['features'])
 m.parse_warnings(data,datetime.now(timezone.utc))
 print('Live DWD positive spatial control verified:',f['properties']['NAME'],'matching records:',len(data['features']),flush=True)
else:print('No current national warning is available for a positive spatial probe.',flush=True)
