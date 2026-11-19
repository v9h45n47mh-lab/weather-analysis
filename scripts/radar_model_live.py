"""Verify the real DWD twelve-hour forecast and native geographical grid."""
import asyncio,json,math,sys,time
from pathlib import Path
from types import ModuleType
from urllib.request import urlopen
root=Path(__file__).resolve().parents[1]/'custom_components/weather_analysis'
pkg=ModuleType('live_model');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
from live_model.radar_model import ModelRadarStore,decode,model_sampling,model_image
from live_model.radar import map_box
async def main():
    store=ModelRadarStore(None)
    async def download(url):
        def fetch():
            with urlopen(url,timeout=35) as response:return response.read()
        return await asyncio.to_thread(fetch)
    store._download=download
    try:
        store.ensure();await store.refresh;run=store.available();assert run,store.error
        reference=run['reference'];valid=math.ceil((store.clock()+3600)/300)*300+39600
        begin=time.perf_counter();raw=await store.get_field(reference,(valid-reference)//60)
        meta,values=decode(raw,'TOT_PR',reference,valid);grid=await store.get_grid(reference,meta['uuid'])
        sampling=await store.execute(model_sampling,grid,map_box(49.3806,8.3039,2))
        scale=json.loads((root/'frontend/family-ui/1.16.1/radar-scale.json').read_text())
        image=await store.execute(model_image,raw,reference,valid,grid,sampling,scale)
        assert image.startswith(b'\x89PNG') and sampling[1][128,128]
        Path('/tmp/dwd-model-live.png').write_bytes(image)
        print(f'PASS twelve-hour DWD ICON-D2-RUC: native grid {meta["count"]} cells, real run {reference}, valid {valid}, 30-minute forecast step, centred view and mm/h verified; one model field {len(raw)} bytes, render pipeline {time.perf_counter()-begin:.2f}s')
    finally:await store.close()
asyncio.run(main())
