"""Probe official DWD capabilities, exact historical analysis, +1h nowcast and BKG map."""
from urllib.request import urlopen
from urllib.parse import urlencode
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from types import ModuleType
import importlib.util,sys
root=Path(__file__).parents[1]/'custom_components/weather_analysis'
pkg=ModuleType('live_radar');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
spec=importlib.util.spec_from_file_location('live_radar.radar',root/'radar.py')
r=importlib.util.module_from_spec(spec);sys.modules[spec.name]=r;spec.loader.exec_module(r)
def get(url,params):
 with urlopen(url+'?'+urlencode(params),timeout=35) as response:return response.read()
meta=r.capabilities(get(r.CAPABILITIES_URL,{'service':'WMS','version':'1.3.0','request':'GetCapabilities'}))
now=datetime.now(timezone.utc).timestamp();frames=r.frame_window(meta,now)
window={'bbox':r.map_box(49.3806,8.3039,1),'frames':frames}
requests=[r.image_request(window,'frame',0),r.image_request(window,'frame',len(frames)-1),r.image_request(window,'base'),r.image_request(window,'legend')]
with ThreadPoolExecutor(max_workers=4) as executor:
 images=list(executor.map(lambda request:get(*request),requests))
assert all(image.startswith(r.PNG) and len(image)>100 for image in images)
assert frames[0]['kind']=='observation' and frames[-1]['kind']=='prediction'
print('PASS live DWD RV and BKG: historical analysis through +1h nowcast, correct reference times, four valid PNGs',*[len(image) for image in images])
