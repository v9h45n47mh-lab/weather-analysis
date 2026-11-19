"""DWD ICON-D2-RUC precipitation rate, decoded on its native geographical grid."""
from __future__ import annotations
import asyncio
from datetime import datetime,timezone
import math
from pathlib import Path
import re
from .radar_data import RadarUnavailable,colour_image
from .radar_grib import decode
from .radar_store import RawRadarStore

MODEL_URL='https://opendata.dwd.de/weather/nwp/v1/m/icon-d2-ruc/p/'
RUN=re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2})(?:%3[Aa]|:)00/')
STEP=re.compile(r'PT(\d{3})H(\d{2})M\.grib2')

def native_grid(latitude_raw,longitude_raw,uuid):
    import numpy as np
    from scipy.spatial import cKDTree
    lat_meta,lat=decode(latitude_raw,'CLAT');lon_meta,lon=decode(longitude_raw,'CLON')
    if lat_meta['uuid']!=uuid or lon_meta['uuid']!=uuid or lat_meta['count']!=lon_meta['count'] or not np.isfinite(lat).all() or not np.isfinite(lon).all() or np.max(np.abs(lat))>90 or np.max(np.abs(lon))>180:raise ValueError('Model grid coordinates disagree')
    lat,lon=np.radians(lat.astype('float64')),np.radians(lon.astype('float64'))
    xyz=np.column_stack((np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)))
    return {'uuid':uuid,'count':len(lat),'tree':cKDTree(xyz)}

def model_sampling(grid,bbox,size=256):
    import numpy as np
    from pyproj import Transformer
    west,south,east,north=map(float,bbox.split(','))
    x=west+(np.arange(size)+.5)*(east-west)/size;y=north-(np.arange(size)+.5)*(north-south)/size
    xx,yy=np.meshgrid(x,y);lon,lat=Transformer.from_crs('EPSG:3857','EPSG:4326',always_xy=True).transform(xx,yy)
    lat,lon=np.radians(lat),np.radians(lon)
    xyz=np.stack((np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)),axis=-1)
    distance,index=grid['tree'].query(xyz.reshape(-1,3),distance_upper_bound=3500/6371000)
    return index.clip(0,grid['count']-1).reshape(size,size),np.isfinite(distance).reshape(size,size)

def model_image(raw,reference,valid,grid,sampling,scale):
    import numpy as np
    meta,values=decode(raw,'TOT_PR',reference,valid)
    if meta['uuid']!=grid['uuid'] or meta['count']!=grid['count']:raise ValueError('Changed model grid')
    index,coverage=sampling;rate=values[index];known=coverage&np.isfinite(rate)
    if not known.any():raise ValueError('No model coverage')
    return colour_image(np.maximum(0,rate),known,scale)

class ModelRadarStore(RawRadarStore):
    """Shared bounded GRIB cache; model files load only when the long view is opened."""
    def __init__(self,hass,session=None,clock=None):
        super().__init__(hass,session,clock)
        path=getattr(getattr(hass,'config',None),'path',None)
        self.directory=Path(path('.storage','weather_analysis.radar-model')) if callable(path) else None
        self.grid=None;self.grid_task=None;self.network=asyncio.Semaphore(2)

    def ensure(self):
        if self.refresh and not self.refresh.done():return
        if self.clock()-self.attempt<(60 if self.error else 900):return
        self.attempt=self.clock();self.refresh=self.spawn(self._refresh(),'Weather Analysis model metadata')

    async def _download(self,url,*args):
        if not url.startswith(MODEL_URL):raise ValueError('Untrusted model source')
        if self.session is None:
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            self.session=async_get_clientsession(self.hass)
        async with self.network,asyncio.timeout(35):
            async with self.session.get(url) as response:
                response.raise_for_status();raw=await response.read()
                if len(raw)>8_000_000:raise ValueError('Oversize model data')
                return raw

    @staticmethod
    def url(reference,parameter,lead=0):
        date=datetime.fromtimestamp(reference,timezone.utc).strftime('%Y-%m-%dT%H')+'%3A00'
        return MODEL_URL+f'{parameter}/r/{date}/s/PT{lead//60:03}H{lead%60:02}M.grib2'

    async def _refresh(self):
        try:
            listing=(await self._download(MODEL_URL+'TOT_PR/r/')).decode('utf-8')
            runs=sorted({int(datetime.strptime(run,'%Y-%m-%dT%H').replace(tzinfo=timezone.utc).timestamp()) for run in RUN.findall(listing)},reverse=True)
            for reference in [run for run in runs if 0<=self.clock()-run<=14400][:3]:
                url=self.url(reference,'TOT_PR').rsplit('/',1)[0]+'/'
                listing=(await self._download(url)).decode('utf-8')
                leads={int(hour)*60+int(minute) for hour,minute in STEP.findall(listing)}
                required=set(range(math.ceil((self.clock()+3600-reference)/1800)*30,math.ceil((self.clock()+43200-reference)/1800)*30+1,30))
                if required<=leads:
                    self.latest={'reference':reference,'leads':leads};self.error=None;return
            raise ValueError('No complete fresh twelve-hour model run')
        except asyncio.CancelledError:raise
        except Exception:
            self.error='Die DWD-Modellvorhersage für zwölf Stunden ist derzeit nicht verfügbar.'

    def available(self):
        return self.latest if self.latest and 0<=self.clock()-self.latest['reference']<=14400 and math.ceil((self.clock()+43200-self.latest['reference'])/1800)*30 in self.latest['leads'] else None

    def _read(self,name):
        if self.directory is None:return None
        path=self.directory/name
        try:return path.read_bytes() if path.is_file() and path.stat().st_size<=8_000_000 else None
        except OSError:return None

    def _write(self,name,raw):
        if self.directory is None:return
        with self.disk_lock:
            self.directory.mkdir(parents=True,exist_ok=True);path=self.directory/name;temp=path.with_suffix('.tmp');temp.write_bytes(raw);temp.replace(path)
            entries=sorted(self.directory.glob('*.grib2'),key=lambda p:p.stat().st_mtime,reverse=True);used=0
            for index,path in enumerate(entries):
                size=path.stat().st_size;used+=size
                if index>=80 or used>80_000_000:path.unlink(missing_ok=True)

    async def _field(self,reference,lead):
        if not isinstance(reference,int) or not isinstance(lead,int) or not 0<=lead<=1620 or lead%5:raise RadarUnavailable('Ungültige Modellzeit.')
        try:
            name=f'{reference}_{lead}.grib2';raw=await self.execute(self._read,name)
            if raw:
                try:await self.execute(decode,raw,'TOT_PR',reference,reference+lead*60)
                except Exception:raw=None
            if not raw:raw=await self._download(self.url(reference,'TOT_PR',lead))
            await self.execute(decode,raw,'TOT_PR',reference,reference+lead*60);self._remember({(reference,lead):raw})
            try:await self.execute(self._write,name,raw)
            except OSError:pass
            return raw
        except asyncio.CancelledError:raise
        except Exception as error:raise RadarUnavailable('Dieses DWD-Modellbild ist derzeit nicht verfügbar.') from error

    async def get_grid(self,reference,uuid):
        if self.grid and self.grid['uuid']==uuid:return self.grid
        if self.grid_task:
            await asyncio.shield(self.grid_task)
            if self.grid and self.grid['uuid']==uuid:return self.grid
        async def load():
            raw=[]
            for parameter in ('CLAT','CLON'):
                name=f'grid_{uuid}_{parameter}.grib2';data=await self.execute(self._read,name)
                if data:
                    try:meta,_=await self.execute(decode,data,parameter);assert meta['uuid']==uuid
                    except Exception:data=None
                if not data:data=await self._download(self.url(reference,parameter))
                raw.append(data)
                try:await self.execute(self._write,name,data)
                except OSError:pass
            self.grid=await self.execute(native_grid,*raw,uuid)
        task=self.grid_task=self.spawn(load(),'Weather Analysis native model grid')
        try:await asyncio.shield(task)
        finally:
            if task.done() and self.grid_task is task:self.grid_task=None
        return self.grid
