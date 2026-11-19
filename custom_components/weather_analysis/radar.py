"""DWD RV analysis/nowcast images on a BKG map, served through authenticated HA WS."""
from __future__ import annotations
import asyncio
import base64
from collections import OrderedDict
from datetime import datetime, timezone
import math
from uuid import uuid4
import xml.etree.ElementTree as ET
from .location import coordinates

API_URL = "https://maps.dwd.de/geoserver/ows"
BASE_URL = "https://sgx.geodatenzentrum.de/wms_topplus_open"
LAYER = "dwd:Niederschlagsradar"
NS = {"w":"http://www.opengis.net/wms"}
PNG = b"\x89PNG\r\n\x1a\n"

class RadarUnavailable(RuntimeError):
    pass

def instant(value):
    date=datetime.fromisoformat(value.replace("Z","+00:00"))
    if date.tzinfo is None:raise ValueError("Missing timezone")
    return int(date.timestamp())

def iso(value):
    return datetime.fromtimestamp(value,timezone.utc).isoformat().replace("+00:00","Z")

def capabilities(xml):
    """Read exact analysis runs and dynamic coverage; EPSG:4326 is lat/lon in WMS 1.3."""
    root=ET.fromstring(xml)
    layer=next(l for l in root.findall(".//w:Layer",NS) if l.findtext("w:Name",namespaces=NS)==LAYER)
    dims={d.get("name"):d for d in layer.findall("w:Dimension",NS)}
    refs={instant(t.strip()) for t in dims["REFERENCE_TIME"].text.split(",")}
    latest=instant(dims["REFERENCE_TIME"].get("default"))
    start,end,step=dims["time"].text.strip().split("/")
    if step!="PT5M" or latest not in refs:raise ValueError("Unexpected DWD time grid")
    box=next(b for b in layer.findall("w:BoundingBox",NS) if b.get("CRS")=="EPSG:4326")
    return {"refs":refs,"latest":latest,"first":instant(start),"last":instant(end),
        "coverage":tuple(float(box.get(k)) for k in ("minx","miny","maxx","maxy"))}

def frame_window(meta,now):
    """Five minute instants covering two hours back and at least one hour ahead."""
    anchor=int(now//300)*300
    if now-meta["latest"]>2700 or meta["latest"]>now+300:raise RadarUnavailable("DWD-Radardaten sind derzeit zu alt oder nicht verfügbar.")
    frames=[]
    end=math.ceil((now+3600)/300)*300
    for valid in range(anchor-7200,end+1,300):
        if valid<meta["first"] or valid>meta["last"]:continue
        measured=valid<=meta["latest"]
        if measured and valid not in meta["refs"]:continue
        frames.append({"time":valid,"reference":valid if measured else meta["latest"],"kind":"observation" if measured else "prediction"})
    if not frames or frames[0]["time"]>now-6900 or frames[-1]["time"]<now+3600:
        raise RadarUnavailable("Der DWD stellt den vollständigen Radarzeitraum derzeit nicht bereit.")
    return frames

def map_box(latitude,longitude,zoom):
    lat,lon=coordinates(latitude,longitude)
    x=6378137*math.radians(lon);y=6378137*math.log(math.tan(math.pi/4+math.radians(lat)/2))
    half=125000/(2**(zoom-1))/math.cos(math.radians(lat))
    return ",".join(f"{v:.2f}" for v in (x-half,y-half,x+half,y+half))

def image_request(window,kind,index=0):
    params={"service":"WMS","version":"1.3.0","request":"GetMap","crs":"EPSG:3857",
        "bbox":window["bbox"],"width":512,"height":512,"format":"image/png","styles":""}
    if kind=="base":return BASE_URL,{**params,"layers":"web"}
    if kind=="legend":return API_URL,{"service":"WMS","version":"1.3.0","request":"GetLegendGraphic","layer":LAYER,"format":"image/png"}
    frame=window["frames"][index]
    return API_URL,{**params,"layers":LAYER,"transparent":"true","time":iso(frame["time"]),"dim_REFERENCE_TIME":iso(frame["reference"])}

class RadarClient:
    """Bounded image/window caches. Arbitrary remote URLs and times are never accepted."""
    def __init__(self,hass,session=None,clock=None):
        self.hass,self.session=hass,session
        self.clock=clock or (lambda:datetime.now(timezone.utc).timestamp())
        self.meta=None;self.updated=0;self.attempt=None;self.lock=asyncio.Lock()
        self.windows=OrderedDict();self.images=OrderedDict();self.image_bytes=0
        self.inflight={};self.semaphore=asyncio.Semaphore(4)

    def _session(self):
        if self.session is None:
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            self.session=async_get_clientsession(self.hass)
        return self.session

    async def _metadata(self):
        async with self.lock:
            now=self.clock()
            if self.meta and now-self.updated<120:return self.meta
            if self.attempt is not None and now-self.attempt<30:raise RadarUnavailable("DWD-Regenradar ist derzeit nicht erreichbar.")
            self.attempt=now
            try:
                async with asyncio.timeout(30):
                    async with self._session().get(API_URL,params={"service":"WMS","version":"1.3.0","request":"GetCapabilities"}) as response:
                        response.raise_for_status();xml=await response.read()
                        if len(xml)>16000000:raise ValueError("Oversize capabilities")
                meta=capabilities(xml)
            except Exception as error:raise RadarUnavailable("DWD-Regenradar ist derzeit nicht erreichbar.") from error
            self.meta,self.updated=meta,now
            return meta

    async def get(self,owner,latitude,longitude,zoom=1):
        lat,lon=coordinates(latitude,longitude)
        if not isinstance(zoom,int) or not 0<=zoom<=3:raise ValueError("Invalid radar zoom")
        if abs(lat)>80:return {"status":"outside"}
        meta=await self._metadata();south,west,north,east=meta["coverage"]
        if not (south<=lat<=north and west<=lon<=east):return {"status":"outside"}
        now=self.clock();frames=frame_window(meta,now)
        token=uuid4().hex;window={"owner":owner,"created":now,"bbox":map_box(lat,lon,zoom),"frames":frames}
        self.windows[token]=window
        while len(self.windows)>128:self.windows.popitem(last=False)
        return {"status":"ok","token":token,"frames":frames,"now":now,"latest":meta["latest"],"updated_at":self.updated,"zoom":zoom}

    async def image(self,owner,token,kind,index=0):
        window=self.windows.get(token)
        if not window or window["owner"]!=owner or self.clock()-window["created"]>900:raise RadarUnavailable("Radarzeitraum abgelaufen. Bitte aktualisieren.")
        if kind not in ("base","legend","frame") or not isinstance(index,int) or not 0<=index<len(window["frames"]):raise ValueError("Invalid radar image")
        url,params=image_request(window,kind,index);key=(url,tuple(sorted(params.items())))
        if key in self.images:
            self.images.move_to_end(key);return self.images[key]
        if key not in self.inflight:
            task=asyncio.create_task(self._image(url,params,key))
            self.inflight[key]=task
            def finished(done):
                if self.inflight.get(key) is done:self.inflight.pop(key,None)
                if not done.cancelled():done.exception()
            task.add_done_callback(finished)
        task=self.inflight[key]
        try:return await asyncio.shield(task)
        finally:
            if task.done():self.inflight.pop(key,None)

    async def _image(self,url,params,key):
        try:
            async with self.semaphore,asyncio.timeout(30):
                async with self._session().get(url,params=params) as response:
                    response.raise_for_status();raw=await response.read()
            if not raw.startswith(PNG) or len(raw)>2000000:raise ValueError("Invalid WMS image")
            image="data:image/png;base64,"+base64.b64encode(raw).decode("ascii")
        except Exception as error:raise RadarUnavailable("Radarbild konnte nicht geladen werden. Eine leere Karte bedeutet keine Entwarnung.") from error
        self.images[key]=image;self.image_bytes+=len(image)
        while self.image_bytes>24000000 or len(self.images)>160:
            _,old=self.images.popitem(last=False);self.image_bytes-=len(old)
        return image
