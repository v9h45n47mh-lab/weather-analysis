"""Verify DWD's published WFS using public city-centre coordinates only."""
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
for place,lat,lon in [('Böhl-Iggelheim',49.3806,8.3039),('Creußen',49.86,11.6)]:
 params={'service':'WFS','version':'2.0.0','request':'GetFeature','typeNames':'dwd:Warnungen_Gemeinden','outputFormat':'application/json','srsName':'EPSG:4326','count':100,'CQL_FILTER':f'INTERSECTS(THE_GEOM,POINT({lon:.4f} {lat:.4f}))'}
 with urlopen(m.API_URL+'?'+urlencode(params),timeout=20) as r:data=json.load(r)
 warnings=m.parse_warnings(data,datetime.now(timezone.utc))
 assert len(data['features'])<100
 print('Live DWD spatial query verified:',place,'active/upcoming warnings:',len(warnings))
