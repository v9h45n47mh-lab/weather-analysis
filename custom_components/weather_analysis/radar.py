"""Fast, location-aware radar using shared DWD raw fields and local graphics."""
from __future__ import annotations
import asyncio
import base64
from collections import OrderedDict
from datetime import datetime,timezone
import json
import math
from pathlib import Path
from uuid import uuid4
from .location import coordinates
from .radar_data import RadarUnavailable,metadata,sampling_grid,render,project_map
from .radar_store import RawRadarStore,DATA_URL

MAX_ZOOM=3
DEFAULT_ZOOM=2
UI_VERSION='1.15.0'

def instant(value):
    date=datetime.fromisoformat(value.replace('Z','+00:00'))
    if date.tzinfo is None:raise ValueError('Missing timezone')
    return int(date.timestamp())

def iso(value):return datetime.fromtimestamp(value,timezone.utc).isoformat().replace('+00:00','Z')

def frame_window(meta,now):
    reference=meta['reference'];anchor=int(now//300)*300
    if not 0<=now-reference<=2700:raise RadarUnavailable('DWD-Radardaten sind derzeit zu alt.')
    end=math.ceil((now+3600)/300)*300
    if end>reference+7200:raise RadarUnavailable('Der DWD stellt den vollständigen Vorhersagezeitraum noch nicht bereit.')
    return [{'time':valid,'reference':valid if valid<=reference else reference,'kind':'observation' if valid<=reference else 'prediction'} for valid in range(anchor-7200,end+1,300)]

def map_box(latitude,longitude,zoom):
    lat,lon=coordinates(latitude,longitude)
    x=6378137*math.radians(lon);y=6378137*math.log(math.tan(math.pi/4+math.radians(lat)/2))
    half=125000/(2**(zoom-1))/math.cos(math.radians(lat))
    return ','.join(f'{v:.2f}' for v in (x-half,y-half,x+half,y+half))

def read_assets():
    root=Path(__file__).parent
    return json.loads((root/'data/radar-map.json').read_text()),json.loads((root/f'frontend/family-ui/{UI_VERSION}/radar-scale.json').read_text())

class RadarClient:
    def __init__(self,hass,session=None,clock=None):
        self.hass=hass;self.clock=clock or (lambda:datetime.now(timezone.utc).timestamp())
        self.store=RawRadarStore(hass,session,clock=self.clock)
        self.windows=OrderedDict();self.images=OrderedDict();self.image_bytes=0;self.inflight={}
        self.grids=OrderedDict();self.foreground=asyncio.Semaphore(2);self.background=asyncio.Semaphore(2)
        self.assets=None;self.asset_lock=asyncio.Lock()

    async def warm(self):
        self.store.ensure()
        if self.store.refresh:await asyncio.shield(self.store.refresh)

    async def _assets(self):
        async with self.asset_lock:
            if self.assets is None:self.assets=await self.store.execute(read_assets)
        return self.assets

    async def get(self,owner,latitude,longitude,zoom=DEFAULT_ZOOM):
        lat,lon=coordinates(latitude,longitude)
        if not isinstance(zoom,int) or not 0<=zoom<=MAX_ZOOM:raise ValueError('Invalid radar zoom')
        now=self.clock()
        if not (44<=lat<=58 and 0<=lon<=22):return {'status':'outside','now':now,'zoom':zoom,'context':f'outside|{lat}|{lon}','basemap':{}}
        bbox=map_box(lat,lon,zoom);data,_=await self._assets();basemap=await self.store.execute(project_map,bbox,data)
        base={'context':'raw-rv-v1|'+bbox,'basemap':basemap,'zoom':zoom,'now':now}
        self.store.ensure();meta=self.store.latest
        if not meta:
            return {**base,'status':'error' if self.store.error else 'loading','error':self.store.error,'frames':[],'refreshing':True}
        if not (meta['south']<=lat<=meta['north'] and meta['west']<=lon<=meta['east']):return {**base,'status':'outside'}
        try:frames=frame_window(meta,now)
        except RadarUnavailable as error:return {**base,'status':'error','error':str(error),'frames':[],'refreshing':True}
        token=uuid4().hex;self.windows[token]={'owner':owner,'created':now,'bbox':bbox,'frames':frames}
        while len(self.windows)>128:self.windows.popitem(last=False)
        return {**base,'status':'ok','token':token,'frames':frames,'latest':meta['reference'],'refreshing':bool(self.store.refresh and not self.store.refresh.done())}

    async def image(self,owner,token,kind,index=0,background=False):
        window=self.windows.get(token)
        if not window or window['owner']!=owner or self.clock()-window['created']>900:raise RadarUnavailable('Radarzeitraum abgelaufen. Bitte aktualisieren.')
        if kind!='frame' or not isinstance(index,int) or not 0<=index<len(window['frames']):raise ValueError('Bitte die Karte vollständig neu laden.')
        frame=window['frames'][index];key=(window['bbox'],frame['time'],frame['reference'])
        if key in self.images:self.images.move_to_end(key);return self.images[key]
        if key not in self.inflight:
            task=asyncio.create_task(self._image(window,frame,key,background));self.inflight[key]=task
            def done(result):
                if self.inflight.get(key) is result:self.inflight.pop(key,None)
                if not result.cancelled():result.exception()
            task.add_done_callback(done)
        return await asyncio.shield(self.inflight[key])

    async def _image(self,window,frame,key,background):
        async with (self.background if background else self.foreground):
            reference=frame['reference'];lead=(frame['time']-reference)//60
            raw=await self.store.get_field(reference,lead)
            try:
                meta=await self.store.execute(metadata,raw,(reference,lead))
                grid_key=(window['bbox'],meta['projection'],meta['width'],meta['height'],meta['xscale'],meta['yscale'],meta['origin_x'],meta['origin_y'])
                if grid_key not in self.grids:
                    self.grids[grid_key]=await self.store.execute(sampling_grid,meta,window['bbox'])
                    while len(self.grids)>16:self.grids.popitem(last=False)
                _,scale=await self._assets()
                png=await self.store.execute(render,raw,meta,self.grids[grid_key],scale)
            except Exception as error:raise RadarUnavailable('Für dieses Bild sind keine verlässlichen Radardaten verfügbar.') from error
            image='data:image/png;base64,'+base64.b64encode(png).decode('ascii')
            self.images[key]=image;self.image_bytes+=len(image)
            while self.image_bytes>24000000 or len(self.images)>160:
                _,old=self.images.popitem(last=False);self.image_bytes-=len(old)
            return image

    async def close(self):
        tasks=list(self.inflight.values())
        for task in tasks:task.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)
        await self.store.close()
