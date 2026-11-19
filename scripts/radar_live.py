"""Verify official raw DWD history and forecasts, local projection and render speed."""
from urllib.request import urlopen,Request
from pathlib import Path
from datetime import datetime,timezone
from types import ModuleType
import sys,time,json
root=Path(__file__).parents[1]/'custom_components/weather_analysis'
pkg=ModuleType('live_radar');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
from live_radar.radar_data import archive_fields,first_member,metadata,sampling_grid,render,PNG
from live_radar.radar import map_box,frame_window
from live_radar.radar_store import DATA_URL
def get(url,start=None,end=None):
 headers={'Range':f'bytes={start}-{end}'} if start is not None else {}
 with urlopen(Request(url,headers=headers),timeout=40) as response:return response.read()
begin=time.perf_counter();archive=get(DATA_URL+'composite_rv_LATEST.tar');download=time.perf_counter()-begin
fields=archive_fields(archive);reference=max(key[0] for key in fields)
meta=metadata(fields[(reference,0)],(reference,0));frames=frame_window(meta,datetime.now(timezone.utc).timestamp())
scale=json.loads((root/'frontend/family-ui/1.16.0/radar-scale.json').read_text());bbox=map_box(49.3806,8.3039,3)
grid=sampling_grid(meta,bbox);begin=time.perf_counter();images=[]
for lead in range(0,76,5):images.append(render(fields[(reference,lead)],meta,grid,scale))
elapsed=time.perf_counter()-begin
assert all(image.startswith(PNG) for image in images)
historical=frames[0]['time'];date=datetime.fromtimestamp(historical,timezone.utc).strftime('%Y%m%d_%H%M')
url=DATA_URL+f'composite_rv_{date}.tar';prefix=get(url,0,524287);key,size=first_member(prefix)
if len(prefix)<size+512:prefix+=get(url,len(prefix),size+511)
assert key==(historical,0)
raw=prefix[512:512+size];older=metadata(raw,key);image=render(raw,older,sampling_grid(older,bbox),scale);assert image.startswith(PNG)
print(f'PASS raw DWD: past two hours and next hour verified; one forecast archive {len(archive)} bytes in {download:.2f}s; 16 local images in {elapsed:.3f}s ({sum(map(len,images))} bytes), no WMS map requests')
